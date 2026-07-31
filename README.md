# datadog-code-analysis

A Claude Code plugin that helps your agent add high-quality logs, metrics, and traces to source code.

## Overview

Coding agents struggle to add useful and well-structured observability to source code. This plugin hooks into your Claude Code session to surface Datadog telemetry best practices while your agent works. At session start and on relevant file edits, it nudges the agent to fetch relevant observability guidance and to apply it when planning features or implementing tasks.

## Requirements

- [Claude Code](https://code.claude.com/docs) with plugin support
- Python 3.10+ (standard library only -- no third-party dependencies)
- A Datadog account: your [Datadog site](https://docs.datadoghq.com/getting_started/site/#access-the-datadog-site) and an API/Application key pair, used to fetch telemetry guidance
- The `claude` CLI available on `PATH` (only needed if you enable on-commit telemetry
  review)

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
sessions -- there's nothing to invoke directly. If you've configured on commit telemetry review or datadog resource suggestions:

- **On-commit telemetry review**: after each commit, reviews the diff against Datadog
  guidance and reports any observability gaps back into your session as suggestions.
- **Datadog resource suggestions**: after a commit that adds telemetry for a new feature,
  nudges the agent to offer creating a supporting Datadog Notebook.

## Contributing

We welcome contributions. Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on
submitting issues and pull requests.

## License

Unless explicitly stated otherwise all files in this repository are licensed under the
Apache License Version 2.0.

This product includes software developed at Datadog (<https://www.datadoghq.com/>).
Copyright 2026 Datadog, Inc.
