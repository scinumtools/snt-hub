from scinumtools3.dip import Environment, run_adapter_snapshot

from lammps_dipl.generator import LammpsAdapter, generate


def test_saved_lammps_plan_replays_native_input(tmp_path):
    first, replay = tmp_path / "first", tmp_path / "replay"
    generate(first, "lj_minimize_2d")
    snapshot = first / "environment.diph5"
    loaded = Environment()
    loaded.load(snapshot)
    plan = loaded.output_plan
    assert plan is not None
    tagged_paths = {node.name for node in loaded.select("?", tags_all=["lammps:param"])}
    assert tagged_paths
    assert tagged_paths <= {mapping.source_path for mapping in plan.mappings}
    assert any(m.target == "command:region box" and m.source_path == "geometry.xlo"
               for m in plan.mappings)
    assert any(m.target == "command:minimize" for m in plan.mappings)
    run_adapter_snapshot(snapshot, LammpsAdapter(), replay)
    assert (first / "in.lammps").read_bytes() == (replay / "in.lammps").read_bytes()
