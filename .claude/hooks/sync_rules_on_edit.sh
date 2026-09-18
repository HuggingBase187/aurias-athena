#!/usr/bin/env bash
# PostToolUse hook: if a tool call touched the screening rulebook, regenerate
# the "Screening Rules — Aurias 2" Google Doc so it can never drift.
# The sync script is a no-op unless the rule sections actually changed.
input=$(cat)
case "$input" in
  *data-template.md*)
    cd "$(dirname "$0")/../skills/generator-ups-data-enrichment/scripts" || exit 0
    PYTHONIOENCODING=utf-8 python sync_screening_rules_doc.py --if-changed >&2 || \
      echo "WARNING: Screening Rules doc sync failed — run sync_screening_rules_doc.py by hand." >&2
    ;;
esac
exit 0
