"""Local PWscf build and execution for complete QE setups."""

from __future__ import annotations

from pathlib import Path

from snt_hub_runtime.setup import HubSetupError, _source_dirty
from snt_hub_runtime.workflow import (complete_setup, digest, execute, new_build_output,
                                      run_project, workspace, write_lock)


def build(bundle_path: Path, source_path: Path, workspace_path: Path,
          output_path: Path, profile: str, setup_path: Path | None = None) -> Path:
    bundle, root, source = workspace(bundle_path, source_path, workspace_path)
    setup = complete_setup(bundle, setup_path)[0] if setup_path is not None else None
    if profile != "local":
        raise HubSetupError(f"Unknown QE build profile: {profile}")
    required = ("mbd/CMakeLists.txt", "wannier90/src/wannier_lib.F90",
                "devxlib/src/deviceXlib_mod.f90")
    missing = [name.split("/")[0] for name in required
               if not (source / "external" / name).is_file()]
    if missing:
        raise HubSetupError("QE source needs pinned nested submodules: " + ", ".join(missing) +
                            "; in the fetched workspace run git -C source submodule update --init " +
                            "external/mbd external/wannier90 external/devxlib")
    output = new_build_output(root, output_path)
    output.mkdir(parents=True)
    cmake_dir = output / "cmake"
    configure = ["cmake", "-S", str(source), "-B", str(cmake_dir),
                 "-DQE_ENABLE_MPI=OFF", "-DQE_ENABLE_OPENMP=OFF",
                 "-DQE_ENABLE_SCALAPACK=OFF", "-DQE_ENABLE_HDF5=OFF",
                 "-DQE_ENABLE_TEST=OFF"]
    execute(configure, root, output / "configure.log")
    command = ["cmake", "--build", str(cmake_dir), "--target", "qe_pw_exe", "--parallel", "2"]
    execute(command, root, output / "build.log")
    candidates = list(cmake_dir.rglob("pw.x"))
    if len(candidates) != 1 or not candidates[0].is_file():
        raise HubSetupError("QE build did not produce exactly one pw.x")
    executable = candidates[0]
    write_lock(output / "build-lock.json", {
        "project": "quantum-espresso", "source_revision": bundle.record["source_revision"],
        "source_dirty": _source_dirty(source),
        **({"setup": str(setup.relative_to(root)),
            "setup_lock_sha256": digest(setup / "setup-lock.json")} if setup else {}),
        "profile": profile, "configure_command": configure, "build_command": command,
        "executable": str(executable), "executable_sha256": digest(executable),
        "configure_log": str(output / "configure.log"), "build_log": str(output / "build.log"),
    })
    return output


def run(bundle_path: Path, source_path: Path, workspace_path: Path,
        setup_path: Path, executable_path: Path) -> Path:
    bundle, _, _ = workspace(bundle_path, source_path, workspace_path)
    return run_project(bundle, setup_path, executable_path, input_file="pw.in",
                       arguments=["-i", "pw.in"], log_name="pw.out", project_label="QE")
