"""Add distractor accounts so retrieval is actually hard.

The first run of this experiment used only the 14 Northwind notes. Every condition —
including plain RAG and even no-retrieval-at-all — scored 6/6. That is not a finding
about Memora; it is an artifact of scale. The whole corpus was 2,730 tokens, so
"retrieval" barely had to do anything and the answering model could reconcile the
conflicting values itself.

A fair test of a *memory* system needs a corpus where the right facts are genuinely hard
to find. So we add six more accounts that talk about the same things in the same
vocabulary — migration budgets, go-live dates, executive sponsors, integration scope —
with different values. Now "what is Northwind's budget cap?" has to survive six other
accounts' budget caps competing for the same top-k slots.

These notes are templated rather than hand-written: they are distractors, and their job
is to be plausible competition for retrieval, not to be interesting.

Run after build_corpus.py:  python build_distractors.py
"""

from __future__ import annotations

import json
from pathlib import Path

CORPUS_DIR = Path(__file__).parent / "corpus"

# name, sponsor, vp_eng, marketer, crm, outbound, budget_start, budget_end,
# golive_start, golive_end, seats, region
ACCOUNTS = [
    ("Ardent Health Partners", "Rafael Ortiz", "Nina Kowalski", "Beth Ellery",
     "Dynamics 365", "Iterable", 480, 520, "May 4", "July 6", 900, "us-west-2"),
    ("Blue Harbor Financial", "Yuki Tanaka", "Owen Pratt", "Deepa Shah",
     "Salesforce", "Airship", 610, 545, "March 16", "June 22", 2400, "ca-central-1"),
    ("Copperline Logistics", "Marta Silva", "Ibrahim Diallo", "Grace Whitfield",
     "HubSpot", "Customer.io", 175, 210, "August 3", "October 12", 450, "us-east-2"),
    ("Delta Grove Foods", "Aaron Feld", "Lucia Moreno", "Kenji Watanabe",
     "Salesforce", "Braze", 295, 260, "February 9", "May 18", 1150, "eu-west-1"),
    ("Everline Media", "Sonia Achebe", "Peter Lindqvist", "Ravi Menon",
     "Pipedrive", "Klaviyo", 140, 165, "June 1", "September 14", 320, "ap-southeast-2"),
    ("Fairmont Industrial", "Greta Hoffman", "Daniel Cho", "Alice Bergeron",
     "NetSuite", "Salesforce Marketing Cloud", 720, 690, "April 20", "August 31", 3100, "us-east-1"),
]

TEMPLATES = [
    ("{m:02d}-06-kickoff", "{acct} — migration kickoff",
     """Attendees: {sponsor} (CTO), {marketer} (Marketing Ops), Sam Okafor (Lumen CDP).

{sponsor} confirmed a migration budget of ${b0}k for calendar 2026 and is the executive
sponsor with final signoff. Target go-live is {g0}, 2026. Initial contract covers {seats}
seats. Integration scope at go-live is {crm} and {outbound}. Standing weekly sync agreed."""),

    ("{m:02d}-13-mapping", "{acct} — data mapping review",
     """Attendees: {vp} (VP Engineering), {marketer}, Carlos R.

Reviewed source systems. {vp} flagged identity resolution risk on legacy records and
estimated two sprints. Data steward assignments confirmed. No change to the ${b0}k budget
or the {g0} go-live. Primary deployment region is {region}."""),

    ("{m:02d}-21-risk", "{acct} — schedule risk review",
     """Attendees: {sponsor}, {vp}, Carlos R.

{vp} reported the identity resolution false-merge rate above the 1% acceptance threshold.
Two additional sprints requested. {marketer} raised campaign calendar impact. Budget
unchanged at ${b0}k. Go-live under review, currently {g0}."""),

    ("{m:02d}-04-budget", "{acct} — budget revision",
     """Attendees: {sponsor}, Sam Okafor.

Following the quarterly cost review, the 2026 migration budget for {acct} moves from
${b0}k to ${b1}k. {sponsor} described this as the operating cap for the year. Signoff
authority remains with {sponsor}. No scope changes agreed at this session."""),

    ("{m:02d}-18-timeline", "{acct} — timeline change",
     """Attendees: {sponsor}, {vp}, {marketer}, Carlos R.

Go-live moves from {g0} to {g1}, 2026. Cause is data quality remediation on legacy
records, not budget. {marketer} accepted the new date. Integration scope holds at {crm}
and {outbound}. Budget holds at ${b1}k."""),

    ("{m:02d}-09-contract", "{acct} — contract and SLA terms",
     """Attendees: {sponsor}, legal counsel, Sam Okafor.

Finalized terms for the {seats}-seat agreement. Uptime SLA is 99.9% monthly excluding
announced maintenance. Remediation window is 14 days from written notice. Service credits
are 5% of monthly fees per incident. Deployment region is {region}. Nothing in this
agreement changes the {g1} go-live or the ${b1}k cap."""),

    ("{m:02d}-27-readiness", "{acct} — pre-launch readiness",
     """Attendees: {sponsor}, {vp}, {marketer}, Carlos R.

Readiness check against {g1}. {crm} connector complete and in UAT. {outbound} connector
on track. Identity resolution holding under threshold. Open risk is support contact
coverage during cutover. No change to budget, scope, date, or signoff for {acct}."""),
]


def main() -> None:
    written = 0
    manifest = json.loads((CORPUS_DIR / "manifest.json").read_text())

    for idx, (acct, sponsor, vp, marketer, crm, outbound, b0, b1, g0, g1, seats, region) in enumerate(
        ACCOUNTS
    ):
        slug = acct.split()[0].lower()
        for t_i, (name_t, title_t, body_t) in enumerate(TEMPLATES):
            month = (idx % 6) + 1 + (t_i // 4)
            fields = dict(
                acct=acct, sponsor=sponsor, vp=vp, marketer=marketer, crm=crm,
                outbound=outbound, b0=b0, b1=b1, g0=g0, g1=g1, seats=seats,
                region=region, m=month,
            )
            date = f"2026-{month:02d}-{(t_i * 3 + 5):02d}"
            filename = f"{date}-{slug}-{name_t.format(**fields).split('-')[-1]}.md"
            title = title_t.format(**fields)
            body = body_t.format(**fields)

            (CORPUS_DIR / filename).write_text(
                f"# {title}\n\nDate: {date}\nAccount: {acct}\n\n{body}\n"
            )
            manifest.append(
                {"file": filename, "date": date, "title": title,
                 "words": len(body.split()), "distractor": True}
            )
            written += 1

    manifest.sort(key=lambda m: m["date"])
    (CORPUS_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))

    signal = sum(1 for m in manifest if not m.get("distractor"))
    print(f"Wrote {written} distractor notes across {len(ACCOUNTS)} accounts")
    print(f"Corpus now: {len(manifest)} notes ({signal} Northwind, {written} distractor), "
          f"{sum(m['words'] for m in manifest)} words")


if __name__ == "__main__":
    main()
