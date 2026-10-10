from scinumtools3.dip import Environment, run_adapter_snapshot

from wrf_dipl.generator import ROOT, WrfAdapter, generate


def test_saved_wrf_plan_replays_namelist_and_assets(tmp_path):
    first, replay = tmp_path / "first", tmp_path / "replay"
    source = ROOT.parent / "source"
    generate(first, "hill_2d", source_root=source)
    snapshot = first / "environment.diph5"
    loaded = Environment()
    loaded.load(snapshot)
    plan = loaded.output_plan
    assert plan is not None
    assert any(m.target == "namelist:domains" and m.key == "dx" for m in plan.mappings)
    run_adapter_snapshot(snapshot, WrfAdapter("hill_2d", source), replay)
    for name in ("namelist.input", "input_sounding"):
        assert (first / name).read_bytes() == (replay / name).read_bytes()
