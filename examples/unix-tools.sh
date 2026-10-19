#!/bin/bash
# Run with Bridge81's Cygwin adapter. Save shell scripts with LF line endings.
set -eu
printf 'Hello from Bash %s\n' "$BASH_VERSION"
printf 'Working directory: %s\n' "$PWD"
printf 'Argument count: %s\n' "$#"
for argument in "$@"; do printf 'Argument: <%s>\n' "$argument"; done
printf 'Sample Unix pipeline: '
printf 'python\nbash\npython\n' | sort | uniq -c
