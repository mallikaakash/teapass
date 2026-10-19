"""Explicit local provisioning; only public signing material is accepted."""

import argparse
import base64
import json
from pathlib import Path

from sqlalchemy.exc import IntegrityError

from teapass.config import Settings
from teapass.db import make_database
from teapass.models import Actor, Organization


def main():
    parser = argparse.ArgumentParser(description="Enroll an organization and its first admin")
    parser.add_argument("--organization", required=True)
    parser.add_argument(
        "--subject", required=True, help="Exact subject from the configured OIDC issuer"
    )
    parser.add_argument(
        "--signing-public-key-file",
        type=Path,
        required=True,
        help="File containing a base64-encoded 32-byte Ed25519 public key",
    )
    args = parser.parse_args()
    key = base64.b64decode(args.signing_public_key_file.read_text().strip(), validate=True)
    if (
        len(key) != 32
        or not 1 <= len(args.organization) <= 200
        or not 1 <= len(args.subject) <= 255
    ):
        parser.error("Invalid public key, organization name or subject")
    engine, sessions = make_database(Settings())
    try:
        with sessions() as db, db.begin():
            organization = Organization(name=args.organization)
            db.add(organization)
            db.flush()
            admin = Actor(
                org_id=organization.id, subject=args.subject, role="admin", signing_public_key=key
            )
            db.add(admin)
            db.flush()
            result = {
                "org_id": str(organization.id),
                "actor_id": str(admin.id),
                "role": "admin",
                "on_chain_issuer_authority": False,
            }
        print(json.dumps(result))
    except IntegrityError:
        raise SystemExit(
            "Enrollment conflicts with an existing subject; no changes committed"
        ) from None
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
