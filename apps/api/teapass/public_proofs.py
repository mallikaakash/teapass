from datetime import UTC, datetime
from typing import Literal

import httpx
from fastapi import HTTPException
from pydantic import AwareDatetime, Field

from teapass.schemas import StrictModel
from teapass.workflow_schemas import Hash


class PublicPolicy(StrictModel):
    analyte: Hash
    method: Hash
    unit: str = Field(pattern=r"^[0-9]{1,3}$")
    threshold: str = Field(pattern=r"^[0-9]{1,20}$")
    validFrom: str = Field(pattern=r"^[0-9]{1,20}$")
    validUntil: str = Field(pattern=r"^[0-9]{1,20}$")


class PublicProof(StrictModel):
    claimId: Hash
    claimType: Literal["LAB_MEASUREMENT_AT_OR_BELOW_POLICY_THRESHOLD"]
    status: Literal["VALID", "INVALID"]
    reasons: list[Literal["LAB_REVOKED", "POLICY_REVOKED", "EXPIRED", "POLICY_NOT_YET_VALID"]]
    batchCommitment: Hash
    batchReference: Hash
    materialClass: Literal["1", "2", "3"]
    labAuthority: Hash
    policyId: Hash
    expiresAt: str = Field(pattern=r"^[0-9]{1,20}$")
    policy: PublicPolicy
    network: str
    contractAddress: Hash
    finalizedBlockHash: Hash
    stateBlockHash: Hash
    checkedAt: AwareDatetime
    trustBasis: Literal["CONFIGURED_NODE_AND_INDEXER_WITH_PINNED_VERIFIER_KEYS"]
    limitations: list[str] = Field(max_length=5)


def read_proof(settings, claim_id, *, client=None):
    if not settings.midnight_verifier_url or not settings.midnight_contract_address:
        raise HTTPException(503, "MIDNIGHT_NOT_CONFIGURED")
    owned_client = client is None
    client = client or httpx.Client(timeout=10, follow_redirects=False)
    try:
        response = client.get(settings.midnight_verifier_url.rstrip("/") + "/claims/" + claim_id)
        if response.status_code == 404:
            raise HTTPException(404, "CLAIM_NOT_FOUND")
        response.raise_for_status()
        proof = PublicProof.model_validate(response.json())
        age = (datetime.now(UTC) - proof.checkedAt).total_seconds()
        if (
            proof.claimId != claim_id
            or proof.contractAddress != settings.midnight_contract_address
            or proof.network != settings.midnight_network
            or not -5 <= age <= 15
        ):
            raise ValueError("Unbound or stale verification")
        if proof.status == "VALID" and (
            proof.reasons
            or int(proof.expiresAt) <= datetime.now(UTC).timestamp()
            or int(proof.policy.validUntil) <= datetime.now(UTC).timestamp()
            or int(proof.policy.validFrom) > datetime.now(UTC).timestamp()
        ):
            raise ValueError("Expired claim marked valid")
        return proof
    except (httpx.HTTPError, ValueError, TypeError):
        raise HTTPException(503, "CHAIN_VERIFICATION_UNAVAILABLE") from None
    finally:
        if owned_client:
            client.close()
