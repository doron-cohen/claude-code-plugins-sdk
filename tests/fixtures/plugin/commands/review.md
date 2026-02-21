---
name: example-plugin:review
description: Run a code review on the current changes
argument-hint: "[--strict]"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
agent: example-reviewer
---

Run a comprehensive code review. If `--strict` is passed, enforce all style guidelines strictly.

Focus on: $ARGUMENTS
