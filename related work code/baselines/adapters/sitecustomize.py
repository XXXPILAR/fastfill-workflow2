"""Loaded automatically (PYTHONPATH set by with_api.py): every openai chat call made by a baseline repo goes to our
relay's Responses API with the chosen model / reasoning effort, whatever model name the repo hard-codes (gpt-4o, ...),
and its usage is appended to BASELINE_USAGE_FILE."""
import os
try:
    import openai
    from openai.resources.chat import completions as _c
    from openai.types.chat import ChatCompletion
    import relay  # the relay routes GPT models only on its Responses API: chat calls are sent there (relay.py)

    class _Raw:  # what with_raw_response.create returns, as far as langchain-openai uses it
        def __init__(self, parsed):
            self._parsed, self.headers, self.http_response = parsed, {}, None
        def parse(self):
            return self._parsed

    def create(self, *args, **kwargs):
        # model / reasoning effort: BASELINE_MODEL / BASELINE_REASONING_EFFORT (relay.chat), whatever the repo names;
        # sampling knobs and max_tokens are dropped (reasoning models reject them; max_tokens would cut reasoning)
        try:
            text, call = relay.chat(kwargs["messages"])
        except Exception:
            _log({"usage": None, "failed_attempts": 10})
            raise
        _log(call)
        parsed = ChatCompletion.model_validate({
            "id": "relay", "object": "chat.completion", "created": 0, "model": os.environ["OPENAI_MODEL"],
            "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": text}}],
            "usage": {k: call["usage"].get(k) or 0 for k in ("prompt_tokens", "completion_tokens", "total_tokens")}})
        raw = any(str(k).lower() == "x-stainless-raw-response" for k in (kwargs.get("extra_headers") or {}))
        return _Raw(parsed) if raw else parsed
    def _log(record):
        path = os.environ.get("BASELINE_USAGE_FILE")
        if path:
            import json
            with open(path, "a") as f:
                f.write(json.dumps(record) + "\n")
    _c.Completions.create = create
    _init = openai.OpenAI.__init__
    def __init__(self, *args, **kwargs):
        headers = dict(kwargs.pop("default_headers", None) or {}); headers["User-Agent"] = "fastfill-llm-baseline/1.0"
        _init(self, *args, default_headers=headers, **kwargs)
    openai.OpenAI.__init__ = __init__
except ImportError:
    pass
