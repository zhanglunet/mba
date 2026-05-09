"""Create an AgentBay browser session, print SessionId + ResourceUrl, exit
without deleting so the user can open the URL in a browser."""
import os
import sys
from pathlib import Path


def load_env(path: Path) -> dict:
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def main() -> int:
    env = load_env(Path.home() / "mba" / ".env")
    api_key = env["WUYING_API_KEY"]
    image_id = env.get("WUYING_IMAGE_ID", "browser_latest")

    from agentbay import AgentBay
    from agentbay.session_params import CreateSessionParams

    client = AgentBay(api_key=api_key)
    result = client.create(CreateSessionParams(image_id=image_id))
    session = getattr(result, "session", None) or result
    session_id = getattr(session, "session_id", None) or getattr(session, "id", "?")

    # The ResourceUrl is on the raw API response. The SDK exposes it via
    # session.resource_url; fall back to digging into the result if needed.
    resource_url = getattr(session, "resource_url", None)
    if not resource_url:
        for attr in ("data", "raw", "_raw", "response"):
            obj = getattr(result, attr, None)
            if isinstance(obj, dict):
                resource_url = obj.get("ResourceUrl") or obj.get("resourceUrl")
                if resource_url:
                    break

    print("===")
    print(f"SESSION_ID={session_id}")
    print(f"RESOURCE_URL={resource_url}")
    print("===")
    print("Session left ALIVE. To delete later, run:")
    print(f'  python3 -c "from agentbay import AgentBay; c=AgentBay(api_key=\\"{api_key}\\"); '
          f'from agentbay.session import Session; '
          f'c.delete_by_id(\\"{session_id}\\") if hasattr(c,\\"delete_by_id\\") else None"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
