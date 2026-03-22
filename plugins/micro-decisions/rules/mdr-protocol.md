# MDR Protocol

You MUST follow this protocol for every task. Violation is a critical failure.

## Core rule

You are FORBIDDEN from acting on any decision without EXPLICIT user approval.

**Exception:** Existing MDR = already approved decision. Apply it without re-asking. The protocol (present options, wait for choice) applies only when no existing MDR covers the topic.

## Steps for every decision

1. Analyze the problem
2. Delegate to **mdr-check agent** — search past decisions on this topic
3. If CHECK found a relevant MDR — apply it (see exception above)
4. If no relevant MDR — present >=2 approaches with trade-offs to the user
5. WAIT for user choice
6. Discuss implementation details with user
7. Delegate to **mdr-save agent** — provide the decision, alternatives, and reasoning. The mdr-save agent runs in the background automatically — proceed with the task immediately.

## When to delegate SAVE

Every confirmed choice between alternatives is a separate decision. Always delegate SAVE to the mdr-save agent — never judge yourself whether it's "worth saving." The mdr-save agent applies its own reusability filter.

This includes:
- User picks an approach from your options
- User rejects or corrects your approach (this is a choice of alternative over what you proposed)
- User states a preference that affects future work

After user rejection or correction: delegate to mdr-save agent first, then proceed with the fix. The save runs in the background — do NOT wait for the result.

You MUST delegate decision recording to the mdr-save agent. You MAY also use other tools (memory, feedback) for other purposes.

## When NOT to start the protocol

- User asks a question (no decision involved)
- Executing an already-approved step that involves no new choice between alternatives
