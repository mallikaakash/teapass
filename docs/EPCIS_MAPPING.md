# TeaPass EPCIS profile v1

This adapter is a strict, bounded subset of GS1 EPCIS 2.0, using the official [ObjectEvent vocabulary](https://ref.gs1.org/epcis/ObjectEvent) and [2.0 artefacts](https://ref.gs1.org/standards/epcis/2.0.0/artefacts).

| TeaPass field | EPCIS field |
| --- | --- |
| operation UUID | eventID as urn:uuid |
| batch UUID | epcList single urn:uuid |
| occurred_at normalized UTC | eventTime, eventTimeZoneOffset +00:00 |
| CREATE_BATCH | ObjectEvent, ADD |
| Observation/correction | ObjectEvent, OBSERVE |
| Exact signed command/signature | teapass:signed extension |

The extension namespace is a placeholder vocabulary identifier, not a claim of GS1 registration or a remotely fetched resource. The only accepted context is the pinned official context plus that declared prefix; the server never fetches remote JSON-LD URLs. Wrapper identifiers, action and timestamp must exactly match the signed command.

Import is all-or-nothing, limited to 100 signed events and the API body cap. Only the authenticated signer's commands can be imported. Re-importing an identical event returns ALREADY_RECORDED; altered signatures/commands cannot overwrite history. Export is private/tenant-scoped. Encrypted commercial fields remain encrypted.

This is not a general EPCIS server or official GS1 conformance certification. TransformationEvent/quantity mappings, arbitrary third-party CSV, GS1 master data, actual Tea Board/GTAC payloads and full external interoperability are not yet supported. Unsupported fields fail rather than silently losing meaning or leaking plaintext commercial quantities.
