# Data mapping review

Date: 2026-01-28
Account: Northwind Retail Group

Attendees: Priya Raman, Marcus Bell (VP Engineering, Northwind), Carlos R.

Walked the data mapping draft. Three legacy sources: an on-prem Oracle instance (customer
master, ~9.4M profiles), a Postgres loyalty database (~3.1M members), and a Segment
warehouse export.

Marcus raised that the loyalty database has no reliable primary key across 2019-2021
records — roughly 400k rows will need fuzzy identity resolution. He estimated two
engineering sprints. This is the first real schedule risk anyone has named.

Priya confirmed the data steward assignments: Ana Duarte for Oracle, Tom Reyes for loyalty,
Priya herself for Segment.

No change to budget or timeline discussed. Go-live remains June 30.
