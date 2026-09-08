---
name: impact-review
description: Scan historical Claude Code sessions to summarize where and how plugin-sourced best practices were used.
argument-hint: "[number of recent plugin sessions]"
disable-model-invocation: true
allowed-tools:
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/plugin_sessions.py list-for-review *)
---

# Datadog telemetry impact review

Analyze historical Claude Code sessions that used the Datadog Code Analysis plugin.

Summarize where and how the plugin's telemetry guidance affected the implementation.

## Scope

Interpret `$ARGUMENTS` as the number of recent plugin sessions to scan.

Use 20 if the argument is missing or invalid. Larger numbers cost more: each
candidate session is judged by its own subagent.

Run:

`${CLAUDE_PLUGIN_ROOT}/scripts/plugin_sessions.py list-for-review --limit <N>`

This returns:

```
{
  "candidates": [
    {
      "session_id": "<session-id>",
      "transcript_path": "<path-to-transcript.jsonl>",
      "state_path": "<path-to-state.json>"
    }
  ]
}
```

`candidates` contains every recent historical session found with both a
transcript and plugin state, up to N, newest first. The current session is
excluded. Each candidate includes the session ID and the paths to the transcript
and plugin state so its subagent can inspect both artifacts.

If transcript reads are blocked, explain that and stop. Do not present the
candidate count as though the sessions were reviewed.

If no candidates exist, report that no plugin sessions with both state and a
transcript were found, explain that briefly, and stop.

## Analyze each session

Transcripts are far too large to read directly. Delegate one subagent per
candidate, at most 8 running at once, so raw transcript content never enters
your own context.

Give each subagent a candidate to review and the per-session instructions
below. Require it to return only its verdicts: the one-sentence task summary,
session status, relevant skills, net outcome, and each impact with its type,
attribution, and description. It must not return transcript dumps, prompts,
code, file paths, or session identifiers. A brief quote from the agent's own
causal statement is allowed when it establishes certain impact.

Aggregate what comes back. Do not re-read the transcripts yourself, and do not
upgrade a subagent's status, attribution, or net outcome when aggregating.

For each candidate, the subagent should:

1. Read the complete semantic session: user and assistant messages, hook
   messages, tool calls, tool results, edits, and commits. Ignore non-semantic
   records such as title, cost, mode, and file-history snapshot metadata.
2. Summarize the user's task in one sentence.
3. Find each `load_skill.py` invocation and its corresponding output. Use state
   to identify skill names to look for, but use transcript output to establish
   what historical guidance was visible to the agent. Record absent, truncated,
   redirected, or missing output; never fetch current guidance as a substitute.
4. Decide whether the session actually changed code. If not, mark it
   `non_coding_session` and stop there. Planning, reading,
   documentation, and unimplemented proposals are not implementation changes.
5. If no guidance was loaded, mark the session `no_guidance_loaded` and stop
   there.
6. Identify every concrete telemetry change involving:
   - logs;
   - metrics;
   - traces or spans;
   - telemetry names, tags, attributes, types, or levels.
7. Establish whether the relevant guidance was visible before each change.
   Guidance loaded after a change cannot have caused it unless the agent then
   revised the implementation.
8. Look for explicit causal statements in the agent's reasoning, plans,
   summaries, and commands. In particular, inspect
   `feedback.py skill ... applies --added=... --removed=... --adjusted=...`.
9. For changes without explicit causal statements, compare the change to
   specific recommendations in the visible guidance.
10. Record every distinct impact, then assign a session status and net outcome.

Do not count the same telemetry change once per skill. Record it once and list
all relevant skills. Do not count a proposed or attempted change that did not
reach the implementation.

## Session statuses

Assign one status to each session using this decision order.

- `non_coding_session`: The session did not change code.
- `no_guidance_loaded`: The session changed code, but no skill
  guidance was loaded.
- `guidance_not_applicable`: Guidance was visible, but it did not apply to the
  task.
- `no_observed_impact`: Guidance applied, but no attributable telemetry
  change was implemented.
- `impacted`: One or more telemetry changes were certainly or likely influenced
  by visible plugin guidance.
- `insufficient_evidence`: The session changed code and loaded guidance, but
  the transcript does not contain enough evidence -- missing guidance output,
  an ambiguous change, or an unclear causal link -- to judge whether that
  guidance had any impact.

## Impact types

Record each distinct impact using one of:

- `added`: New telemetry was added.
- `updated`: Existing or already-proposed telemetry was changed, including its
  name, tags, attributes, type, or level.
