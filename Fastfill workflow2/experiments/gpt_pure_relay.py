"""Pure GPT baseline through the relay: fastfill.v2.ops.llm_probe's protocol on chosen test300 rooms.

One request per room, the full condition (polygon, doors/windows, fixed objects, the object list, constraints); GPT
chooses sizes, positions and facings; no tidy, no repair (the raw first answer). The prompt, the parser and the
problem count are llm_probe's own (``llm_workflow.instructions`` / ``request_text`` / ``parse`` /
``workflow_problems``, with the instructions as a system message, which the relay keeps). The key and model are read
in place from ``~/.fastfill_api.env`` (never copied, never printed); only the base URL is replaced in memory by a
relay entry (``workflow.credentials.RELAY_HOSTS``). Requests go through the rate limit shared with the workflow
runs (``workflow.llm._throttle``: ``WORKFLOW_RPM`` / ``WORKFLOW_RPM_FILE``). Resumable: rooms answered without an
error are kept.

    ../.venv/bin/python experiments/gpt_pure_relay.py --rows ../test300/rows.jsonl --rooms experiments/exp150/rooms.json \
        --out experiments/exp150/gpt_pure --rpm 30 --rpm-file experiments/exp150/.rpm_state.json
"""
import argparse, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from workflow import llm  # noqa: E402  (also puts the fastfill package on sys.path)
from workflow.credentials import RELAY_BASE_URL, RELAY_ENV_FILE, RELAY_HOSTS  # noqa: E402
from fastfill.v2.llm_baseline import load_env  # noqa: E402
from fastfill.v2.llm_baseline import USER_AGENT, request_parameters  # noqa: E402
from fastfill.v2.llm_workflow import instructions, parse, request_text, workflow_problems  # noqa: E402
from fastfill.v2.schema import migrate_legacy_row  # noqa: E402


def chat(env, model, messages, *, limiter, usage, timeout=300., attempts=None):
    """llm_structured.chat's request, unchanged (request_parameters + messages to /chat/completions), with one change:
    an answer without ``choices`` is retried like a dropped connection. The relay sometimes answers HTTP 200 with
    {"type": "error", "error": {"type": "upstream_error", "message": "Our servers are currently busy..."}}, on which
    llm_structured.chat raised KeyError('choices') at once (2026-10-29)."""
    import urllib.error, urllib.request
    if attempts is None:  # WORKFLOW_LLM_ATTEMPTS: 0 = until it succeeds (busy / rate limit / 5xx / dropped connection)
        attempts = int(os.environ.get("WORKFLOW_LLM_ATTEMPTS", "8"))
    body = json.dumps({**request_parameters(env, model), "messages": messages}).encode()
    problem, attempt = None, -1
    while True:
        attempt += 1
        if attempts and attempt >= attempts:
            raise RuntimeError(f"relay gave no answer after {attempt} tries: {str(problem)[:300]}")
        if attempt and attempt % 5 == 0:
            print(f"retry {attempt}: {str(problem)[:160]}", flush=True)
        limiter.wait()
        request = urllib.request.Request(env["OPENAI_BASE_URL"].rstrip("/") + "/chat/completions", data=body, headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {env['OPENAI_API_KEY']}", "User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                answer = json.loads(response.read())
            if answer.get("choices"):
                if answer.get("usage"):
                    usage.append(answer["usage"])
                return answer["choices"][0]["message"]["content"]
            problem = answer.get("error") or answer
        except urllib.error.HTTPError as error:
            if error.code not in (408, 409, 425, 429) and error.code < 500:
                raise
            problem = f"HTTP {error.code}"
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, ValueError) as error:
            problem = error
        time.sleep(min(120., 5. * 2 ** min(attempt, 5)))


class SharedLimiter:
    """llm_probe's limiter interface (``wait``) on the workflow's cross-process request log."""

    def wait(self):
        llm._throttle()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=Path, required=True)
    ap.add_argument("--rooms", type=Path, required=True, help="JSON list of row indices")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--base-url", default=RELAY_BASE_URL)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--model", help="model id (default: the env file's OPENAI_MODEL), e.g. gpt-6.1-sol")
    ap.add_argument("--effort", default="medium", help="reasoning effort (FASTFILL_LLM_REASONING_EFFORT)")
    ap.add_argument("--rpm", type=int, default=30)
    ap.add_argument("--rpm-file", type=Path, required=True)
    a = ap.parse_args()
    if urlparse(a.base_url).hostname not in RELAY_HOSTS:
        raise SystemExit("--base-url must be a relay entry")
    env = load_env(RELAY_ENV_FILE)
    env["OPENAI_BASE_URL"] = a.base_url.rstrip("/")  # in memory only; the file is not touched
    env["FASTFILL_LLM_REASONING_EFFORT"] = a.effort  # llm_baseline.request_parameters reads it
    model = a.model or env["OPENAI_MODEL"]
    os.environ["WORKFLOW_RPM"], os.environ["WORKFLOW_RPM_FILE"] = str(a.rpm), str(a.rpm_file.resolve())
    rows = [migrate_legacy_row(json.loads(l)) for l in a.rows.read_text().splitlines() if l.strip()]
    rooms = json.loads(a.rooms.read_text())
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "config.json").write_text(json.dumps({"protocol": "fastfill.v2.ops.llm_probe (one request, no repair)",
                                                   "model": model, "effort": a.effort, "base_url": env["OPENAI_BASE_URL"], "rpm": a.rpm,
                                                   "rows": str(a.rows), "rooms": len(rooms)}, indent=1))
    limiter = SharedLimiter()

    def one(k):
        condition = rows[k]["condition"]
        messages = [{"role": "system", "content": instructions(condition, False)},
                    {"role": "user", "content": request_text(condition, None)}]
        usage, start, reply, error, layout, problems = [], time.perf_counter(), None, None, None, None
        try:
            reply = chat(env, model, messages, limiter=limiter, usage=usage)
            layout = parse(reply, condition, None)
            problems = workflow_problems(layout, condition)
        except Exception as e:  # keep the raw reply for inspection
            error = f"{type(e).__name__}: {e}"
        out = {"k": k, "source": rows[k].get("provenance", {}).get("source"), "latency_s": time.perf_counter() - start,
               "usage": usage, "error": error, "problems": problems, "layout": layout, "reply": reply,
               "system": messages[0]["content"], "request": messages[1]["content"], "base_url": env["OPENAI_BASE_URL"]}
        (a.out / f"room_{k:03d}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str))
        print(k, out["source"], f"{out['latency_s']:.0f}s", "error " + error[:80] if error else f"{len(problems or [])} problems",
              flush=True)

    def done(k):
        f = a.out / f"room_{k:03d}.json"
        return f.is_file() and not json.loads(f.read_text())["error"]
    with ThreadPoolExecutor(a.workers) as pool:
        list(pool.map(one, [k for k in rooms if not done(k)]))
    results = {k: json.loads((a.out / f"room_{k:03d}.json").read_text()) for k in rooms}
    with (a.out / "predictions.jsonl").open("w") as f:  # aligned with --rows; rooms not run have no layout
        for k in range(len(rows)):
            r = results.get(k)
            f.write(json.dumps({"layout": r["layout"] if r else None, "error": r["error"] if r else "not run",
                                "latency_s": r["latency_s"] if r else None}) + "\n")
    print(json.dumps({"model": model, "rooms": len(results), "errors": sum(bool(r["error"]) for r in results.values())}))


if __name__ == "__main__":
    main()
