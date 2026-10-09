"""Arepo's setup-specific Make build and local execution."""

from __future__ import annotations

import os
from pathlib import Path
import platform

from snt_hub_runtime.setup import HubSetupError, _source_dirty
from snt_hub_runtime.workflow import (digest, execute, new_build_output, prepared_setup,
                                      run_project, workspace, write_lock)


def build(bundle_path: Path, source_path: Path, workspace_path: Path,
          setup_path: Path | None, output_path: Path, profile: str) -> Path:
    bundle, root, source = workspace(bundle_path, source_path, workspace_path)
    if setup_path is None:
        raise HubSetupError("Arepo build requires --setup-dir (its Config.sh is setup-specific)")
    setup, _ = prepared_setup(bundle, setup_path)
    config = setup / "Config.sh"
    if not config.is_file():
        raise HubSetupError("Prepared Arepo setup has no Config.sh")
    if profile != "local":
        raise HubSetupError(f"Unknown Arepo build profile: {profile}")
    system = platform.system()
    if system not in {"Darwin", "Linux"}:
        raise HubSetupError(f"No local Arepo toolchain recipe for {system}")
    output = new_build_output(root, output_path)
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
        "executable": executable.relative_to(output).as_posix(),
        "executable_sha256": digest(executable), "build_log": "build.log",
    })
    return output


def run(bundle_path: Path, source_path: Path, workspace_path: Path,
        setup_path: Path, executable_path: Path) -> Path:
    bundle, _, _ = workspace(bundle_path, source_path, workspace_path)
    return run_project(bundle, setup_path, executable_path, input_file="param.txt",
                       arguments=["param.txt"], log_name="run.log", project_label="Arepo",
                       extra_lock={"launcher": "direct MPI singleton", "processes": 1})
