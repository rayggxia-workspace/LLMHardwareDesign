#!/bin/bash
set -euo pipefail
echo "Retired symbolic entry. Use the macro-native flow in README.md." >&2
echo "Historical diagnostics require legacy_symbolic_diagnostic.sbatch explicitly." >&2
exit 2
