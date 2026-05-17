"""Create an AgentBay browser session, print SessionId + ResourceUrl, exit
without deleting so the user can open the URL in a browser."""
import sys
import shlex
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


def main() -> int:
    if not ENV_PATH.is_file():
        print(f"ERROR: env file not found: {ENV_PATH}", file=sys.stderr)
        return 2
    env = load_env(ENV_PATH)
    api_key = env.get("WUYING_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        print(f"ERROR: WUYING_API_KEY not set in {ENV_PATH}", file=sys.stderr)
        return 2
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
    print(
        f"  cd {shlex.quote(str(ROOT))} && "
        "python3 -c \"from pathlib import Path; "
        "from agentbay import AgentBay; "
        "env=dict(line.strip().split('=', 1) for line in Path('.env').read_text().splitlines() "
        "if line.strip() and not line.lstrip().startswith('#') and '=' in line); "
        "c=AgentBay(api_key=env['WUYING_API_KEY']); "
        f"c.delete_by_id('{session_id}') if hasattr(c, 'delete_by_id') else None\""
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
