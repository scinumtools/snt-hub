"""Local PWscf build and execution for complete QE setups."""

from __future__ import annotations

from pathlib import Path
import subprocess

from snt_hub_runtime.setup import HubSetupError, _source_dirty
from snt_hub_runtime.workflow import complete_setup, digest, execute, verify_executable, workspace, write_lock


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
    output = output_path.resolve()
    if root not in output.parents or output.exists():
        raise HubSetupError("Build output must be a new directory inside the workspace")
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
    setup, _ = complete_setup(bundle, setup_path)
    if not (setup / "pw.in").is_file():
        raise HubSetupError("Prepared QE setup has no pw.in")
    executable = verify_executable(bundle, setup, executable_path)
    if (setup / "run-lock.json").exists():
        raise HubSetupError("This setup already has a run-lock.json")
    command = [str(executable), "-i", "pw.in"]
    result = None
    with (setup / "pw.out").open("w") as output:
        try:
            result = subprocess.run(command, cwd=setup, stdout=output, stderr=subprocess.STDOUT,
                                    check=False)
            status = result.returncode
        except OSError as exc:
            status = None
            error = str(exc)
    write_lock(setup / "run-lock.json", {
        "project": "quantum-espresso", "source_revision": bundle.record["source_revision"],
        "setup_lock_sha256": digest(setup / "setup-lock.json"),
        "input_sha256": {"pw.in": digest(setup / "pw.in")},
        "command": command, "executable": str(executable),
        "executable_sha256": digest(executable), "exit_status": status,
        "run_log": str(setup / "pw.out"),
        **({"start_error": error} if result is None else {}),
    })
    if status != 0:
        raise HubSetupError(f"QE run failed; see {setup / 'pw.out'}")
    return setup
