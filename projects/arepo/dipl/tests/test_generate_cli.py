import sys

from arepo_dipl.__main__ import main


def test_generate_command_passes_override_to_arepo_generator(tmp_path, monkeypatch):
    override = tmp_path / "tuning.dip"
    override.write_text("resources.wall_clock.limit = 1800 s\n")
    output = tmp_path / "generated"
    monkeypatch.setattr(sys, "argv", ["arepo-dipl", "generate", "--setup", "mhd_shock_tube",
                                  "--output", str(output), "--override-file", str(override)])
    main()
    assert any(line.split() == ["TimeLimitCPU", "1800"] for line in
               (output / "param.txt").read_text().splitlines())
