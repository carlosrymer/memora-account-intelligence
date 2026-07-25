# DPA / legal review — data residency constraint

Date: 2026-02-11
Account: Northwind Retail Group

Attendees: Dana Liu, Helena Vogt (Northwind Legal), Sam Okafor, Carlos R.

Northwind Legal completed the data processing agreement review. Helena introduced a hard
constraint that was not in the original scope: all EU customer data must remain resident
in the EU. Specifically, EU profiles must be stored and processed in eu-central-1
(Frankfurt) and must not transit US regions, including for backup or analytics.

This traces to DPA clause 7.3, which Helena will not waive. Roughly 2.8M of the 9.4M
profiles are EU-resident.

Dana was clear this is non-negotiable and gates go-live for the EU segment. Carlos noted
this likely requires a dual-region deployment topology, which was not in the January
estimate.

Action: Lumen to come back with a dual-region architecture and cost delta by Feb 25.
