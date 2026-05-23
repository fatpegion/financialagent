"""Upload the A-share MCP wheel to Alibaba Cloud OSS.

The script reads credentials from environment variables so secrets do not need
to be written into the repository.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


DEFAULT_WHEEL = (
    Path(__file__).resolve().parents[1]
    / "a-share-mcp-is-just-i-need"
    / "dist"
    / "a_share_finance_mcp-0.1.1-py3-none-any.whl"
)
DEFAULT_ENV_FILE = Path(__file__).resolve().parents[1] / "oss_upload.env"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name and name not in os.environ:
            os.environ[name] = value


def main() -> int:
    load_env_file(DEFAULT_ENV_FILE)

    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", default=str(DEFAULT_WHEEL))
    parser.add_argument("--bucket", default=os.getenv("OSS_BUCKET"))
    parser.add_argument("--endpoint", default=os.getenv("OSS_ENDPOINT", "oss-cn-beijing.aliyuncs.com"))
    parser.add_argument("--object-key", default=os.getenv("OSS_OBJECT_KEY", "mcp/a_share_finance_mcp-0.1.1-py3-none-any.whl"))
    parser.add_argument("--expires", type=int, default=int(os.getenv("OSS_SIGNED_URL_EXPIRES", "604800")))
    args = parser.parse_args()

    try:
        import oss2
    except Exception as exc:
        print("Missing Python package: oss2", file=sys.stderr)
        print("Install it with: python -m pip install oss2", file=sys.stderr)
        print(f"Import error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    access_key_id = os.getenv("OSS_ACCESS_KEY_ID")
    access_key_secret = os.getenv("OSS_ACCESS_KEY_SECRET")
    security_token = os.getenv("OSS_SECURITY_TOKEN")

    missing = [
        name
        for name, value in {
            "OSS_BUCKET": args.bucket,
            "OSS_ACCESS_KEY_ID": access_key_id,
            "OSS_ACCESS_KEY_SECRET": access_key_secret,
        }.items()
        if not value
    ]
    if missing:
        print("Missing required environment variables: " + ", ".join(missing), file=sys.stderr)
        return 2

    wheel_path = Path(args.wheel).resolve()
    if not wheel_path.exists():
        print(f"Wheel does not exist: {wheel_path}", file=sys.stderr)
        return 2

    endpoint = args.endpoint
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        public_endpoint = endpoint.split("://", 1)[1]
        endpoint_url = endpoint
    else:
        public_endpoint = endpoint
        endpoint_url = "https://" + endpoint

    if security_token:
        auth = oss2.StsAuth(access_key_id, access_key_secret, security_token)
    else:
        auth = oss2.Auth(access_key_id, access_key_secret)

    bucket = oss2.Bucket(auth, endpoint_url, args.bucket)
    headers = {
        "Content-Type": "application/octet-stream",
    }
    bucket.put_object_from_file(args.object_key, str(wheel_path), headers=headers)

    object_key_url = args.object_key.replace(" ", "%20")
    public_url = f"https://{args.bucket}.{public_endpoint}/{object_key_url}"
    signed_url = bucket.sign_url("GET", args.object_key, args.expires, slash_safe=True)

    print("Upload complete.")
    print(f"Wheel: {wheel_path}")
    print(f"OSS object: oss://{args.bucket}/{args.object_key}")
    print(f"Public URL: {public_url}")
    print(f"Signed URL ({args.expires}s): {signed_url}")
    print("\nBailian uvx args:")
    print('  "--from",')
    print(f'  "{signed_url}",')
    print('  "a-share-finance-mcp"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
