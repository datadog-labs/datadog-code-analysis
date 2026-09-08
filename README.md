# datadog-code-analysis

A Claude Code plugin that helps your agent add high-quality logs, metrics, and traces to source code.

## Overview

Coding agents struggle to add useful and well-structured observability to source code. This plugin hooks into your Claude Code session to surface Datadog telemetry best practices while your agent works. At session start and on relevant file edits, it nudges the agent to fetch relevant observability guidance and to apply it when planning features or implementing tasks.

## Requirements

- [Claude Code](https://code.claude.com/docs) with plugin support
- Python 3.10+ (standard library only -- no third-party dependencies)
- A Datadog account: your [Datadog site](https://docs.datadoghq.com/getting_started/site/#access-the-datadog-site) and an API/Application key pair, used to fetch telemetry guidance. The Application Key should have `Datadog Standard Role` as its Owner Role
- The `git` CLI available on `PATH`
- The `claude` CLI available on `PATH` (needed if you enable on-commit telemetry review)

## Installation

Add the marketplace and install the plugin, filling in your Datadog site/credentials:

```bash
claude plugin marketplace add datadog-labs/datadog-code-analysis
claude plugin install datadog-code-analysis@datadog-code-analysis \
  --config dd_site=<your datadog site e.g. datadoghq.com> \
  --config dd_api_key=<your-api-key> \
  --config dd_app_key=<your-app-key> \
  --config enable_on_commit_telemetry_review=<true or false> \
  --config enable_datadog_resource_suggestions=<true or false>
```

Or install interactively from within a Claude Code session:

```
/plugin marketplace add datadog-labs/datadog-code-analysis
/plugin install datadog-code-analysis@datadog-code-analysis
```

> Auto-updates: Enable auto-update so Claude Code automatically picks up plugin improvements. Run /plugin, select the Marketplaces tab, select datadog-code-analysis, then select Enable auto-update.

## Usage

Once installed, the plugin runs automatically in the background during your Claude Code
sessions. If you've configured on commit telemetry review or datadog resource suggestions:

- **On-commit telemetry review**: after each commit, reviews the diff against Datadog
  guidance and reports any observability gaps back into your session as suggestions.
- **Datadog resource suggestions**: after a commit that adds telemetry for a new feature,
  nudges the agent to offer creating a supporting Datadog Notebook.

Two slash commands are also available to review the plugin's impact on your work:

- **`/impact-preview [number of sessions]`**: scans recent Claude Code sessions that did
  *not* use the plugin and estimates where its current telemetry guidance might have been
  relevant.
- **`/impact-review [number of sessions]`**: scans recent Claude Code sessions that *did*
  use the plugin and summarizes where and how its telemetry guidance affected the
  implementation.

Both commands analyze local session transcripts only and print their report directly in
your session. At the end of each report, you're asked whether you're willing to share the
resulting counts with Datadog -- no prompts, file paths, code, or session content are ever
sent, and nothing is sent unless you explicitly agree.

## Filesystem and network access

The plugin reads/writes outside your project directory. Please ensure your session has
read/write access to the following:

- `~/.dd-code-analysis/` -- plugin home directory. Holds per-session plugin state, like
  whether the session loaded best practices and which best practices were loaded.
- The OS temp directory (`$TMPDIR`, typically `/tmp`) -- holds a per-session debug log
  (`dd-code-analysis-plugin-<session_id>.log`) and, during on-commit telemetry review,
  a short-lived diff file (`dd-code-analysis-plugin-<session_id>-review-*.diff`) that's
  deleted after the review runs.

The plugin also makes outbound requests to Datadog to fetch telemetry best practices and
send the usage telemetry described below. Please ensure your session can reach
`https://api.<your-datadog-site>`.

If you're running Claude Code with the [sandboxed Bash tool](https://code.claude.com/docs/en/sandboxing),
you may need to explicitly grant access to these locations, e.g. in `~/.claude/settings.json`
(the OS temp directory is writable by default, so only `~/.dd-code-analysis` and the Datadog
API domain need to be added):

```json
{
  "sandbox": {
    "filesystem": {
      "allowWrite": ["~/.dd-code-analysis"]
    },
    "network": {
      "allowedDomains": ["api.<your-datadog-site>"]
    }
  }
}
```

## Telemetry

The plugin sends basic usage telemetry events back to Datadog. No code content, session content, or user identifiers are sent:

- *Session Started* -- Emitted once at the start of a session
- *Coding Session Started* -- Emitted at most once per session when the agent updates a coding file
- *Edit Nudge Fired* -- Emitted at most once per session if the agent was reminded to consider listing telemetry best practices after a file edit
- *Skills Listed* -- Emitted when the agent lists telemetry best practices
- *Skills Loaded* -- Emitted when the agent loads telemetry best practices
- *Agent Feedback* -- Emitted at most once per session for each loaded best practice; the agent reports whether the best practice was useful
- *Reviewer Ran* -- (If applicable) Emitted at most once per session after the on-commit telemetry reviewer runs
- *Agent Review Feedback* -- (If applicable) Emitted at most once per session; the agent reports whether the review findings were addressed
- *Datadog Resource Creation Nudge Fired* -- (If applicable) Emitted at most once per session when the agent is nudged to offer to create a supporting Datadog resource (e.g. a Notebook)
- *Impact Preview Submitted* -- (If applicable) Emitted when you run `/impact-preview` and explicitly agree to share the resulting session/opportunity counts
- *Impact Review Submitted* -- (If applicable) Emitted when you run `/impact-review` and explicitly agree to share the resulting session/impact counts

Two feedback events (`Agent Feedback`, `Agent Review Feedback`) cost tokens since the main agent 
is being asked to assess utility of guidance/reviews. The cost, however, is minimal since the feedback 
is in the form of enums (yes/no, all/some/none).

All other feedback events are emitted automatically as side-effect of the plugin's hooks. These impose 
no token cost on your agent.

## Contributing

We welcome contributions. Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on
submitting issues and pull requests.

## License

Unless explicitly stated otherwise all files in this repository are licensed under the
Apache License Version 2.0.

This product includes software developed at Datadog (<https://www.datadoghq.com/>).
Copyright 2026 Datadog, Inc.
