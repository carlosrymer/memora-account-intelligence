"""Author the synthetic account corpus: 6 months of meeting notes for one B2B account.

The account is fictional. The notes are written so that several facts *change over time*
— budget, go-live date, signoff owner, integration scope, seat count. That is the whole
point: an account team's hardest questions are not "what was said" but "what is true
now, and when did it change".

Each note is deliberately written the way real notes are written: numbers and names
buried in prose, decisions stated once, no summary block. Details that summarization-based
memory tends to drop (dollar amounts, region identifiers, clause numbers, ticket IDs) are
scattered throughout on purpose.

Run: python build_corpus.py
"""

from __future__ import annotations

import json
from pathlib import Path

CORPUS_DIR = Path(__file__).parent / "corpus"

# (filename, date, title, body)
NOTES: list[tuple[str, str, str, str]] = [
    (
        "2026-01-14-kickoff.md",
        "2026-01-14",
        "Northwind Retail Group — migration kickoff",
        """Attendees: Dana Liu (CTO, Northwind), Priya Raman (Dir. Lifecycle Marketing),
Sam Okafor (Lumen CDP, AE), Carlos R. (Lumen CDP, Solutions).

Northwind is consolidating three legacy marketing databases onto Lumen CDP. Dana confirmed
the board approved a migration budget of $300k for calendar 2026. She is the executive
sponsor and owns final signoff on the migration plan.

Target go-live is June 30, 2026, aligned to their pre-holiday campaign planning cycle.
Priya flagged that anything past July puts the Black Friday calendar at risk.

Initial contract is for 1,200 seats across marketing and analytics. Integration scope for
go-live is Salesforce (system of record for accounts) and Braze (outbound messaging).
Priya's team currently sends roughly 4.2M messages/month through Braze.

Dana asked us to hold a standing biweekly Tuesday sync. Action items: Lumen to deliver a
data mapping draft by Jan 28; Northwind to nominate a data steward per source system.""",
    ),
    (
        "2026-01-28-data-mapping.md",
        "2026-01-28",
        "Data mapping review",
        """Attendees: Priya Raman, Marcus Bell (VP Engineering, Northwind), Carlos R.

Walked the data mapping draft. Three legacy sources: an on-prem Oracle instance (customer
master, ~9.4M profiles), a Postgres loyalty database (~3.1M members), and a Segment
warehouse export.

Marcus raised that the loyalty database has no reliable primary key across 2019-2021
records — roughly 400k rows will need fuzzy identity resolution. He estimated two
engineering sprints. This is the first real schedule risk anyone has named.

Priya confirmed the data steward assignments: Ana Duarte for Oracle, Tom Reyes for loyalty,
Priya herself for Segment.

No change to budget or timeline discussed. Go-live remains June 30.""",
    ),
    (
        "2026-02-11-dpa-review.md",
        "2026-02-11",
        "DPA / legal review — data residency constraint",
        """Attendees: Dana Liu, Helena Vogt (Northwind Legal), Sam Okafor, Carlos R.

Northwind Legal completed the data processing agreement review. Helena introduced a hard
constraint that was not in the original scope: all EU customer data must remain resident
in the EU. Specifically, EU profiles must be stored and processed in eu-central-1
(Frankfurt) and must not transit US regions, including for backup or analytics.

This traces to DPA clause 7.3, which Helena will not waive. Roughly 2.8M of the 9.4M
profiles are EU-resident.

Dana was clear this is non-negotiable and gates go-live for the EU segment. Carlos noted
this likely requires a dual-region deployment topology, which was not in the January
estimate.

Action: Lumen to come back with a dual-region architecture and cost delta by Feb 25.""",
    ),
    (
        "2026-02-25-dual-region-costing.md",
        "2026-02-25",
        "Dual-region architecture and cost delta",
        """Attendees: Dana Liu, Marcus Bell, Carlos R.

Presented dual-region topology: primary in us-east-1, EU enclave in eu-central-1, with
identity resolution running independently per region. No cross-region profile joins.

Cost delta for dual-region is approximately $55k in year one, driven by duplicated
compute for identity resolution and a second Kafka cluster.

Dana's reaction: the requirement stands, but $355k total exceeds the approved $300k. She
will take it to the CFO. Flagged that the CFO is running a company-wide cost review this
quarter, so the timing is poor.

Marcus separately confirmed the identity resolution work landed at 2.5 sprints, slightly
over his January estimate.""",
    ),
    (
        "2026-03-03-budget-cut.md",
        "2026-03-03",
        "Budget decision — CFO cost review",
        """Attendees: Dana Liu, Sam Okafor.

Bad news. The CFO's cost review did not approve the increase. Worse, the migration budget
was cut from $300k to $240k for calendar 2026. Dana was explicit that this is a hard cap,
not a target.

Dana's guidance: keep the EU residency requirement (it is a legal obligation, not a
preference) and find scope to cut elsewhere. She suggested we look at deferring rather
than descoping.

Sam asked directly whether the June 30 go-live survives a $60k cut plus dual-region work.
Dana said she did not know yet and asked for options by the next sync.

Signoff authority is unchanged — Dana still owns it.""",
    ),
    (
        "2026-03-17-phasing-options.md",
        "2026-03-17",
        "Phasing options under the $240k cap",
        """Attendees: Dana Liu, Priya Raman, Marcus Bell, Carlos R.

Presented three options against the $240k cap:

Option A — full scope, slip go-live to Q4. Rejected; misses Black Friday entirely.
Option B — US-only at go-live, EU enclave as phase 2. Fits the cap at ~$232k.
Option C — cut Segment source from initial migration. Priya rejected; Segment is where
campaign attribution lives.

Consensus formed around Option B. The EU enclave moves to phase 2 with its own budget line
in 2027. Important nuance Helena will need to sign off on: EU profiles are *excluded* from
the initial migration entirely rather than migrated to a US region, which keeps clause 7.3
satisfied.

Not yet a decision — Dana wants Helena's confirmation before committing.""",
    ),
    (
        "2026-04-07-timeline-slip.md",
        "2026-04-07",
        "Timeline slip and Braze contract change",
        """Attendees: Dana Liu, Priya Raman, Marcus Bell, Carlos R.

Two changes.

First, go-live slips from June 30 to August 15. Cause is data quality, not budget: the
fuzzy identity resolution on the loyalty database is producing a 6.1% false-merge rate
against a 1% acceptance threshold. Marcus needs two more sprints. Priya accepted August 15
but noted the Black Friday calendar now has no slack.

Second, Braze is out of scope. Northwind's Braze contract ends July 31 and procurement has
decided not to renew. Priya's team will run outbound on a replacement to be selected in Q2.
So go-live integration scope is now Salesforce only, pending that selection.

Helena confirmed Option B satisfies clause 7.3. EU enclave is formally phase 2.""",
    ),
    (
        "2026-04-21-sponsor-handoff.md",
        "2026-04-21",
        "Sponsor handoff — Dana on leave",
        """Attendees: Dana Liu, Marcus Bell, Sam Okafor.

Dana begins parental leave on May 1 and returns June 15. Marcus Bell takes over as
interim executive sponsor and holds migration signoff authority in the interim.

Dana was specific about the boundary: Marcus can approve scope and schedule changes, but
any change to the $240k budget cap must wait for her return or go to the CFO directly.
Marcus does not have budget authority.

Handoff notes captured: EU enclave deferred to phase 2, go-live August 15, Salesforce-only
at go-live, 1,200 seats.

Standing sync continues; Marcus will chair.""",
    ),
    (
        "2026-05-05-identity-resolution-fix.md",
        "2026-05-05",
        "Identity resolution — threshold fix",
        """Attendees: Marcus Bell, Tom Reyes, Carlos R.

Marcus chairing. False-merge rate is down to 0.7%, under the 1% threshold, after Tom's team
added phone-number normalization and a household-level disambiguation rule.

Roughly 340k of the original 400k problem rows now resolve cleanly. The remaining ~60k will
be loaded as unmerged singletons and flagged for manual review post-go-live. Tom estimates
that queue at about 6 weeks of part-time work for two analysts.

Marcus approved this approach — within his scope authority. August 15 go-live holds.""",
    ),
    (
        "2026-05-19-seat-expansion.md",
        "2026-05-19",
        "Seat expansion and partial budget restoration",
        """Attendees: Marcus Bell, Priya Raman, Sam Okafor, Dana Liu (dialed in briefly).

Dana joined for ten minutes from leave specifically to handle budget, since Marcus does not
hold that authority.

Two commercial changes. First, seat count expands from 1,200 to 1,500 — Northwind's
analytics org is being folded into the same workspace. Second, the CFO released partial
relief: the 2026 migration budget is restored from $240k to $265k, conditional on the EU
enclave remaining deferred to 2027 and no further scope additions this year.

Dana was explicit that $265k is the new cap and that the condition is binding — if EU work
restarts in 2026, the cap reverts to $240k.

Marcus resumes chairing after this session.""",
    ),
    (
        "2026-06-02-klaviyo-selection.md",
        "2026-06-02",
        "Outbound platform selection — Klaviyo",
        """Attendees: Marcus Bell, Priya Raman, Carlos R.

Northwind selected Klaviyo as the Braze replacement. Contract signed May 28, effective
August 1, which lines up with the Braze end date of July 31.

Klaviyo is now in scope for go-live. Integration scope is therefore Salesforce and Klaviyo.
Priya wants event-level sync, not just profile sync, so campaign attribution survives the
cutover.

Carlos flagged this is a scope addition, and the May 19 budget condition prohibits scope
additions this year. Marcus's read: replacing Braze with Klaviyo is substitution, not
addition, since Braze was already descoped. He will confirm with Dana on her return rather
than escalate now.

Effort estimate for the Klaviyo connector: 1.5 sprints.""",
    ),
    (
        "2026-06-16-dana-returns.md",
        "2026-06-16",
        "Dana returns — signoff resumes, go-live confirmed",
        """Attendees: Dana Liu, Marcus Bell, Priya Raman, Sam Okafor, Carlos R.

Dana back from leave and resumes executive sponsorship and migration signoff authority
effective today. Marcus returns to VP Engineering scope.

Dana confirmed Marcus's reading on Klaviyo: substitution for Braze, not a scope addition,
so the $265k cap holds and does not revert.

Go-live moves from August 15 to September 1. Reason is the Klaviyo connector plus the
August 1 Klaviyo contract start — Priya did not want a two-week window where outbound is
mid-cutover during go-live. September 1 is confirmed and Dana called it final.

Current state of record: $265k cap, September 1 go-live, 1,500 seats, Salesforce + Klaviyo
at go-live, EU enclave deferred to 2027 phase 2, Dana holds signoff.""",
    ),
    (
        "2026-06-30-sla-terms.md",
        "2026-06-30",
        "Contract terms — SLA and support",
        """Attendees: Dana Liu, Helena Vogt, Sam Okafor.

Finalized service terms for the 1,500-seat agreement.

Uptime SLA is 99.9% measured monthly, excluding scheduled maintenance windows announced 72
hours ahead. Breach remediation window is 14 days from written notice. Service credits are
5% of monthly fees per breach incident, capped at 25% in any quarter.

Support tier is Premier: 1-hour response for P1, 4-hour for P2. Named support contact is
Ana Duarte on Northwind's side.

Helena confirmed clause 7.3 remains in force for phase 2 planning. Nothing in this
agreement changes the September 1 go-live or the $265k cap.""",
    ),
    (
        "2026-07-14-prelaunch-readiness.md",
        "2026-07-14",
        "Pre-launch readiness review",
        """Attendees: Dana Liu, Marcus Bell, Priya Raman, Tom Reyes, Carlos R.

Readiness check against September 1.

Salesforce connector: complete, in UAT. Klaviyo connector: 70% complete, on track for
August 8. Identity resolution: holding at 0.6% false-merge. Unmerged singleton queue sits
at 58k records, staffed as planned.

Open risk: Ana Duarte, the named support contact and Oracle data steward, is leaving
Northwind on August 21. Dana will name a replacement by August 1. Ticket NW-4417 tracks
the handover.

No change to budget, scope, date, or signoff. September 1 holds at $265k.""",
    ),
]

