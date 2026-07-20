#!/usr/bin/env bash
# Produce a repeatable source inventory of UI/processing coupling.
#
# Run from the StoryToolkitAI repository root:
#
#   bash scripts/audit_ui_coupling.sh
#
# The report is written to /tmp/storytoolkitai-ui-coupling-audit.txt by
# default. Pass another path as the first argument to override it. The script
# does not modify source files.

set -euo pipefail

if ! command -v rg >/dev/null 2>&1; then
  echo "error: ripgrep (rg) is required. Install it on macOS with: brew install ripgrep" >&2
  exit 1
fi

if [[ ! -d storytoolkitai ]]; then
  echo "error: run this script from the StoryToolkitAI repository root" >&2
  exit 1
fi

REPORT="${1:-/tmp/storytoolkitai-ui-coupling-audit.txt}"
mkdir -p "$(dirname "$REPORT")"

# Keep searches in one helper so a query with no matches does not terminate the
# script under `set -e`. No match is useful evidence and should be recorded.
run_search() {
  local title="$1"
  shift

  {
    printf '\n============================================================\n'
    printf '%s\n' "$title"
    printf '============================================================\n'
    printf 'Command: rg'
    printf ' %q' "$@"
    printf '\n\n'

    rg "$@" || true
  } >>"$REPORT"
}

{
  echo "StoryToolkitAI UI/processing coupling audit"
  echo "Generated: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "Branch: $(git branch --show-current 2>/dev/null || echo unknown)"
  echo "Commit: $(git rev-parse HEAD 2>/dev/null || echo unknown)"
} >"$REPORT"

run_search \
  "Processing references to UI concepts" \
  -n --glob '*.py' \
  'toolkit_UI_obj|notify_via_os|notify_via_messagebox|AskDialog|ask_for_target_dir|receive_notification' \
  storytoolkitai

run_search \
  "Observer and callback coupling" \
  -n --glob '*.py' \
  'attach_observer|dettach_observer|notify_observers|add_observer_to_window|window\.after\(' \
  storytoolkitai

run_search \
  "UI access to queue implementation" \
  -n --glob '*.py' \
  'processing_queue|queue_history|queue_threads|queue_tasks|get_all_queue_items|get_item\(|set_to_canceled' \
  storytoolkitai/ui

run_search \
  "Shared NLE state and Resolve calls" \
  -n --glob '*.py' \
  '\bNLE\.|execute_resolve_operation|resolve_check_timeline|resolve_api|resolve_enable|resolve_disable' \
  storytoolkitai/ui storytoolkitai/core

run_search \
  "Search objects and UI-owned worker threads" \
  -n --glob '*.py' \
  'TextSearch\(|VideoSearch\(|ToolkitSearch\(|Thread\(|index_text|index_video' \
  storytoolkitai/ui storytoolkitai/core/toolkit_ops/search.py

run_search \
  "Broad model construction in UI" \
  -n --glob '*.py' \
  'Project\(|Transcription\(|Story\(|Document\(|ToolkitAssistant\(' \
  storytoolkitai/ui

run_search \
  "Ambient runtime-mode reads" \
  -n --glob '*.py' \
  'sys\.argv|cli_args|--noresolve|--mode.?cli|subprocess\.(Popen|run)' \
  storytoolkitai/core storytoolkitai/integrations

run_search \
  "Direct UI imports from processing" \
  -n --glob '*.py' \
  '(^|[[:space:]])(from|import)[[:space:]]+storytoolkitai\.ui|from[[:space:]]+\.\.?ui' \
  storytoolkitai/core storytoolkitai/integrations

run_search \
  "Wildcard ToolkitOps import in UI" \
  -n --glob '*.py' \
  'from storytoolkitai\.core\.toolkit_ops\.toolkit_ops import \*' \
  storytoolkitai/ui

printf '\nAudit written to %s\n' "$REPORT"
