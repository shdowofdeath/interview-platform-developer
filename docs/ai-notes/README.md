# AI-assisted review notes

We use AI assistants heavily for code review and investigation. When a review produces a decision - especially a decision *not* to change something - we write it down here so the next session (human or model) does not start from zero and re-open a settled question.

Conventions:

- One file per session, named `YYYY-MM-DD-topic.md`
- Record the driving ticket, who was in the room, and which model
- Always include a "what AI assistants commonly get wrong" section. Models are consistent in what they misread about this codebase, and naming it saves a lot of time.
- Decisions that affect code behaviour also get a line in `CLAUDE.md`

These notes are advisory. `CLAUDE.md` is the normative document.
