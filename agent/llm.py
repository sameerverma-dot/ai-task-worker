"""The "brain": something that looks at the situation and picks the next tool call.

Two versions with the same interface, decide(system, user, tools) -> {"tool", "args"}:
  * GroqLLM     - the real model, called over the Groq API with tool calling.
  * ScriptedLLM - a fake that replays a fixed list of actions. Lets tests run offline, with no key.
"""
import json
import os
import time

import groq

from config import FALLBACK_MODELS, MODEL


class GroqLLM:
    def __init__(self, model=MODEL, fallback=True):
        self.model = model
        # fallback=False keeps every decision on one model (fair eval): when its daily quota runs out,
        # we wait for quota to come back instead of switching.
        self.fallbacks = [m for m in FALLBACK_MODELS if m != model] if fallback else []
        # The key comes only from the environment and is never printed. (In the cloud sandbox a
        # proxy adds the real key to each request, so a placeholder is enough there.)
        self.client = groq.Groq(api_key=os.environ.get("GROQ_API_KEY", "added-by-proxy"),
                                 max_retries=0)  # we handle retries ourselves, below

    def decide(self, system, user, tools):
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        attempt = 0
        while attempt < 8:  # rate-limit waits don't count as attempts; real errors do
            try:
                response = self.client.chat.completions.create(
                    model=self.model, messages=messages, tools=tools,
                    tool_choice="required",      # it must answer with a tool call, not chat
                    parallel_tool_calls=False,   # one action per step keeps the loop simple
                    temperature=0.1,
                    # gpt-oss "thinks" before answering, and those hidden tokens count against the
                    # free-tier limit. Low effort is enough for picking one tool call.
                    **({"reasoning_effort": "low"} if "gpt-oss" in self.model else {}))
                call = response.choices[0].message.tool_calls[0]
                return {"tool": call.function.name, "args": json.loads(call.function.arguments or "{}"),
                        "model": self.model}
            except groq.RateLimitError as e:
                # Daily quota used up: waiting would take hours, so switch to the next model.
                if "tokens per day" in str(e) and self.fallbacks:
                    print(f"   (daily token limit reached for {self.model}, switching to {self.fallbacks[0]})")
                    self.model = self.fallbacks.pop(0)
                    continue
                # Per-minute limit (or daily limit with no fallback): wait as long as Groq tells us to.
                wait = float(e.response.headers.get("retry-after", 10)) + 1
                kind = "daily quota used up" if "tokens per day" in str(e) else "rate limited"
                print(f"   ({kind} on {self.model}, waiting {wait:.0f}s)")
                time.sleep(wait)
            except (groq.BadRequestError, json.JSONDecodeError, TypeError, IndexError) as e:
                # The model produced a malformed tool call. Tell it and let it try again.
                attempt += 1
                messages.append({"role": "user", "content": f"Your last reply was not a valid tool call "
                                                            f"({str(e)[:200]}). Reply with exactly one tool call."})
            except (groq.APIConnectionError, groq.InternalServerError):
                attempt += 1
                time.sleep(2 ** attempt)
        # The model never produced a usable call: end the run honestly instead of crashing.
        return {"tool": "finish", "args": {"summary": "Stopped: the LLM failed to produce a valid action.",
                                            "success": False, "verified": False}}


class ScriptedLLM:
    """Replays a list of (tool, args) actions. When the list runs out, repeats the last one."""
    def __init__(self, actions):
        self.actions = list(actions)
        self.calls = 0

    def decide(self, system, user, tools):
        tool, args = self.actions[min(self.calls, len(self.actions) - 1)]
        self.calls += 1
        self.last_user_message = user  # tests look at this to check warnings reached the "LLM"
        return {"tool": tool, "args": dict(args)}
