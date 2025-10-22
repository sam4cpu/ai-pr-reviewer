"""
robust_openai.py
- wraps OpenAI client calls with exponential backoff + jitter
- local caching of responses to survive quota/rate-limit outages
- graceful fallback to MOCK mode
"""

import os
import time
import json
import random
from pathlib import Path

try:
    from openai import OpenAI, APIError, RateLimitError, ServiceUnavailableError
except Exception:
    OpenAI = None
    APIError = Exception
    RateLimitError = Exception
    ServiceUnavailableError = Exception

CACHE_DIR = Path(".cache")
RESP_CACHE = CACHE_DIR / "openai_responses.json"
CACHE_DIR.mkdir(exist_ok=True)

def _load_cache():
    if RESP_CACHE.exists():
        try:
            return json.loads(RESP_CACHE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _save_cache(cache):
    RESP_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")

def request_with_backoff(openai_key, messages, model="gpt-4o-mini", max_retries=4, timeout=30):
    """
    Return: text or None
    Behavior:
      - Try live OpenAI if key present and client available
      - On transient errors (rate limits/service unavailable), retry with exponential backoff + jitter
      - On final failure, try cached response (by prompt hash)
      - If no cache, return None (caller should fallback to MOCK text)
    """
    prompt_hash = str(abs(hash("".join(m.get("content","") for m in messages))))  # stable-ish
    cache = _load_cache()

    if openai_key and OpenAI is not None:
        client = OpenAI(api_key=openai_key)
        for attempt in range(1, max_retries + 1):
            try:
                # set a moderate timeout; keep single-call semantics
                resp = client.chat.completions.create(model=model, messages=messages, timeout=timeout)
                # adapt to different possible response shapes
                choice = resp.choices[0]
                content = getattr(choice, "message", None)
                if content:
                    text = content.content
                else:
                    text = choice.get("message", {}).get("content") or choice.get("text")
                # store into cache
                cache[prompt_hash] = {"ts": time.time(), "model": model, "text": text}
                _save_cache(cache)
                return text
            except (RateLimitError, ServiceUnavailableError) as e:
                wait = (2 ** attempt) + random.uniform(0, 1.0)  # jitter
                print(f"[WARN] Rate/service error ({e}). Backoff {wait:.1f}s (attempt {attempt}/{max_retries})")
                time.sleep(wait)
            except APIError as e:
                print(f"[ERROR] APIError: {e} (attempt {attempt}/{max_retries})")
                time.sleep(2)
            except Exception as e:
                # unknown errors - break early to avoid long hangs
                print(f"[FATAL] Unexpected OpenAI client error: {e}")
                break

    # Live call failed or not possible — attempt cached response
    if prompt_hash in cache:
        print("[INFO] Using cached OpenAI response (offline fallback).")
        return cache[prompt_hash]["text"]

    print("[WARN] No OpenAI response available and no cache found.")
    return None
