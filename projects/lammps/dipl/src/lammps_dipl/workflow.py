"""Local LAMMPS CMake build and execution for complete LJ setups."""

from __future__ import annotations

from pathlib import Path

from snt_hub_runtime.setup import HubSetupError, _source_dirty
from snt_hub_runtime.workflow import (complete_setup, digest, execute, new_build_output, run_project,
                                      workspace, write_lock)


def build(bundle_path: Path, source_path: Path, workspace_path: Path,
          output_path: Path, profile: str, setup_path: Path | None = None) -> Path:
    bundle, root, source = workspace(bundle_path, source_path, workspace_path)
    setup = complete_setup(bundle, setup_path)[0] if setup_path is not None else None
    if profile != "local":
        raise HubSetupError(f"Unknown LAMMPS build profile: {profile}")
    if not (source / "cmake" / "CMakeLists.txt").is_file():
        raise HubSetupError("Pinned LAMMPS source has no CMake project")
    output = new_build_output(root, output_path)
    output.mkdir(parents=True)
    cmake_dir = output / "cmake"
    configure = ["cmake", "-S", str(source / "cmake"), "-B", str(cmake_dir),
                 "-D", "BUILD_MPI=OFF", "-D", "BUILD_OMP=OFF",
                 "-D", "CMAKE_BUILD_TYPE=Release"]
    execute(configure, root, output / "configure.log")
    command = ["cmake", "--build", str(cmake_dir), "--target", "lmp", "--parallel", "2"]
    execute(command, root, output / "build.log")
    executable = cmake_dir / "lmp"
    if not executable.is_file():
        raise HubSetupError("LAMMPS build returned success without creating lmp")
    cache = cmake_dir / "CMakeCache.txt"
    compiler = next((line.split("=", 1)[1] for line in
                     (cache.read_text().splitlines() if cache.is_file() else [])
                     if line.startswith("CMAKE_CXX_COMPILER:FILEPATH=")), "CMake C++ compiler")
    write_lock(output / "build-lock.json", {
        "project": "lammps", "source_revision": bundle.record["source_revision"],
        "source_dirty": _source_dirty(source), "profile": profile,
        **({"setup": str(setup.relative_to(root)),
            "setup_lock_sha256": digest(setup / "setup-lock.json")} if setup else {}),
        "compiler": compiler, "build_options": ["BUILD_MPI=OFF", "BUILD_OMP=OFF",
                                                "CMAKE_BUILD_TYPE=Release"],
        "configure_command": configure, "build_command": command,
        "executable": "cmake/lmp", "executable_sha256": digest(executable),
        "configure_log": "configure.log", "build_log": "build.log",
    })
    return output


def run(bundle_path: Path, source_path: Path, workspace_path: Path,
        setup_path: Path, executable_path: Path) -> Path:
    bundle, _, _ = workspace(bundle_path, source_path, workspace_path)
    return run_project(bundle, setup_path, executable_path, input_file="in.lammps",
                       arguments=["-in", "in.lammps", "-log", "log.lammps"],
                       log_name="run.log", project_label="LAMMPS",
                       extra_lock={"solver_log": str(setup_path.resolve() / "log.lammps")})
