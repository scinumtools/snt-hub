#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python_bin="${PYTHON_BIN:-python3}"
cd "$repo_root"

usage() {
  cat <<'EOF'
SNT Hub task controller

Usage: ./setup.sh COMMAND [OPTIONS]

Commands:
  scaffold [OPTIONS]   Create a non-published project starter under projects/_drafts/
  docs [OPTIONS]       Generate Brief++ parameter and schema JSON exports
  docs-check [OPTIONS] Check whether those generated exports are current
  qe-import            Reimport QE PWscf examples from the pinned source checkout
  spec-pdf             Build docs/INTEGRATION_SPEC.md as a PDF
  website              Build the static website
  test [OPTIONS]       Check bundles, run Python/browser tests, and build the website
  all                  Regenerate docs, then run the full test/build workflow
  help                 Show this help

Useful environment variables:
  SNT_BIN              SNT executable used by docs generation (default: snt)
  PYTHON_BIN           Python executable used for Hub scripts (default: python3)
  SNT_PYTHON_DIR       Optional local SNT3 Python package directory for tests

Options after a command are passed to its underlying script. Examples:
  ./setup.sh scaffold --id my-code --name "My Code" \
    --source-url https://example.org/my-code --source-revision <commit> \
    --setup example=examples/example/input
  SNT_BIN=../scinumtools3/build/bin/snt ./setup.sh docs --project arepo
  SNT_PYTHON_DIR=../scinumtools3/build/python ./setup.sh test
  ./setup.sh docs-check --project arepo --setup mhd_shock_tube
EOF
}

command="${1:-help}"
if (($#)); then shift; fi

case "$command" in
  scaffold)
    "$python_bin" scripts/scaffold_project.py "$@"
    ;;
  docs)
    "$python_bin" scripts/generate_project_docs.py --snt "${SNT_BIN:-snt}" "$@"
    ;;
  docs-check)
    "$python_bin" scripts/generate_project_docs.py --snt "${SNT_BIN:-snt}" --check "$@"
    ;;
  qe-import)
    "$python_bin" scripts/import_qe_pw_scf.py
    ;;
  spec-pdf)
    scripts/build_integration_spec.sh
    ;;
  website)
    (cd website && npm run build)
    ;;
  test)
    test_args=("$@")
    if [[ -n "${SNT_PYTHON_DIR:-}" ]]; then
      test_args+=(--snt-python-dir "$SNT_PYTHON_DIR")
    fi
    "$python_bin" scripts/test_all.py "${test_args[@]}"
    ;;
  all)
    if (($#)); then
      echo "setup.sh all does not accept arguments; configure SNT_BIN and SNT_PYTHON_DIR in the environment" >&2
      exit 2
    fi
    "$python_bin" scripts/generate_project_docs.py --snt "${SNT_BIN:-snt}"
    test_args=()
    if [[ -n "${SNT_PYTHON_DIR:-}" ]]; then
      test_args+=(--snt-python-dir "$SNT_PYTHON_DIR")
    fi
    "$python_bin" scripts/test_all.py "${test_args[@]}"
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    echo "Unknown command: $command" >&2
    usage >&2
    exit 2
    ;;
esac
