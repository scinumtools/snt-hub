#!/usr/bin/env bash
# Build the Python environment, test DIPL, generate, or compile a bundled setup.
set -euo pipefail

DIP_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
AREPO_DIR=$(cd -- "$DIP_DIR/../source" && pwd)
BASE_PYTHON=${PYTHON:-python3}
PYTHON_BIN=$BASE_PYTHON
VENV_DIR="$DIP_DIR/.venv"
OUTPUT_ROOT=${DIP_OUTPUT_ROOT:-$DIP_DIR/generated}
case $OUTPUT_ROOT in
  /*) ;;
  *) OUTPUT_ROOT="$PWD/$OUTPUT_ROOT" ;;
esac

usage() {
  cat <<'EOF'
Usage: projects/arepo/dipl/setup.sh -b
       projects/arepo/dipl/setup.sh -t
       projects/arepo/dipl/setup.sh -g SETUP
       projects/arepo/dipl/setup.sh -c SETUP
       projects/arepo/dipl/setup.sh -g SETUP -c

  -b          Create dipl/.venv and install SciNumTools3 0.9.0+ from PyPI.
  -t          Run the DIP test suite.
  -g SETUP    Generate Config.sh, param.txt, and supporting files.
  -c [SETUP]  Generate, then compile Arepo for SETUP (or the -g setup).
  -h          Show this help.

Flags can be combined, for example -b -t -g SETUP. An existing dipl/.venv is
used automatically. Outputs go to dipl/generated/SETUP/. Set SYSTYPE or
configure Makefile.systype before compiling. Set PYTHON to choose Python 3.
EOF
}

fail() {
  printf 'setup.sh: %s\n' "$*" >&2
  exit 2
}

set_setup() {
  local requested=$1
  [[ "$requested" =~ ^[a-zA-Z0-9_]+$ ]] || fail "Invalid setup name: $requested"
  [[ -z "$setup" || "$setup" == "$requested" ]] || fail "Conflicting setups: $setup and $requested"
  setup=$requested
}

setup=""
run_tests=false
build_venv=false
generate=false
compile=false

while (($#)); do
  case $1 in
    -b)
      build_venv=true
      shift
      ;;
    -t)
      run_tests=true
      shift
      ;;
    -g)
      (($# >= 2)) || fail "-g requires a setup name"
      set_setup "$2"
      generate=true
      shift 2
      ;;
    -c)
      compile=true
      generate=true
      shift
      if (($#)) && [[ $1 != -* ]]; then
        set_setup "$1"
        shift
      fi
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown argument: $1 (use -h for help)"
      ;;
  esac
done

if ! $build_venv && ! $run_tests && ! $generate; then
  usage >&2
  exit 2
fi
if $generate; then
  [[ -n "$setup" ]] || fail "Specify a setup with -g SETUP or -c SETUP"
  [[ -f "$DIP_DIR/examples/$setup/DIPfile" ]] || fail "Unknown setup: $setup"
fi
if $compile && [[ -z "${SYSTYPE:-}" && ! -f "$AREPO_DIR/Makefile.systype" ]]; then
  fail "Set SYSTYPE or configure $AREPO_DIR/Makefile.systype before compiling"
fi

if $build_venv; then
  "$BASE_PYTHON" -m venv --clear "$VENV_DIR"
  PYTHON_BIN="$VENV_DIR/bin/python"
  "$PYTHON_BIN" -m pip install --upgrade --index-url https://pypi.org/simple 'scinumtools3>=0.9.0' pytest
  env -u PYTHONPATH "$PYTHON_BIN" -c 'from scinumtools3.dip import DIP; parser = DIP(); parser.add_string("answer int = 42"); assert parser.parse().select("?answer")[0].value == 42; print("SciNumTools3 ready")'
elif [[ -z "${PYTHON:-}" && -x "$VENV_DIR/bin/python" ]]; then
  PYTHON_BIN="$VENV_DIR/bin/python"
fi

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$DIP_DIR/src"

if $run_tests; then
  "$PYTHON_BIN" -B -m pytest "$DIP_DIR/tests"
fi

if $generate; then
  output="$OUTPUT_ROOT/$setup"
  "$PYTHON_BIN" -B -m arepo_dipl generate --setup "$setup" --output "$output"
fi

if $compile; then
  make_args=(
    "CONFIG=$output/Config.sh"
    "BUILD_DIR=$output/build"
    "EXEC=$output/Arepo"
    "PYTHON=$PYTHON_BIN"
  )
  if [[ -n "${SYSTYPE:-}" ]]; then
    export SYSTYPE
  fi
  (cd "$AREPO_DIR" && make "${make_args[@]}")
  printf 'Compiled %s\n' "$output/Arepo"
fi
