"""Shared checks and provenance for opt-in local build/run adapters."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess

from .setup import HubSetupError, ProjectBundle, _pinned_revision


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def new_build_output(workspace_root: Path, output_path: Path) -> Path:
    output = output_path.resolve()
    if workspace_root.resolve() not in output.parents or output.exists():
        raise HubSetupError("Build output must be a new directory inside the workspace")
    return output


def workspace(bundle_path: Path, source_path: Path, workspace_path: Path) -> tuple[ProjectBundle, Path, Path]:
    root = workspace_path.resolve()
    bundle = ProjectBundle.load(root)
    source = source_path.resolve()
    if bundle_path.resolve() != root / "dipl" or source != root / "source":
        raise HubSetupError("Bundle and source must belong to this local Hub workspace")
    _pinned_revision(source, bundle.record["source_revision"])
    return bundle, root, source


def prepared_setup(bundle: ProjectBundle, setup_path: Path) -> tuple[Path, dict]:
    setup = setup_path.resolve()
    if not setup.is_dir() or bundle.root not in setup.parents:
        raise HubSetupError("Setup must be a directory inside this workspace")
    lock_path = setup / "setup-lock.json"
    if not lock_path.is_file():
        raise HubSetupError("Prepared setup has no setup-lock.json")
    lock = json.loads(lock_path.read_text())
    if (lock.get("project") != bundle.record["id"] or
            lock.get("source_revision") != bundle.record["source_revision"] or
            lock.get("capability") not in {"complete", "native-inputs-only"}):
        raise HubSetupError("Prepared setup does not match this pinned source")
    return setup, lock


def complete_setup(bundle: ProjectBundle, setup_path: Path) -> tuple[Path, dict]:
    setup, lock = prepared_setup(bundle, setup_path)
    if lock["capability"] != "complete":
        raise HubSetupError("Run requires a complete setup")
    return setup, lock


def verify_executable(bundle: ProjectBundle, setup: Path, executable_path: Path) -> Path:
    executable = executable_path.resolve()
    if not executable.is_file():
        raise HubSetupError(f"Executable does not exist: {executable}")
    build_root = bundle.root / "build"
    if executable.is_relative_to(build_root):
        lock_path = next((parent / "build-lock.json" for parent in executable.parents
                          if parent.is_relative_to(build_root) and
                          (parent / "build-lock.json").is_file()), None)
        if lock_path is None:
            raise HubSetupError("Workspace build executable has no build-lock.json")
        lock = json.loads(lock_path.read_text())
        declared = Path(lock.get("executable", ""))
        declared = (declared if declared.is_absolute() else lock_path.parent / declared).resolve()
        if (lock.get("project") != bundle.record["id"] or
                lock.get("source_revision") != bundle.record["source_revision"] or
                declared != executable or
                lock.get("executable_sha256") != digest(executable)):
            raise HubSetupError("Build lock does not match this executable and pinned source")
        if (lock.get("setup_lock_sha256") is not None and
                lock["setup_lock_sha256"] != digest(setup / "setup-lock.json")):
            raise HubSetupError("Build was made for a different setup")
    return executable


def execute(command: list[str], cwd: Path, log: Path, *, env: dict[str, str] | None = None) -> None:
    with log.open("w") as output:
        try:
            result = subprocess.run(command, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT,
                                    check=False)
        except OSError as exc:
            raise HubSetupError(f"Cannot start {command[0]}: {exc}") from exc
    if result.returncode:
        raise HubSetupError(f"Command failed ({result.returncode}); see {log}")


def write_lock(path: Path, data: dict) -> None:
    path.write_text(json.dumps({"schema_version": 1, **data}, indent=2) + "\n")


def run_project(bundle: ProjectBundle, setup_path: Path, executable_path: Path, *,
                input_file: str, arguments: list[str], log_name: str,
                project_label: str, extra_lock: dict | None = None) -> Path:
    setup, _ = complete_setup(bundle, setup_path)
    native = setup / input_file
    if not native.is_file():
        raise HubSetupError(f"Prepared {project_label} setup has no {input_file}")
    executable = verify_executable(bundle, setup, executable_path)
    if (setup / "run-lock.json").exists():
        raise HubSetupError("This setup already has a run-lock.json")
    command = [str(executable), *arguments]
    status = None
    error = None
    with (setup / log_name).open("w") as log:
        try:
            status = subprocess.run(command, cwd=setup, stdout=log,
                                    stderr=subprocess.STDOUT, check=False).returncode
        except OSError as exc:
            error = str(exc)
    write_lock(setup / "run-lock.json", {
        "project": bundle.record["id"], "source_revision": bundle.record["source_revision"],
        "setup_lock_sha256": digest(setup / "setup-lock.json"),
        "input_sha256": {input_file: digest(native)},
        "command": command, "executable": str(executable),
        "executable_sha256": digest(executable), "exit_status": status,
        "run_log": str(setup / log_name),
        **({"start_error": error} if error is not None else {}),
        **(extra_lock or {}),
    })
    if status != 0:
        raise HubSetupError(f"{project_label} run failed; see {setup / log_name}")
    return setup
