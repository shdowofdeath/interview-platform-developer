# INC-2026-05-20 — Alert storm, Acme SOC

**Severity**: SEV-2
**Duration**: 2026-05-20 04:10 → 2026-05-20 16:55
**Author**: Dana Feldstein

## Impact

Acme's SOC received 4,180 critical-severity alerts from Nightjar in twelve hours, against a normal daily volume of about 60. Their on-call muted the Nightjar integration at 08:20 and it stayed muted for six days.

## What happened

Our honeypot collector began scoring aggressively after a tuning change on their side. Because `confidence.aggregate` took the **maximum** of the per-source scores at the time, any indicator the honeypot touched inherited the honeypot's score, and almost everything crossed the alert threshold of 70.

Nothing in Nightjar changed. A single source changed its behaviour and our aggregation had no resistance to it.

## Resolution

Short term: excluded the honeypot source from aggregation by hand.

Medium term (NJ-2841): changed `aggregate` to the arithmetic mean of all sources. A single loud source can now move the aggregate but cannot dominate it. Alert volume returned to baseline within a day of the change and Acme re-enabled the integration.

## What we would do differently

The right answer is almost certainly per-source weighting, with the honeypot weighted low, rather than an unweighted mean. We did not have the appetite for a scoring-model design while Acme's integration was muted, and the mean was a two-line change that solved the immediate problem.

This is a known compromise. It is documented in `CLAUDE.md`. If it ever produces a complaint in the other direction — an indicator that should be critical reading as low — that is the trade-off arriving, and the fix is weighting, not reverting to max.

## Action items

- [x] Ship the mean (NJ-2841)
- [x] Document in `CLAUDE.md`
- [ ] Design per-source weighting — NJ-2903, backlog, no owner
- [ ] Alert on a source's score distribution shifting — not started
