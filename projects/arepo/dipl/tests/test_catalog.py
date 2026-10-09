from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from arepo_dipl.inventory import runtime_tags, template_flags


ROOT = Path(__file__).parents[2]
SOURCE_ROOT = ROOT / "source"
DIP_ROOT = ROOT / "dipl"


class CatalogTests(unittest.TestCase):
    def test_arepo_inventory_is_readable(self):
        self.assertIn("COOLING", template_flags(SOURCE_ROOT))
        self.assertIn("PMGRID", template_flags(SOURCE_ROOT))
        self.assertIn("InitCondFile", runtime_tags(SOURCE_ROOT))

    def test_mhd_setup_is_registered(self):
        from arepo_dipl.generator import SETUPS

        for setup in ("mhd_shock_tube", "cosmological_gravity_only"):
            self.assertEqual(SETUPS[setup].name, "DIPfile")
            self.assertTrue(SETUPS[setup].is_file())

    def test_every_arepo_example_has_a_dipl_setup(self):
        from arepo_dipl.generator import SETUPS

        expected = {
            "alfven_wave_1d",
            "cosmo_zoom_gravity_only_3d",
            "current_sheet_2d",
            "galaxy_merger_star_formation_3d",
            "gresho_2d",
            "interacting_blastwaves_1d",
            "isolated_galaxy_collisionless_3d",
            "noh_2d",
            "noh_3d",
            "polytrope_1d_spherical",
            "shocktube_1d",
            "wave_1d",
            "yee_2d",
        }
        self.assertTrue(expected <= set(SETUPS))
        self.assertEqual(16, len(SETUPS))

    def test_every_profile_instantiates_the_shared_runtime_schemas(self):
        schemas = DIP_ROOT / "profiles" / "schemas"
        build_schema = (schemas / "build.dip").read_text()
        self.assertIn("$schema arepo_build", build_schema)
        self.assertNotIn("enabled bool", build_schema)
        self.assertIn("particle_mesh bool = false\n      ?descr", build_schema)
        self.assertIn("grid_resolution int = 0", build_schema)
        self.assertTrue((schemas / "cosmology.dip").is_file())
        self.assertTrue((schemas / "experiment.dip").is_file())
        self.assertTrue((schemas / "analysis.dip").is_file())
        self.assertTrue((schemas / "cooling.dip").is_file())
        self.assertTrue((schemas / "star_formation.dip").is_file())
        self.assertTrue((schemas / "snapshots.dip").is_file())
        self.assertTrue((schemas / "input.dip").is_file())
        self.assertTrue((schemas / "output.dip").is_file())
        self.assertTrue((schemas / "resources.dip").is_file())
        self.assertTrue((schemas / "simulation.dip").is_file())
        self.assertTrue((schemas / "gravity.dip").is_file())
        self.assertTrue((schemas / "hydrodynamics.dip").is_file())
        self.assertTrue((schemas / "mesh.dip").is_file())
        self.assertIn("force_accuracy : gravity_force_accuracy", (schemas / "gravity.dip").read_text())
        self.assertIn("$schema gravity_softening_length", (schemas / "gravity.dip").read_text())
        self.assertIn("setup : experiment_setup_selection", (schemas / "experiment.dip").read_text())
        self.assertIn("subfind : subfind_analysis_settings", (schemas / "analysis.dip").read_text())
        self.assertIn("regularization : mesh_regularization", (schemas / "mesh.dip").read_text())
        units = (schemas / "arepo_units.dip").read_text()
        self.assertIn("$unit arepo_length = {?code_units.length}", units)
        self.assertIn("$unit arepo_density = 1*arepo_mass/arepo_length3", units)
        self.assertIn("initial_conditions : initial_conditions_settings", (schemas / "input.dip").read_text())
        self.assertIn("snapshots : snapshot_settings", (schemas / "output.dip").read_text())
        resources = (schemas / "resources.dip").read_text()
        simulation = (schemas / "simulation.dip").read_text()
        self.assertIn("wall_clock : wall_clock_resources", resources)
        self.assertIn("limit float s\n    !condition ({.} > 0 s)", resources)
        self.assertIn("time : simulation_time", simulation)
        self.assertIn("size float arepo_length\n    !condition ({.} > 0 arepo_length)", simulation)
        shared_baseline = (
            (DIP_ROOT / "profiles" / "ideal_hydrodynamics.dip").read_text()
            + (DIP_ROOT / "profiles" / "standard_softenings.dip").read_text()
        )
        required_roots = (
            "input : input_settings",
            "output : output_settings",
            "resources : resources_settings",
            "simulation : simulation_settings",
            "gravity : gravity_settings",
            "hydrodynamics : hydrodynamics_settings",
            "mesh : mesh_settings",
        )
        for profile in (DIP_ROOT / "examples").glob("*/profile.dip"):
            text = profile.read_text()
            self.assertIn("experiment : experiment_settings", text)
            self.assertIn("build : arepo_build", text)
            for root in required_roots:
                self.assertTrue(root in text or root in shared_baseline)
            self.assertTrue(
                "comoving list : gravity_softening_length" in text
                or "comoving list : gravity_softening_length" in shared_baseline
            )
        for name in ("cosmological_star_formation", "cosmological_gravity_only"):
            text = (DIP_ROOT / "examples" / name / "profile.dip").read_text()
            self.assertIn("analysis : analysis_settings", text)


if __name__ == "__main__":
    unittest.main()
