"""Create the RS256 key pair used to sign access tokens (backend/keys/, never committed).

Usage (from backend/):  python scripts/generate_jwt_keys.py [--force]
"""

import argparse
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import _bootstrap  # noqa: F401
from app.core.config import get_settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="overwrite existing keys")
    args = parser.parse_args()
    settings = get_settings()
    private_path, public_path = settings.jwt_private_key_path, settings.jwt_public_key_path
    if private_path.exists() and not args.force:
        print(f"Keys already exist at {private_path.parent} (use --force to replace them).")
        return 0
    private_path.parent.mkdir(parents=True, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    private_path.write_bytes(
        key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    )
    private_path.chmod(0o600)
    public_path.write_bytes(
        key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    )
    print(f"Wrote {private_path} and {public_path}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
