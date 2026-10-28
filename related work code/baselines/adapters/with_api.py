"""Run a command with our OpenAI-compatible endpoint in the environment (never prints the key).

    python with_api.py <command ...>
Exports OPENAI_BASE_URL / OPENAI_API_KEY / OPENAI_MODEL (and OPENAI_API_BASE for old langchain) from
~/.fastfill_api.env, read through fastfill.v2.llm_baseline.load_env.
"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))  # the project root (fastfill-v4)
sys.path.insert(0, os.path.join(ROOT, "fastfill-main"))
from fastfill.v2.llm_baseline import load_env

# the relay's key file, read in place (FASTFILL_API_ENV overrides the default location, e.g. on a server)
env = load_env(os.path.expanduser(os.environ.get("FASTFILL_API_ENV", "~/.fastfill_api.env")))
for key in ("OPENAI_BASE_URL", "OPENAI_API_KEY", "OPENAI_MODEL"):
    if env.get(key):
        os.environ[key] = env[key]
if os.environ.get("BASELINE_BASE_URL"):  # override the env file's relay (same key)
    os.environ["OPENAI_BASE_URL"] = os.environ["BASELINE_BASE_URL"]
os.environ["OPENAI_MODEL"] = os.environ.get("BASELINE_MODEL", "gpt-6.1-sol")  # the model the user picked for baselines
os.environ.setdefault("BASELINE_REASONING_EFFORT", "medium")
os.environ.setdefault("OPENAI_API_BASE", os.environ.get("OPENAI_BASE_URL", ""))
# the relay is Cloudflare-fronted and rejects default client user agents (see llm_baseline.USER_AGENT)
os.environ["PYTHONPATH"] = os.path.dirname(os.path.abspath(__file__)) + os.pathsep + os.environ.get("PYTHONPATH", "")
if len(sys.argv) > 1:
    os.execvp(sys.argv[1], sys.argv[1:])
