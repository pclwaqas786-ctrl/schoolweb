"""ai_engine.py — provider-agnostic LLM module for SchoolWeb.

Provider order:
  1. Claude API (primary / production) — needs CLAUDE_API_KEY env var.
     To switch Groq -> Claude: set CLAUDE_API_KEY and restart. That's it (1-line change).
  2. Groq (fallback / dev, $0) — uses the user's vault credential (custom.groq)
     through the authd surrogate; NEVER a raw key in env/files/chat.

ask_ai(prompt, system=None, max_tokens=800) -> (text, provider)
Raises RuntimeError when no provider is reachable.
"""
import json
import os
import sys
import urllib.request

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# --- Groq via vault surrogate (secure, no raw key) ---
_SKILL_BIN = "/opt/hatch/skills/skill-creator/bin"
_GROQ_OK = False
try:
    sys.path.insert(0, _SKILL_BIN)
    from dynamic_credentials import (  # noqa: E402
        add_surrogate_to_request,
        read_json_response,
    )
    _GROQ_OK = True
except Exception:
    _GROQ_OK = False

GROQ_MODEL = "openai/gpt-oss-20b"  # verified working on the free tier
GROQ_BASE = "https://api.groq.com/openai/v1"
CLAUDE_MODEL = "claude-sonnet-4-20250514"


def _groq_call(prompt, system, max_tokens):
    if not _GROQ_OK:
        raise RuntimeError("Groq surrogate helper unavailable")
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {"model": GROQ_MODEL, "messages": messages,
               "max_tokens": max_tokens, "temperature": 0.5}
    req = urllib.request.Request(GROQ_BASE + "/chat/completions",
                                 data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", UA)
    add_surrogate_to_request(req, "custom.groq", allowed_hosts=["api.groq.com"])
    with urllib.request.urlopen(req, timeout=90) as resp:
        out = read_json_response(resp)
    choices = out.get("choices") or []
    if not choices:
        raise RuntimeError("Groq returned no choices: %s" % json.dumps(out)[:300])
    return choices[0]["message"]["content"].strip()


def _claude_call(prompt, system, max_tokens):
    key = os.environ.get("CLAUDE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("CLAUDE_API_KEY not set")
    payload = {"model": CLAUDE_MODEL, "max_tokens": max_tokens,
               "messages": [{"role": "user", "content": prompt}]}
    if system:
        payload["system"] = system
    req = urllib.request.Request("https://api.anthropic.com/v1/messages",
                                 data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("x-api-key", key)
    req.add_header("anthropic-version", "2023-06-01")
    req.add_header("User-Agent", UA)
    with urllib.request.urlopen(req, timeout=90) as resp:
        out = json.loads(resp.read().decode())
    blocks = out.get("content") or []
    text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
    if not text:
        raise RuntimeError("Claude returned no text: %s" % json.dumps(out)[:300])
    return text


def ask_ai(prompt, system=None, max_tokens=800):
    """Ask the LLM. Returns (text, provider_name).

    Provider order: Claude (if CLAUDE_API_KEY set) -> Groq (vault, free).
    """
    errors = []
    if os.environ.get("CLAUDE_API_KEY", "").strip():
        try:
            return _claude_call(prompt, system, max_tokens), "claude"
        except Exception as e:  # noqa: BLE001 - fall through to Groq
            errors.append("claude: %s" % e)
    try:
        return _groq_call(prompt, system, max_tokens), "groq"
    except Exception as e:  # noqa: BLE001
        errors.append("groq: %s" % e)
    raise RuntimeError("No AI provider reachable (" + "; ".join(errors) + ")")


def provider_status():
    """For the dashboard badge: which provider would be used."""
    if os.environ.get("CLAUDE_API_KEY", "").strip():
        return "claude"
    return "groq" if _GROQ_OK else "none"


if __name__ == "__main__":
    txt, prov = ask_ai("Reply with exactly: AI_ENGINE_OK")
    print("provider:", prov)
    print("reply:", txt[:100])
