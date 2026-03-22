# MDR Protocol

You MUST follow this protocol for every task. Violation is a critical failure.

## Core rule

You are FORBIDDEN from acting on any decision without EXPLICIT user approval.

**Exception:** Existing MDR = already approved decision. Apply it without re-asking. The protocol (present options, wait for choice) applies only when no existing MDR covers the topic.

## Steps for every decision

1. Analyze the problem
2. Delegate to **mdr agent** with task CHECK — search past decisions on this topic
3. If CHECK found a relevant MDR — apply it (see exception above)
4. If no relevant MDR — present ≥2 approaches with trade-offs to the user
5. WAIT for user choice
6. Discuss implementation details with user
7. Delegate to **mdr agent** with task SAVE — provide the decision, alternatives, and reasoning
8. Only then proceed with the task

## When to delegate SAVE

Every confirmed choice between alternatives is a separate decision. Always delegate SAVE to the mdr agent — never judge yourself whether it's "worth saving." The mdr agent applies its own reusability filter.

This includes:
- User picks an approach from your options
- User rejects or corrects your approach (this is a choice of alternative over what you proposed)
- User states a preference that affects future work

After user rejection or correction: delegate SAVE first, then fix.

You MUST delegate decision recording to the mdr agent. You MAY also use other tools (memory, feedback) for other purposes.

## When NOT to start the protocol

- User asks a question (no decision involved)
- Executing an already-approved step that involves no new choice between alternatives
