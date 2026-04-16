#!/usr/bin/env bash
# Script: Run Tests
# Purpose: Execute automated tests for backend and frontend

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" > /dev/null 2>&1 || exit 1; pwd -P)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." > /dev/null 2>&1 || exit 1; pwd -P)"

echo "===================================="
echo "Running Backend Tests (pytest)"
echo "===================================="

cd "$PROJECT_ROOT/backend"
# Run pytest with full verbosity
uv run pytest -v

echo ""
echo "===================================="
echo "Running Frontend Tests (vitest)"
echo "===================================="
cd "$PROJECT_ROOT/frontend"
# Check if vitest is installed, if not, skip
if grep -q "\"vitest\"" package.json; then
    npm run test -- --run
else
    echo "Vitest not configured yet. Skipping frontend tests."
fi

echo ""
echo "All tests completed."
