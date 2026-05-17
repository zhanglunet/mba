"""Smoke-test the WUYING_API_KEY in the repo .env by spinning up an AgentBay
browser session, fetching the CDP endpoint, and tearing it down.
"""
import asyncio
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"


def load_env(path: Path) -> dict:
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


async def main() -> int:
    if not ENV_PATH.is_file():
        print(f"ERROR: env file not found: {ENV_PATH}", file=sys.stderr)
        return 2
    env = load_env(ENV_PATH)
    api_key = env.get("WUYING_API_KEY")
    image_id = env.get("WUYING_IMAGE_ID", "browser_latest")
    if not api_key or api_key == "your_api_key_here":
        print(f"ERROR: WUYING_API_KEY not set in {ENV_PATH}", file=sys.stderr)
        return 2

    masked = f"{api_key[:8]}…{api_key[-4:]}"
    print(f"[1/5] api_key={masked}  image_id={image_id}")

    from agentbay import AgentBay
    from agentbay.session_params import CreateSessionParams
    from agentbay.browser.browser import BrowserOption

    t0 = time.time()
    client = AgentBay(api_key=api_key)
    print(f"[2/5] AgentBay client constructed ({time.time()-t0:.2f}s)")

    t0 = time.time()
    result = client.create(CreateSessionParams(image_id=image_id))
    session = getattr(result, "session", None) or result
    session_id = getattr(session, "session_id", None) or getattr(session, "id", "?")
    print(f"[3/5] session created: {session_id} ({time.time()-t0:.2f}s)")

    try:
        t0 = time.time()
        ok = await session.browser.initialize_async(BrowserOption())
        print(f"[4/5] browser.initialize_async -> {ok} ({time.time()-t0:.2f}s)")
        endpoint = session.browser.get_endpoint_url()
        print(f"[5/5] CDP endpoint: {endpoint}")
    finally:
        try:
            client.delete(session)
            print("cleanup: session deleted via client.delete()")
        except Exception:
            try:
                session.delete()
                print("cleanup: session deleted via session.delete()")
            except Exception as e:
                print(f"cleanup: failed to delete session: {e!r}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except Exception as e:
        print(f"FATAL: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
