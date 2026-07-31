import json
import os


def get_plugin_root():
    return os.environ.get(
        "CLAUDE_PLUGIN_ROOT",
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ).rstrip("/")


def get_plugin_version():
    try:
        plugin_json = os.path.join(get_plugin_root(), ".claude-plugin", "plugin.json")
        with open(plugin_json) as f:
            return json.load(f).get("version", "unknown")
    except Exception:
        return "unknown"


def on_commit_telemetry_review_enabled():
    return os.environ.get("CLAUDE_PLUGIN_OPTION_ENABLE_ON_COMMIT_TELEMETRY_REVIEW", "false").lower() not in (
        "false",
        "0",
    )


def resource_suggestions_enabled():
    return os.environ.get("CLAUDE_PLUGIN_OPTION_ENABLE_DATADOG_RESOURCE_SUGGESTIONS", "false").lower() not in (
        "false",
        "0",
    )