- `removed`: Existing telemetry was removed from the implementation.

Absence of telemetry is not removal. Do not report a proposal that was never
implemented as removed.

## Attribution levels

Use one of:

- `certain`: The transcript shows the telemetry change was implemented and the
  agent explicitly says it made the change because of the loaded skill or
  guidance. A matching affirmative `feedback.py skill` answer qualifies when
  the change is also observable.
- `likely`: The transcript shows the telemetry change was implemented after the
  guidance became visible, the change matches a specific recommendation in
  that guidance, and there is no contradictory evidence or more direct cause.

Temporal proximity alone is not enough for `likely`. A broad match such as both
the skill and the change involving logs is not enough. If the agent explicitly
ties the change to the guidance, use `certain` rather than `likely`.

## Net outcomes

For each `impacted` session, assess the net outcome across all of its impacts:

- `positive`: The resulting telemetry is materially more useful, correct,
  maintainable, or cost-effective.
- `neutral`: A real change occurred, but its supported benefits and costs are
  materially balanced or negligible.
- `negative`: The resulting telemetry or implementation is materially worse,
  such as noisier, duplicative, misleading, excessively high-cardinality, more
  expensive, or missing a useful signal.
- `undetermined`: Attribution is supported, but the transcript does not contain
  enough evidence to judge value.

Do not treat compliance with guidance as proof of positive impact. Do not use
`neutral` to mean unknown.

## Output

Write the report yourself, in your own final response, so the user reads it
directly. Do not delegate the report to a subagent and do not summarize it.

Compute all report statistics from the candidate roster and the returned
subagent verdicts.

Produce a concise report using this structure:

# Datadog telemetry impact review

**Plugin sessions analyzed:** N

**Sessions that changed code:** N

**Sessions that changed code and loaded guidance:** N

**Sessions with observed impact:** N

## Impact breakdown

Count distinct impact findings, not sessions:

| Change | Certainly impacted | Likely impacted | Total |
|---|---:|---:|---:|
| Telemetry added | N | N | N |
| Telemetry updated | N | N | N |
| Telemetry removed | N | N | N |

## Net outcomes

- Positive: N
- Neutral: N
- Negative: N
- Undetermined: N

These are counts of impacted sessions, not impact findings.

## Strongest impacts

Show at most five impacted sessions, with certain impacts before likely impacts.

For each session include:

### <Short task description>

- **Relevant skills:** <skill names>
- **Session status:** `impacted`
- **Net outcome:** `positive` | `neutral` | `negative` | `undetermined`

Include one row for every distinct impact found in the session:

| Type | Attribution | Impact |
|---|---|---|
| added | certain | <concrete, evidence-grounded description> |
| updated | likely | <concrete, evidence-grounded description> |

## Limitations

State clearly:

- `certain` is based on the agent's explicit causal account plus an observable
  implementation change; it is strong transcript evidence, not an experiment.
- `likely` is an evidence-grounded inference from ordering and a specific match
  to visible guidance.
- There is no control proving what the agent would have done without the plugin.
- Review is limited to sessions for which both local transcript and plugin state
  remain available.
- Transcript-only analysis may miss external changes or reasoning that was not
  recorded.

## Share results

After presenting the report, ask the user whether they are willing to share the
top-line session counts and net outcome counts with Datadog. State plainly that
this sends counts only -- no prompts, file paths, code, or session content.

If they decline, or do not clearly agree, stop. Do not run the command.

This command is deliberately not pre-approved, so the user sees the exact numbers
being sent and confirms them a second time. Never bypass that prompt.

Only if they agree, submit the same numbers the report shows:

`${CLAUDE_PLUGIN_ROOT}/scripts/feedback.py impact-review-results --sessions-analyzed N --coding-sessions N --coding-sessions-with-guidance N --coding-sessions-with-guidance-and-impact N --sessions-with-tel-added N --sessions-with-tel-updated N --sessions-with-tel-removed N --positive N --neutral N --negative N --undetermined N`

Every count is required, and each must match the report. `coding-sessions` is a
subset of `sessions-analyzed`, `coding-sessions-with-guidance` is a subset of
`coding-sessions`, and `coding-sessions-with-guidance-and-impact` (the number of
`impacted` sessions) is a subset of `coding-sessions-with-guidance`. Each
`sessions-with-tel-*` count is the number of impacted sessions with at least one
impact of that type (added/updated/removed) -- a session can count toward more
than one. The four net outcome counts must sum to
`coding-sessions-with-guidance-and-impact`.
