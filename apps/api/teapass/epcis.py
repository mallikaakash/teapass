"""Strict TeaPass EPCIS 2.0 profile. No remote contexts or plaintext commercial quantities."""

from datetime import UTC, datetime
from typing import Literal

from fastapi import HTTPException
from pydantic import Field

from teapass.schemas import SignedBatch, SignedEvent, StrictModel

CONTEXT = "https://ref.gs1.org/standards/epcis/2.0.0/epcis-context.jsonld"
EXTENSION = "https://teapass.example/vocab/"


class Event(StrictModel):
    type: Literal["ObjectEvent"]
    eventID: str
    eventTime: str
    eventTimeZoneOffset: Literal["+00:00"]
    action: Literal["ADD", "OBSERVE"]
    epcList: list[str] = Field(min_length=1, max_length=1)
    signed: SignedBatch | SignedEvent = Field(alias="teapass:signed")


class Body(StrictModel):
    eventList: list[Event] = Field(min_length=1, max_length=100)


class Document(StrictModel):
    context: list[str | dict[str, str]] = Field(alias="@context")
    type: Literal["EPCISDocument"]
    schemaVersion: Literal["2.0"]
    creationDate: str
    mapping: Literal["teapass-epcis-1"] = Field(alias="teapass:mapping")
    epcisBody: Body

    def signed_events(self):
        if self.context != [CONTEXT, {"teapass": EXTENSION}]:
            raise HTTPException(422, "UNSUPPORTED_EPCIS_CONTEXT")
        commands = []
        for event in self.epcisBody.eventList:
            c = event.signed.command
            expected_action = "ADD" if c.command_type == "CREATE_BATCH" else "OBSERVE"
            if (
                event.eventID != f"urn:uuid:{c.operation_id}"
                or event.epcList != [f"urn:uuid:{c.batch_id}"]
                or event.eventTime != c.model_dump(mode="json")["occurred_at"]
                or event.action != expected_action
            ):
                raise HTTPException(422, "EPCIS_SIGNED_BINDING_MISMATCH")
            commands.append(event.signed)
        if len({c.command.operation_id for c in commands}) != len(commands):
            raise HTTPException(422, "DUPLICATE_EPCIS_EVENT")
        return commands


def export_document(events):
    result = []
    # Only observation/creation/correction records are importable with this profile.
    for event in events:
        if event.signed_command["command_type"] not in {"CREATE_BATCH", "APPEND_EVENT"}:
            continue
        c = event.signed_command
        result.append(
            {
                "type": "ObjectEvent",
                "eventID": f"urn:uuid:{event.id}",
                "eventTime": c["occurred_at"],
                "eventTimeZoneOffset": "+00:00",
                "action": "ADD" if c["command_type"] == "CREATE_BATCH" else "OBSERVE",
                "epcList": [f"urn:uuid:{event.batch_id}"],
                "teapass:signed": {"command": c, "signature": event.signature},
            }
        )
    return {
        "@context": [CONTEXT, {"teapass": EXTENSION}],
        "type": "EPCISDocument",
        "schemaVersion": "2.0",
        "creationDate": datetime.now(UTC).isoformat(),
        "teapass:mapping": "teapass-epcis-1",
        "epcisBody": {"eventList": result},
    }
