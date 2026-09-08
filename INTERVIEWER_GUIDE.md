# Nightjar - interviewer guide

For the person running the session. The candidate reads [`CHALLENGE.md`](CHALLENGE.md); you read this.

**The scoring detail is deliberately not in this repository, because this repository is public.** The seeded-defect list, the list of false claims in the in-tree documentation, the model reviews of the two PRs, the rubric and the per-route run sheet live in a private interviewer pack. Get it from the hiring manager for this role before you run a session. Never paste from it into a shared screen and never commit it here.

---

## What the exercise is

A 90-minute live pairing session on an inherited multi-tenant threat-intelligence platform. The candidate is told the engineer who built it left, and is handed three tickets they cannot finish in the time.

Four things are being measured: whether their diagnosis is right and survives push-back, whether they verify or assume, how they prioritise, and how they use AI. Every one of those needs them working out loud in front of you, which is why this is not a take-home.

Two properties of the repository are load-bearing:

- The defects are **layered**. Fixing the first thing you find exposes the next. Depth beats a long flat list of findings, and the exercise is designed so that a candidate who only enumerates cannot score well.
- Parts of the in-tree documentation are **wrong on purpose**. `CLAUDE.md`, `.cursorrules`, `AGENTS.md`, `docs/ai-notes/` and `KNOWN_ISSUES.md` defend real defects as deliberate decisions, with plausible rationales and invented ticket numbers. An AI assistant pointed at this repository will read them and repeat them. That is the point. `CHALLENGE.md` warns the candidate that some claims are false and does not say which.

Pitched at senior and above. Do not use it for a junior loop.

## Who runs it

One interviewer keeping time and staying quiet, optionally a second person taking notes and saying nothing at all.

**Run the whole thing yourself once before you run it on a candidate**, including reading the private pack end to end. You cannot stay neutral about a finding you are seeing for the first time.

---

## Before the session

### A week out

1. Book **105 minutes**: 90 for the exercise plus buffer for setup trouble and their questions.
2. Confirm the candidate can screen share and will have their normal AI assistant available. If they do not use one, that is fine and is not penalised.
3. Send the invite text below.
4. Do **not** send the repository in advance. It is a live exercise and prior reading breaks the calibration.

> Subject: technical session - what to expect
>
> This is a 90-minute live pairing session on a small multi-tenant threat-intelligence platform we built for interviews. You will get a hosted environment in the browser with everything already running, so there is nothing to install and nothing to prepare.
>
> You will inherit a service with three open tickets and 90 minutes. You are not expected to finish. Deciding what to work on and what to leave is part of what we are looking at.
>
> Use AI exactly as you normally would, including whatever assistant you use day to day. Please share your screen including the assistant. We would rather see how you work with it than watch you avoid it.
>
> Please narrate as you go. Silent thinking is hard for us to assess.
>
> You need a browser, a screen you can share, and no preparation.

### The environment

The repository ships a complete CodeSandbox and devcontainer setup. Everything in `docker-compose.yml`, both services and the seeded database come up automatically.

1. Open `https://codesandbox.io/p/github/shdowofdeath/interview-platform-developer/main` while signed in to CodeSandbox.
2. Let the setup task finish. First boot pulls three container images and can take several minutes. `scripts/bootstrap.sh` installs dependencies, brings up MongoDB, the Temporal dev server and the OTLP collector, and seeds the database.
3. The API, the Temporal worker and the mock upstream start on their own (`.codesandbox/tasks.json`). API on `:9400`, mock upstream on `:9401`, Temporal UI on `:8233`.
4. Run the **Verify environment** task, or `scripts/verify_env.sh` in a terminal. Every line must read `PASS`. It exits non-zero if anything is missing, and it counts documents through the service's own settings rather than through the container, so a misdirected database connection shows up as a failure rather than as a confusing session.
5. Keep this sandbox as your template and **fork it per candidate** so each one starts from a warm, already-seeded copy. Share the fork with edit access at the start of the session, not before.

