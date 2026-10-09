"""Arepo's setup-specific Make build and local execution."""

from __future__ import annotations

import os
from pathlib import Path
import platform
import subprocess

from snt_hub_runtime.setup import HubSetupError, _source_dirty
from snt_hub_runtime.workflow import complete_setup, digest, execute, verify_executable, workspace, write_lock


def build(bundle_path: Path, source_path: Path, workspace_path: Path,
          setup_path: Path | None, output_path: Path, profile: str) -> Path:
    bundle, root, source = workspace(bundle_path, source_path, workspace_path)
    if setup_path is None:
        raise HubSetupError("Arepo build requires --setup-dir (its Config.sh is setup-specific)")
    setup, _ = complete_setup(bundle, setup_path)
    config = setup / "Config.sh"
    if not config.is_file():
        raise HubSetupError("Prepared Arepo setup has no Config.sh")
    if profile != "local":
        raise HubSetupError(f"Unknown Arepo build profile: {profile}")
    system = platform.system()
    if system not in {"Darwin", "Linux"}:
        raise HubSetupError(f"No local Arepo toolchain recipe for {system}")
    output = output_path.resolve()
    if root not in output.parents or output.exists():
        raise HubSetupError("Build output must be a new directory inside the workspace")
    executable = output / "Arepo"
    systype = "Darwin" if system == "Darwin" else "Ubuntu"
    command = ["make", f"CONFIG={config}", f"BUILD_DIR={output / 'obj'}", f"EXEC={executable}"]
    # Make's command-line variables allow site-specific compiler and library settings.
    make_vars = os.environ.get("SNT_HUB_AREPO_MAKE_VARS", "")
    allowed_vars = {"CC", "LINKER", "OPTIMIZE", "MPICH_INCL", "MPICH_LIB", "GSL_INCL",
                    "GSL_LIB", "HDF5_INCL", "HDF5_LIB", "FFTW_INCL", "FFTW_LIBS",
                    "HWLOC_INCL", "HWLOC_LIB", "GMP_LIB", "MATH_LIB"}
    for item in make_vars.split(";"):
        if item:
            key, sep, value = item.partition("=")
            if not sep or key not in allowed_vars or "\n" in value:
                raise HubSetupError("SNT_HUB_AREPO_MAKE_VARS contains an unsupported Make override")
            command.append(f"{key}={value}")
    output.mkdir(parents=True)
    execute(command, source, output / "build.log", env={**os.environ, "SYSTYPE": systype})
    if not executable.is_file():
        raise HubSetupError("Arepo build returned success without creating Arepo")
    write_lock(output / "build-lock.json", {
        "project": "arepo", "source_revision": bundle.record["source_revision"],
        "source_dirty": _source_dirty(source),
        "setup": str(setup.relative_to(root)), "setup_lock_sha256": digest(setup / "setup-lock.json"),
        "profile": profile, "systype": systype, "command": command,
        "executable": str(executable),
        "executable_sha256": digest(executable), "build_log": str(output / "build.log"),
    })
    return output


def run(bundle_path: Path, source_path: Path, workspace_path: Path,
        setup_path: Path, executable_path: Path) -> Path:
    bundle, _, _ = workspace(bundle_path, source_path, workspace_path)
    setup, _ = complete_setup(bundle, setup_path)
    if not (setup / "param.txt").is_file():
        raise HubSetupError("Prepared Arepo setup has no param.txt")
    executable = verify_executable(bundle, setup, executable_path)
    if (setup / "run-lock.json").exists():
        raise HubSetupError("This setup already has a run-lock.json")
    command = [str(executable), "param.txt"]
    result = None
    with (setup / "run.log").open("w") as log:
        try:
            result = subprocess.run(command, cwd=setup, stdout=log, stderr=subprocess.STDOUT,
                                    check=False)
            status = result.returncode
        except OSError as exc:
            status = None
            error = str(exc)
    write_lock(setup / "run-lock.json", {
        "project": "arepo", "source_revision": bundle.record["source_revision"],
        "setup_lock_sha256": digest(setup / "setup-lock.json"),
        "input_sha256": {"param.txt": digest(setup / "param.txt")},
        "command": command, "launcher": "direct MPI singleton", "processes": 1,
        "executable": str(executable), "executable_sha256": digest(executable),
        "exit_status": status, "run_log": str(setup / "run.log"),
        **({"start_error": error} if result is None else {}),
    })
    if status != 0:
        raise HubSetupError(f"Arepo run failed; see {setup / 'run.log'}")
    return setup
