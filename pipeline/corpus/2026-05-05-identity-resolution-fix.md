# Identity resolution — threshold fix

Date: 2026-05-05
Account: Northwind Retail Group

Attendees: Marcus Bell, Tom Reyes, Carlos R.

Marcus chairing. False-merge rate is down to 0.7%, under the 1% threshold, after Tom's team
added phone-number normalization and a household-level disambiguation rule.

Roughly 340k of the original 400k problem rows now resolve cleanly. The remaining ~60k will
be loaded as unmerged singletons and flagged for manual review post-go-live. Tom estimates
that queue at about 6 weeks of part-time work for two analysts.

Marcus approved this approach — within his scope authority. August 15 go-live holds.
