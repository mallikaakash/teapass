"""Opt-in real chain integration; ordinary CI does not claim this ran without the devnet."""

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from test_workflows import encrypted, grant, post, signed

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEAPASS_LIVE_CHAIN_EVIDENCE"), reason="Opt-in real Midnight devnet required"
)


@pytest.mark.parametrize(
    "binding", ["matching", "wrong-reference", "wrong-material", "wrong-policy"]
)
def test_real_public_alias_checks_note_batch_material_and_live_revocation(env, binding):
    path = Path(os.environ["TEAPASS_LIVE_CHAIN_EVIDENCE"])
    artifact = json.loads(path.read_text())
    public = json.loads(path.with_name("public-claims-local.json").read_text())["claims"][0]
    assert artifact["complete"] and artifact["networkId"] == "undeployed"
    env.settings.midnight_contract_address = artifact["contractAddress"]
    env.settings.midnight_verifier_url = "http://127.0.0.1:6301"
    batch = env.batch(
        batch_id=artifact["publicBinding"]["batchId"]
        if binding != "wrong-reference"
        else str(uuid4()),
        material_class="BLENDED_TEA" if binding != "wrong-material" else "GREEN_LEAF",
    )
    created = env.client.post("/v1/batches", json=batch, headers=env.headers())
    assert created.status_code == 201, created.text
    _, head = grant(env, (batch, created.json()), "lab", "lab_attest")
    evidence = signed(
        env,
        (batch, head),
        "ATTEST_LAB",
        name="lab",
        attestation_id=str(uuid4()),
        commitment=public["claimId"],
        policy_id=public["policyId"] if binding != "wrong-policy" else "e" * 64,
        expires_at=(datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        encrypted_payload=encrypted(),
    )
    assert post(env, evidence, "lab").status_code == 201
    result = env.client.get("/v1/public/batches/" + batch["command"]["public_alias"])
    assert result.status_code == 200, result.text
    body = result.json()
    if binding == "matching":
        assert body["verification_status"] == "INVALID_CLAIMS", body
        assert body["claims"][0]["status"] == "INVALID"
        assert "LAB_REVOKED" in body["claims"][0]["reasons"]
    else:
        assert body["verification_status"] == "NOT_VERIFIED", body
        assert body["claims"] == []
