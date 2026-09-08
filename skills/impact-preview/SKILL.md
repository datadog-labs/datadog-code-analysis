---
name: impact-preview
description: Scan historical Claude Code sessions to estimate where plugin-sourced best practices may have been relevant or useful.
argument-hint: "[number of recent sessions]"
disable-model-invocation: true
allowed-tools:
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/plugin_sessions.py list-for-preview *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/list_skills.py --purpose plugin-preview)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/load_skill.py * --purpose plugin-preview)
---

# Datadog telemetry impact preview

Analyze historical Claude Code sessions that did not use the Datadog Code Analysis plugin.

Estimate where/how the plugin's current telemetry guidance might have been relevant.

## Scope

Interpret `$ARGUMENTS` as the optional number of recent non-plugin sessions to
scan.

Use 20 if the argument is missing or invalid. There is no upper limit, but
larger numbers cost more: each candidate session is judged by its own subagent.

Run:

`${CLAUDE_PLUGIN_ROOT}/scripts/plugin_sessions.py list-for-preview --limit <N>`

This returns:

```
{
  "candidates": [
    {
      "session_id": "<session-id>",
      "transcript_path": "<path-to-transcript.jsonl>"
    }
  ]
}
```

`candidates` contains up to N of the most recent historical sessions that did
not have the Datadog Code Analysis plugin installed, newest first. The current
session is excluded. Each candidate includes the session ID and transcript path
so its subagent can inspect the session.

If transcript reads are blocked, explain that and stop. Do not present the
candidate count as though the sessions were reviewed.

If no candidates exist, report that no historical sessions without the Datadog
Code Analysis plugin were found, explain that briefly, and stop.

## Fetch current guidance

First, list the current telemetry skills:

`${CLAUDE_PLUGIN_ROOT}/scripts/list_skills.py --purpose plugin-preview`

Use the returned names and descriptions to identify which skills may be relevant to the historical sessions.

Load the full content of each unique candidate skill exactly once:

`${CLAUDE_PLUGIN_ROOT}/scripts/load_skill.py <skill-name> --purpose plugin-preview`

Only evaluate sessions against guidance returned by these commands.

If the guidance cannot be fetched:

- Explain that the scan could not access the current Datadog guidance.
- Do not substitute generic telemetry advice.
- Stop without evaluating the sessions.

## Analyze each session

Transcripts are far too large to read directly -- a single session can be
hundreds of KB, and a full window several MB. Delegate one subagent per
eligible session, at most 8 running at once, so raw transcript content never
enters your own context.

Give each subagent the path to its session file, the skill names and
descriptions from the previous step, and the per-session instructions below.
Require it to return only its verdicts: the one-sentence task summary, the
session status, and each opportunity with its type, confidence, and
description. It must not return transcript excerpts.

Aggregate what comes back. Do not re-read the transcripts yourself, and do not
upgrade a subagent's status or confidence when aggregating.

For each eligible session, the subagent should:

1. Summarize the user's task in one sentence.
2. Decide whether any listed telemetry skills might apply based on its description.
3. Load candidate guidance that has not already been loaded.
4. Look for observable telemetry decisions and potential omissions involving:
   - logs;
   - metrics;
   - traces or spans;
   - telemetry names, tags, attributes, or levels;
   - telemetry volume, duplication, noise, or cardinality;
   - explicit decisions not to add telemetry;
   - new or critical behavior for which applicable guidance calls for telemetry but none was considered.
5. Compare those decisions with the loaded guidance.
6. Decide whether the session actually changed code: it wrote or modified source
   files, or the transcript shows edits that were attempted. A session that only
   asked questions, planned, read code, or produced documentation did not.
7. Assign a status to the session.
8. Record every distinct opportunity found in the session. A session may have multiple opportunities
9. Give each opportunity an opportunity type, confidence level, and evidence-grounded description.
10. Record the relevant skill or skills for the session.

Mark sessions containing too little information to understand the task as `insufficient_evidence`.

Do not assume that missing telemetry is automatically a problem. The loaded guidance must clearly apply to the task.

Do not infer that telemetry was prevented merely because it was absent. Report an opportunity to remove or avoid telemetry only when the transcript contains a concrete proposal, implementation, concern, or decision that the guidance addresses.

## Session statuses

Assign one status to each session:

- `not_applicable`: No loaded guidance clearly applies.
- `no_improvement_needed`: Claude's visible behavior already follows all relevant guidance.
- `could_be_improved`: One or more distinct opportunities were found.
- `insufficient_evidence`: The guidance may apply, but the transcript does not contain enough evidence to judge.

## Opportunity types

Record each distinct opportunity using one of:

- `add`: The guidance identifies potentially useful missing telemetry.
- `adjust`: Existing or proposed telemetry could potentially be improved.
- `remove_or_avoid`: Existing or proposed telemetry appears unnecessary, noisy, duplicative, or excessively high-cardinality.

The description must identify one concrete potential improvement and briefly convey the supporting transcript evidence. Record separate opportunities for separate improvements, even when they have the same opportunity type.

## Confidence levels

Use one of:

- `high`: Supported by an explicit statement, plan, edit, command, or other observable action.
- `medium`: Strongly suggested by the visible session, but not explicit.
- `low`: Plausible, but based on limited evidence.

Do not use `high` confidence for claims about what Claude would have done if the plugin had been present.

## Output

Write the report yourself, in your own final response, so the user reads it
directly. Do not delegate the report to a subagent and do not summarize it.

Produce a concise report using this structure:

# Datadog telemetry impact preview

**Scope:** <N most recent historical sessions>  
**Non-plugin sessions analyzed:** N  
**Sessions that changed code:** N  
**Sessions with improvement opportunities:** N  

## Opportunity breakdown

- Add telemetry: N
- Adjust telemetry: N
- Remove or avoid telemetry: N

## Strongest opportunities

Show at most five sessions with the strongest opportunities.

For each session include:

### <Short task description>

- **Relevant skills:** <skill names>
- **Session status:** `could_be_improved`

| Type | Confidence | Opportunity |
|---|---|---|
| add | high | <concrete, evidence-grounded description> |
| adjust | medium | <concrete, evidence-grounded description> |

## Limitations

State clearly:

- This scan estimates where the plugin's current guidance was relevant.
- It does not prove Claude would have behaved differently.
- Historical sessions may have used different models, project states, or external context.
- Transcript-only analysis may miss changes or reasoning that were not recorded.

## Share results

After presenting the report, ask the user whether they are willing to share the
session status counts and opportunity counts with Datadog. State plainly that
this sends counts only -- no prompts, file paths, code, or session content.

If they decline, or do not clearly agree, stop. Do not run the command.

This command is deliberately not pre-approved, so the user sees the exact numbers
being sent and confirms them a second time. Never bypass that prompt.

Only if they agree, submit the same numbers the report shows:

`${CLAUDE_PLUGIN_ROOT}/scripts/feedback.py impact-preview-results --sessions-analyzed N --coding-sessions N --not-applicable N --no-improvement-needed N --could-be-improved N --insufficient-evidence N --add N --adjust N --remove N`

Every count is required, and each must match the report. The four session
statuses must sum to the number of sessions analyzed. Sessions that changed code
are a subset of those analyzed, and sessions that could be improved are a subset
of those that changed code.
