"""One chat call through the relay: /chat/completions by default since 2026-10-28 (``chat``); before that its Responses API (POST <base>/responses): since 2026-10-21 the relay routed no GPT
model on /chat/completions ("no route available for the requested model"). Chat messages are converted (system ->
instructions, image_url parts -> input_image); usage is returned in chat-completions field names, so ledgers and
llm_cost read it as before.

    text, call = chat(messages)      # call = {"usage": {...}, "failed_attempts": n}
"""
import json, os, time, urllib.error, urllib.request

USER_AGENT = "fastfill-llm-baseline/1.0"


def to_input(messages):
    instructions, items = [], []
    for m in messages:
        content = m["content"]
        if m["role"] in ("system", "developer"):
            instructions.append(content if isinstance(content, str) else " ".join(p.get("text", "") for p in content))
            continue
        if isinstance(content, list):
            parts = []
            for p in content:
                if p.get("type") == "text":
                    parts.append({"type": "input_text" if m["role"] == "user" else "output_text", "text": p["text"]})
                elif p.get("type") == "image_url":
                    url = p["image_url"]["url"] if isinstance(p["image_url"], dict) else p["image_url"]
                    parts.append({"type": "input_image", "image_url": url})
            content = parts
        items.append({"role": m["role"], "content": content})
    return ("\n\n".join(instructions) or None), items


def chat_usage(u):
    u = u or {}
    return {"prompt_tokens": u.get("input_tokens"), "completion_tokens": u.get("output_tokens"), "total_tokens": u.get("total_tokens"),
            "prompt_tokens_details": {"cached_tokens": (u.get("input_tokens_details") or {}).get("cached_tokens")},
            "completion_tokens_details": {"reasoning_tokens": (u.get("output_tokens_details") or {}).get("reasoning_tokens")}}


def output_text(a):
    return "".join(c.get("text", "") for o in a.get("output") or [] if o.get("type") == "message"
                   for c in o.get("content") or [] if c.get("type") == "output_text")


def _throttle():
    """The request log shared with the workflow runs (same file format and rule as Fastfill workflow2's
    workflow/llm.py ``_throttle``: WORKFLOW_RPM requests per rolling 60 s, counted in WORKFLOW_RPM_FILE under an
    exclusive lock), so every run started together stays under the relay's limit. Written out here because the
    baseline environments cannot import the workflow package (it needs torch)."""
    rpm, state = os.environ.get("WORKFLOW_RPM"), os.environ.get("WORKFLOW_RPM_FILE")
    if not rpm or not state:
        return
    import fcntl
    limit = int(rpm)
    while True:
        with open(state, "a+", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0)
            try:
                stamps = [t for t in json.loads(f.read() or "[]") if time.time() - t < 60.]
            except ValueError:
                stamps = []
            if len(stamps) < limit:
                stamps.append(time.time())
                f.seek(0)
                f.truncate()
                f.write(json.dumps(stamps))
                return
            wait = 60. - (time.time() - min(stamps)) + .05
        time.sleep(max(wait, .05))


def chat(messages, attempts=10, timeout=600):
    """Since 2026-10-28 (the relay's new entries, e.g. https://api.kbsfdxc.net/codex/v1): its chat completions route
    serves the GPT models again and keeps the system message as sent, while its Responses route replaces
    ``instructions`` with its own Codex prompt. So the messages go to /chat/completions unchanged (images as
    image_url parts, which it reads). BASELINE_ENDPOINT=responses restores the old Responses call below."""
    if os.environ.get("BASELINE_ENDPOINT", "chat") == "chat":
        return _chat_completions(messages, attempts, timeout)
    instructions, items = to_input(messages)
    body = {"model": os.environ["OPENAI_MODEL"], "input": items, "store": False,
            "reasoning": {"effort": os.environ.get("BASELINE_REASONING_EFFORT", "medium")}}
    # without instructions the relay's codex route puts its own ~4.2k-token Codex agent prompt in front ("I'm Codex
    # ... writing, reviewing, and testing code"); a request with no system message gets a neutral one instead
    body["instructions"] = instructions or "You are a helpful assistant."
    data = json.dumps(body).encode()
    for attempt in range(attempts):
        _throttle()
        try:
            req = urllib.request.Request(os.environ["OPENAI_BASE_URL"].rstrip("/") + "/responses", data=data, headers={
                "Content-Type": "application/json", "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"], "User-Agent": USER_AGENT})
            a = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
            text = output_text(a)
            if a.get("status") == "completed" and text:
                return text, {"usage": chat_usage(a.get("usage")), "failed_attempts": attempt}
            problem = a.get("error") or a.get("incomplete_details") or a
        except urllib.error.HTTPError as e:
            problem = f"HTTP {e.code}: {e.read()[:200]!r}"
        except Exception as e:  # noqa: BLE001 - relay hiccups; the last attempt re-raises
            problem = e
        if attempt == attempts - 1:
            raise RuntimeError(f"relay gave no completion: {str(problem)[:300]}")
        time.sleep(min(120., 5. * 2 ** attempt))


def _chat_completions(messages, attempts, timeout):
    """WORKFLOW_LLM_ATTEMPTS (0 = until it succeeds) overrides ``attempts`` for transient problems (busy, rate limit,
    5xx, dropped connection, an answer without text); a rejected key / no access / unknown model raises at once."""
    attempts = int(os.environ.get("WORKFLOW_LLM_ATTEMPTS", attempts))
    body = {"model": os.environ["OPENAI_MODEL"], "messages": messages,
            "reasoning_effort": os.environ.get("BASELINE_REASONING_EFFORT", "medium")}
    data = json.dumps(body).encode()
    problem, attempt = None, -1
    while True:
        attempt += 1
        if attempts and attempt >= attempts:
            raise RuntimeError(f"relay gave no completion: {str(problem)[:300]}")
        if attempt and attempt % 5 == 0:
            print(f"relay retry {attempt}: {str(problem)[:160]}", flush=True)
        _throttle()
        try:
            req = urllib.request.Request(os.environ["OPENAI_BASE_URL"].rstrip("/") + "/chat/completions", data=data, headers={
                "Content-Type": "application/json", "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"], "User-Agent": USER_AGENT})
            a = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
            choice = (a.get("choices") or [{}])[0]
            text = (choice.get("message") or {}).get("content") or ""
            if choice.get("finish_reason") == "stop" and text:
                u = a.get("usage") or {}
                usage = {"prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"),
                         "total_tokens": u.get("total_tokens"),
                         "prompt_tokens_details": {"cached_tokens": (u.get("prompt_tokens_details") or {}).get("cached_tokens")},
                         "completion_tokens_details": {"reasoning_tokens": (u.get("completion_tokens_details") or {}).get("reasoning_tokens")}}
                return text, {"usage": usage, "failed_attempts": attempt}
            problem = a.get("error") or choice.get("finish_reason") or a
        except urllib.error.HTTPError as e:
            detail = e.read()[:200]
            if e.code in (401, 403, 404) or b"insufficient_quota" in detail:  # key / access / model / quota: final
                raise RuntimeError(f"relay rejected the request: HTTP {e.code} {detail!r}") from None
            problem = f"HTTP {e.code}: {detail!r}"
        except Exception as e:  # noqa: BLE001 - relay hiccups
            problem = e
        time.sleep(min(120., 5. * 2 ** min(attempt, 5)))