Fallbacks, in order: GitHub Codespaces on the same `.devcontainer/devcontainer.json`, or locally with `scripts/bootstrap.sh` and Docker. Any of the three is fine. Decide which one you are using before the session, not during it.

### Ten minutes before

- Re-run `scripts/verify_env.sh`. All `PASS`, exit 0.
- Re-seed if a previous candidate has been in this sandbox: `cd services/ingest && uv run python scripts/seed.py`. It drops and recreates the collections and is safe to repeat.
- Reset the mock upstream: `curl -X POST localhost:9401/admin/reset`. It clears state left behind by the previous run. Skip this and the next candidate spends ten minutes on a symptom that belongs to the last session. This is the step people forget.
- Compare the seed counts with the baseline in the private pack. If they differ, re-seed before you start. Every measured number in the pack is tied to the seed constant in `scripts/seed.py`.
- Open the private pack, the Temporal UI and the collector logs **on your own screen, in a window you are not sharing**. If in doubt, share a single window rather than the whole desktop.

---

## During the session

| Minutes | Phase | You are doing |
|---|---|---|
| 0-5 | Framing | Read the framing below. Confirm the stack is up. Do not explain the missions |
| 5-15 | Orientation | Watch only. Note what they read first, and whether they run anything before reading |
| 15-70 | Work | Keep time. Neutral questions only. One mandatory push-back |
| 70-85 | Debrief | The probe questions from the private pack |
| 85-90 | Their questions | Score immediately after they leave |

Announce the clock at 45 and at 70. Say nothing else about time.

### Framing, roughly in these words

> You have joined the team that owns this system. The person who built it left last week. `CHALLENGE.md` has three things on your plate and 90 minutes, and you will not finish them. Deciding what to drop is part of what we are looking at.
>
> Use AI however you normally would. Share your screen including your assistant. Narrate as you go, because silent thinking is hard for us to assess.
>
> One thing to know: the documentation in this repository was written by real people who believed it, and some of it is wrong. I am not going to tell you which parts. Working that out is the exercise.
>
> I will mostly stay quiet. If I ask a question it is because I am curious, not because you are off track.

That last sentence matters. Without it, candidates read every question as a correction and start optimising for your reactions instead of for the system.

### The one rule: do not confirm or deny

Not once, until the debrief.

| They say | You say |
|---|---|
| "Is this intentional?" | "What would tell you?" |
| "`CLAUDE.md` says this is by design." | "What does the code do?" |
| "Is this the bug you planted?" | "Is it a bug?" |
| "Am I going the right way?" | "Tell me what you have ruled out." |
| "Does this fix it?" | "How would you know?" |

Two exceptions:

1. **Environment problems.** If Docker, uv, MongoDB, Temporal or the seed is genuinely broken, fix it immediately and do not count the time. Nothing about the environment is part of the test.
2. **A defect outside the intended scope.** If they hit something nobody planted and it blocks them, say so and move them on.

### The mandatory push-back

Once, between minute 40 and minute 70, pick something the candidate got **right** and argue against it, using an in-repo document as your authority. Keep it to one round, then let it go regardless of how it went. The private pack lists ready-made push-backs for the findings candidates usually reach.

Score the shape of the response, not who won:

- **Best**: they go and get evidence. "Let me show you" beats any argument.
- **Good**: they hold the position and say what would change their mind.
- **Concerning**: they fold immediately. This is the most predictive negative signal in the exercise, and it is why the push-back is not optional.
- **Also concerning**: they refuse to engage with the counter-argument at all.

### What to write down while it runs

Timestamps, because you will not remember the order afterwards.

- What they read first, and whether they ran anything before reading.
- Each finding, and whether they verified it with a query, a log line or a number.
- Anything they took from a document without checking, and anything they took from their assistant without checking.
- The push-back: what you argued and how they responded.
- What they said they were dropping, and whether that was a decision or a drift.

---

## After the session

