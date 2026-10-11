from scinumtools3.dip import Environment, run_adapter_snapshot

from qe_dipl.generator import PwAdapter, generate


def test_saved_pw_plan_replays_native_input(tmp_path):
    first, replay = tmp_path / "first", tmp_path / "replay"
    generate(first, "si_scf")
    snapshot = first / "environment.diph5"
    loaded = Environment()
    loaded.load(snapshot)
    plan = loaded.output_plan
    assert plan is not None
    tagged_paths = {node.name for node in loaded.select("?", tags_all=["qe:param"])}
    assert tagged_paths
    assert tagged_paths <= {mapping.source_path for mapping in plan.mappings}
    assert any(m.target == "namelist:SYSTEM" and m.key == "ecutwfc" for m in plan.mappings)
    assert any(m.target == "card:ATOMIC_SPECIES" for m in plan.mappings)
    run_adapter_snapshot(snapshot, PwAdapter(), replay)
    assert (first / "pw.in").read_bytes() == (replay / "pw.in").read_bytes()
