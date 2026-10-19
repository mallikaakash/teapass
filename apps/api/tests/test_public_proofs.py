from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi import HTTPException

from teapass.public_proofs import read_proof


def proof():
    return dict(
        claimId="a" * 64,
        claimType="LAB_MEASUREMENT_AT_OR_BELOW_POLICY_THRESHOLD",
        status="VALID",
        reasons=[],
        batchCommitment="b" * 64,
        batchReference="c" * 64,
        materialClass="3",
        labAuthority="c" * 64,
        policyId="d" * 64,
        expiresAt=str(int((datetime.now(UTC) + timedelta(hours=1)).timestamp())),
        policy=dict(
            analyte="e" * 64,
            method="f" * 64,
            unit="1",
            threshold="5",
            validFrom="1",
            validUntil="4102444800",
        ),
        network="undeployed",
        contractAddress="f" * 64,
        finalizedBlockHash="a" * 64,
        stateBlockHash="b" * 64,
        checkedAt=datetime.now(UTC).isoformat(),
        trustBasis="CONFIGURED_NODE_AND_INDEXER_WITH_PINNED_VERIFIER_KEYS",
        limitations=["Synthetic laboratory policy only"],
    )


@pytest.mark.parametrize(
    "change", ["valid", "revoked", "stale", "wrong-contract", "expired", "private-data"]
)
def test_public_verification_allowlist_freshness_and_binding(env, change):
    env.settings.midnight_verifier_url = "http://verifier.example"
    env.settings.midnight_contract_address = "f" * 64
    value = proof()
    if change == "revoked":
        value.update(status="INVALID", reasons=["LAB_REVOKED"])
    elif change == "stale":
        value["checkedAt"] = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    elif change == "wrong-contract":
        value["contractAddress"] = "e" * 64
    elif change == "expired":
        value["expiresAt"] = "1"
    elif change == "private-data":
        value["measurement"] = 3
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=value))
    ) as client:
        if change in {"valid", "revoked"}:
            result = read_proof(env.settings, "a" * 64, client=client)
            assert result.status == ("VALID" if change == "valid" else "INVALID")
        else:
            with pytest.raises(HTTPException) as exc:
                read_proof(env.settings, "a" * 64, client=client)
            assert exc.value.status_code == 503