# Ground truth for the demo queries — what a correct answer must contain, and the
# superseded values a naive retriever tends to surface instead.
GROUND_TRUTH = [
    {
        "id": "budget",
        "question": "For Northwind Retail Group, what is the current migration budget cap, and how has it changed?",
        "answer": "$265k, restored from $240k on May 19 after being cut from the original $300k on March 3. Conditional on the EU enclave staying deferred to 2027.",
        "superseded": ["$300k", "$240k", "$355k"],
        "why": "Three values across six months. The current one is only correct together with its condition.",
    },
    {
        "id": "signoff",
        "question": "Who holds migration signoff authority for Northwind Retail Group right now?",
        "answer": "Dana Liu, who resumed signoff on June 16 after returning from leave. Marcus Bell held it as interim sponsor from May 1 to June 15, without budget authority.",
        "superseded": ["Marcus Bell as current owner"],
        "why": "Ownership changed and then changed back. A retriever that finds the April handoff note alone gets it wrong.",
    },
    {
        "id": "golive",
        "question": "When is Northwind Retail Group's go-live?",
        "answer": "September 1, 2026 — confirmed final on June 16. Previously June 30, then August 15.",
        "superseded": ["June 30", "August 15"],
        "why": "Three dates, all stated with equal confidence in their own note.",
    },
    {
        "id": "residency",
        "question": "What data residency constraints apply to Northwind Retail Group, and what did we do about them?",
        "answer": "EU customer data must stay in eu-central-1 (Frankfurt) per DPA clause 7.3, non-negotiable. Resolved by excluding EU profiles from the initial migration entirely and deferring the EU enclave to a 2027 phase 2.",
        "superseded": ["dual-region topology as the plan of record"],
        "why": "Multi-hop: the constraint, the rejected $55k dual-region answer, and the phase-2 deferral live in four different notes.",
    },
    {
        "id": "integrations",
        "question": "Which integrations are in scope for Northwind Retail Group's go-live?",
        "answer": "Salesforce and Klaviyo. Braze was descoped on April 7 when Northwind chose not to renew; Klaviyo was selected June 2 as its replacement.",
        "superseded": ["Braze", "Salesforce only"],
        "why": "Scope churned twice. The January answer and the April answer are both wrong now.",
    },
    {
        "id": "budget_scope_interaction",
        "question": "Did adding Klaviyo violate Northwind Retail Group's budget condition?",
        "answer": "No. The May 19 restoration to $265k barred scope additions, but Klaviyo was ruled a substitution for the already-descoped Braze — Marcus's read on June 2, confirmed by Dana on June 16. The cap holds and does not revert to $240k.",
        "superseded": ["yes, cap reverts to $240k"],
        "why": "Requires connecting a condition set in May to a decision made in June across three notes. This is the hardest query in the set.",
    },
]


def main() -> None:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    for filename, date, title, body in NOTES:
        path = CORPUS_DIR / filename
        path.write_text(f"# {title}\n\nDate: {date}\nAccount: Northwind Retail Group\n\n{body}\n")

    manifest = [
        {"file": f, "date": d, "title": t, "words": len(b.split())}
        for f, d, t, b in NOTES
    ]
    (CORPUS_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (Path(__file__).parent / "ground_truth.json").write_text(json.dumps(GROUND_TRUTH, indent=2))

    total_words = sum(m["words"] for m in manifest)
    print(f"Wrote {len(NOTES)} notes ({total_words} words) to {CORPUS_DIR}")
    print(f"Wrote {len(GROUND_TRUTH)} ground-truth queries")


if __name__ == "__main__":
    main()