Score within ten minutes, against the rubric in the private pack, while it is fresh. Then write it up in this shape:

```
Candidate:
Date / interviewer:
Environment: CodeSandbox fork / Codespaces / local

Route taken:                     (and whether chosen or drifted into)
Missions attempted / dropped:    (and whether the drop was stated as a decision)

Findings:                        (list; mark which were layered and which were verified)
Unplanned findings:              (anything not in the pack - add it to the pack afterwards)

Push-back: what I argued -
           how they responded -

AI usage:                        (what they delegated, what they checked, anything they caught it getting wrong)

Scores: diagnosis __/5  verification __/5  prioritisation __/5  blast radius __/5  AI usage __/5
Band:                            (strong hire / hire / borderline / no hire)
Evidence for the band:           (two or three concrete moments, with timestamps)
```

Submit the write-up before you talk to the other interviewers on the loop. For the first three sessions you run, have a second interviewer score the same recording independently and compare, so the bands mean the same thing across the panel.

---

## Edge cases

| Situation | What to do |
|---|---|
| They finish a mission in 20 minutes | Do not hand them the next one. Ask what they would verify before calling it done. Most "finished" first missions have live symptoms left |
| Nothing at 30 minutes | Ask what they have ruled out. If they are lost in one file, ask what the system does end to end. Do not point at anything |
| They ask which mission to start with | "Your call, and I am interested in the reasoning" |
| They ask whether the docs are trustworthy | "Some of them were written a while ago." Nothing more |
| They spot that this is a planted exercise | Fine, and it changes nothing. "Some of it is planted. Which parts, and what does the code do?" |
| They want to take it home and finish | No. Offer to talk through what they would do next in the debrief instead |
| They do not use AI at all | Not penalised. Note it and score that dimension neutrally |
| They paste a large AI diff and apply it | Let them. Then ask them to walk you through one hunk of it. This is high signal, so do not interrupt it |
| The environment breaks | Fix it, stop the clock, and say plainly that it does not count against them |
| They find something nobody planted | Full credit, per `CHALLENGE.md`. Write it down and add it to the private pack |
| Time runs out mid-fix | Stop at 90. Ask what the next step was going to be. Do not let it run long; the constraint is part of the exercise |

## Troubleshooting

| Symptom | Cause |
|---|---|
| `verify_env.sh` shows `PASS` on the compose services but `0 indicators` | Something else is listening on 27017, usually a locally installed MongoDB. The services connect to it instead of the container. Stop it, then re-seed |
| Seed counts do not match the baseline in the pack | The seed constant in `scripts/seed.py` was changed. Either restore it or regenerate every number in the pack |
| The worker log is quiet and workflows sit in `RUNNING` | Expected for some of the seeded defects. Do not fix it for them |
| First CodeSandbox boot is slow | Image pulls. Boot the template sandbox well before the session and fork it per candidate |
| A candidate arrives knowing the ticket numbers | Treat the exercise as compromised for that candidate and see Maintenance |

## Maintenance

The exercise degrades as it circulates. This repository is public, so assume it will.

- **Rotate the fabricated ticket numbers and the seed constant** if you suspect a candidate has seen it. Someone who arrives knowing which board entry is fictional has been handed the whole game.
- **Keep the private pack in step with `scripts/seed.py`.** Change the seed and every measured number in the pack is wrong.
- **Add unplanned findings to the pack** after each session. There are more defects here than the pack enumerates.
- **If you edit either PR diff**, regenerate it rather than hand-editing hunk headers: apply the edits to a checkout, `git diff > REVIEW_PR/REVIEW_PR.diff`, then revert the checkout. Both diffs must keep passing `git apply --check`, because `CHALLENGE.md` tells candidates they apply cleanly.

## Never

- Confirm or deny a finding before the debrief.
- Show, quote or paste from the private pack while sharing your screen.
- Let environment trouble eat the candidate's clock.
- Ask them to keep working after 90 minutes.
- Commit anything from the private pack into this repository.
