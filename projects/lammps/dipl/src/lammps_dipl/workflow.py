"""Local LAMMPS CMake build and execution for complete LJ setups."""

from __future__ import annotations

from pathlib import Path
import subprocess

from snt_hub_runtime.setup import HubSetupError, _source_dirty
from snt_hub_runtime.workflow import (complete_setup, digest, execute, verify_executable,
                                      workspace, write_lock)


def build(bundle_path: Path, source_path: Path, workspace_path: Path,
          output_path: Path, profile: str, setup_path: Path | None = None) -> Path:
    bundle, root, source = workspace(bundle_path, source_path, workspace_path)
    setup = complete_setup(bundle, setup_path)[0] if setup_path is not None else None
    if profile != "local":
        raise HubSetupError(f"Unknown LAMMPS build profile: {profile}")
    if not (source / "cmake" / "CMakeLists.txt").is_file():
        raise HubSetupError("Pinned LAMMPS source has no CMake project")
    output = output_path.resolve()
    if root not in output.parents or output.exists():
        raise HubSetupError("Build output must be a new directory inside the workspace")
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
    setup, _ = complete_setup(bundle, setup_path)
    native = setup / "in.lammps"
    if not native.is_file():
        raise HubSetupError("Prepared LAMMPS setup has no in.lammps")
    executable = verify_executable(bundle, setup, executable_path)
    if (setup / "run-lock.json").exists():
        raise HubSetupError("This setup already has a run-lock.json")
    command = [str(executable), "-in", "in.lammps", "-log", "log.lammps"]
    result = None
    with (setup / "run.log").open("w") as output:
        try:
            result = subprocess.run(command, cwd=setup, stdout=output, stderr=subprocess.STDOUT,
                                    check=False)
            status = result.returncode
        except OSError as exc:
            status = None
            error = str(exc)
    write_lock(setup / "run-lock.json", {
        "project": "lammps", "source_revision": bundle.record["source_revision"],
        "setup_lock_sha256": digest(setup / "setup-lock.json"),
        "input_sha256": {"in.lammps": digest(native)},
        "command": command, "executable": str(executable),
        "executable_sha256": digest(executable), "exit_status": status,
        "run_log": str(setup / "run.log"), "solver_log": str(setup / "log.lammps"),
        **({"start_error": error} if result is None else {}),
    })
    if status != 0:
        raise HubSetupError(f"LAMMPS run failed; see {setup / 'run.log'}")
    return setup
