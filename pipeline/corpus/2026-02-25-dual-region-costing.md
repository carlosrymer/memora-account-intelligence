# Dual-region architecture and cost delta

Date: 2026-02-25
Account: Northwind Retail Group

Attendees: Dana Liu, Marcus Bell, Carlos R.

Presented dual-region topology: primary in us-east-1, EU enclave in eu-central-1, with
identity resolution running independently per region. No cross-region profile joins.

Cost delta for dual-region is approximately $55k in year one, driven by duplicated
compute for identity resolution and a second Kafka cluster.

Dana's reaction: the requirement stands, but $355k total exceeds the approved $300k. She
will take it to the CFO. Flagged that the CFO is running a company-wide cost review this
quarter, so the timing is poor.

Marcus separately confirmed the identity resolution work landed at 2.5 sprints, slightly
over his January estimate.
