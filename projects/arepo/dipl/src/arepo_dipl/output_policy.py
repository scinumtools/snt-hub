"""Arepo native-output decisions; these are adapter rules, not DIPL parameters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scinumtools3.dip import ValueNode

from .rendering import GenerationError, value_at


@dataclass(frozen=True)
class Rule:
    enabled: bool = True
    omit_nonpositive: bool = False
    requires: tuple[str, ...] = ()


def requires(feature: str, *, omit_nonpositive: bool = False) -> Rule:
    return Rule(requires=(feature,), omit_nonpositive=omit_nonpositive)


# Only exceptions to ordinary tagged-node export belong here. The DIPL model
# still owns values, units, descriptions, and native names.
RULES: dict[str, Rule] = {
    **{f"build.boundaries.{axis}_mode": Rule(omit_nonpositive=True) for axis in "xyz"},
    "build.physics.adiabatic_index": Rule(omit_nonpositive=True),
    "build.gravity.direct_summation.threshold": requires("build.gravity.direct_summation"),
    "build.gravity.individual_softening_type_mask": Rule(omit_nonpositive=True),
    "build.gravity.particle_mesh.grid_resolution": requires("build.gravity.particle_mesh"),
    "build.gravity.particle_mesh.short_range_cutoff": requires("build.gravity.particle_mesh"),
    "build.gravity.particle_mesh.high_resolution_type_mask": requires("build.gravity.particle_mesh", omit_nonpositive=True),
    "build.gravity.particle_mesh.enlarge_high_resolution_region": requires("build.gravity.particle_mesh", omit_nonpositive=True),
    "build.gravity.particle_mesh.high_resolution_grid_boost": requires("build.gravity.particle_mesh", omit_nonpositive=True),
    "build.gravity.softening_types": Rule(enabled=False),
    "build.analysis.fof.primary_link_type_mask": requires("build.analysis.fof"),
    "build.analysis.fof.secondary_link_type_mask": requires("build.analysis.fof"),
    "mesh.regularization.maximum_face_angle_factor": requires("build.mesh.face_angle_regularization"),
    "mesh.regularization.shaping_factor": Rule(enabled=False),
    **{f"mesh.refinement.{name}": requires("build.mesh.refinement") for name in (
        "reference_gas_mass", "target_gas_mass_factor", "refinement_criterion", "derefinement_criterion")},
    "gravity.hydro.minimum_comoving": requires("build.mesh.adaptive_hydro_softening"),
    "gravity.hydro.spacing": requires("build.mesh.adaptive_hydro_softening"),
    "resources.wall_clock.log_flush_interval": requires("build.io.reduced_flush"),
    **{f"star_formation.{name}": requires("build.physics.star_formation") for name in (
        "critical_overdensity", "temperature_threshold", "critical_physical_density",
        "supernova_temperature", "cloud_temperature", "maximum_timescale",
        "supernova_factor", "evaporation_factor")},
    "datasets.uv_background": requires("build.physics.cooling"),
}


# Profile choices change output policy without introducing export fields into
# the parameter tree. OutputPlan replacements retain both declaration origins.
PROFILE_OVERRIDES: dict[str, dict[str, bool]] = {
    "cosmological_star_formation": {"build.gravity.softening_types": True},
    "galaxy_merger_star_formation_3d": {"build.gravity.softening_types": True},
    "cosmological_gravity_only": {"mesh.regularization.shaping_factor": True,
                                   "build.gravity.softening_types": True},
    "cosmo_zoom_gravity_only_3d": {"mesh.regularization.shaping_factor": True},
    "isolated_galaxy_collisionless_3d": {"mesh.regularization.shaping_factor": True,
                                         "build.gravity.softening_types": True},
    "polytrope_1d_spherical": {"mesh.regularization.shaping_speed": False},
}


DERIVED = {
    "adapter.derived.comoving": ("ComovingIntegrationOn", "simulation.time.coordinate", "scale_factor"),
    "adapter.derived.periodic": ("PeriodicBoundariesOn", "simulation.domain.boundary", "periodic"),
    "adapter.derived.cooling": ("CoolingOn", "build.physics.cooling", True),
    "adapter.derived.star_formation": ("StarformationOn", "build.physics.star_formation", True),
}


def _decision(env: Any, path: str, value: Any, target: str, rule: Rule) -> tuple[bool, str, list[str]]:
    reasons = []
    active = rule.enabled
    if not rule.enabled:
        reasons.append("disabled by default")
    for feature in rule.requires:
        flag = value_at(env, feature)
        if not isinstance(flag, bool):
            raise GenerationError(f"Export dependency `{feature}` must be a boolean feature.")
        active = active and flag
        reasons.append(f"{feature} is true")
    if target == "config" and isinstance(value, bool):
        active = active and value
        reasons.append("flag is true")
    if rule.omit_nonpositive:
        active = active and float(value) > 0
        reasons.append("value is positive")
    return active, "; ".join(reasons) or "tagged native mapping", list(rule.requires)


def describe_outputs(env: Any, outputs: Any, setup: str) -> None:
    candidates = []
    for target in ("config", "param"):
        for node in env.select("?", tags_all=[f"arepo:{target}"]):
            for tag in node.tags:
                if tag.startswith("arepo:") and tag not in ("arepo:config", "arepo:param"):
                    raise GenerationError(f"Unknown export tag `{tag}` on `{node.name}`.")
            if not node.metadata.native:
                raise GenerationError(f"Exported node `{node.name}` has no `?native` metadata.")
            candidates.append((node.name, target, node))
    for name, (_, source, _) in DERIVED.items():
        if env.select("?" + source):
            candidates.append((name, "param", None))

    for path, target, node in sorted(candidates):
        if node is None:
            native, source, expected = DERIVED[path]
            value = value_at(env, source) == expected
            outputs.add_value(f"param:{native}", "param", native, ValueNode(path, value),
                              rule=f"{source} equals {expected!r}", origin="adapter:derived",
                              dependencies=[source])
            continue
        rule = RULES.get(path, Rule())
        active, label, dependencies = _decision(env, path, node.value, target, rule)
        for native in node.metadata.native:
            mapping_id = f"{target}:{native}"
            outputs.add_node(env, mapping_id, target, native, path, active=active,
                             rule=label, origin="adapter:base", dependencies=dependencies)
            override = PROFILE_OVERRIDES.get(setup, {}).get(path)
            if override is not None:
                outputs.replace_node(env, mapping_id, target, native, path,
                                     active=_decision(env, path, node.value, target, Rule())[0]
                                     if override else False,
                                     rule=f"example {setup}: {'enabled' if override else 'disabled'}",
                                     origin=f"example:{setup}", dependencies=dependencies)

    # Indexed native keys are a representation of existing semantic values.
    for prefix, path in (("SofteningComovingType", "gravity.softenings.comoving"),
                         ("SofteningMaxPhysType", "gravity.softenings.physical_maximum")):
        index = 0
        while True:
            source = f"{path}[{index}].length"
            try:
                value_at(env, source)
            except GenerationError:
                break
            native = f"{prefix}{index}"
            outputs.add_node(env, f"param:{native}", "param", native, source,
                             rule="indexed softening length", origin="adapter:indexed")
            index += 1
    particle_map = value_at(env, "gravity.softenings.particle_type_map") if env.select(
        "?gravity.softenings.particle_type_map") else []
    for index, value in enumerate(particle_map):
        native = f"SofteningTypeOfPartType{index}"
        outputs.add_value(f"param:{native}", "param", native,
                          ValueNode(f"adapter.particle_type_map[{index}]", value),
                          rule="indexed particle-type softening", origin="adapter:indexed",
                          dependencies=["gravity.softenings.particle_type_map"])

    for node in env.select(tags_all=["arepo:dataset"]):
        if not node.name.endswith(".output_file"):
            raise GenerationError(f"Dataset tag must be attached to an output_file node: `{node.name}`.")
        dataset = node.name.removesuffix(".output_file")
        rule = RULES.get(dataset, Rule())
        active, label, dependencies = _decision(env, dataset, node.value, "dataset", rule)
        outputs.add_node(env, f"dataset:{dataset}", "dataset", dataset, node.name,
                         active=active, rule=label, origin="adapter:base",
                         dependencies=dependencies)

    if env.select("?output.schedule.enabled"):
        enabled = value_at(env, "output.schedule.enabled")
        if enabled and not env.select("?output.schedule.filename"):
            raise GenerationError("Missing active DIPL node `output.schedule.filename`.")
    if env.select("?output.schedule.filename") and env.select("?output.schedule.enabled"):
        outputs.add_node(env, "schedule:output_list", "schedule", "output_list",
                         "output.schedule.filename", active=value_at(env, "output.schedule.enabled"),
                         rule="output.schedule.enabled is true", origin="adapter:base",
                         dependencies=["output.schedule.enabled"])
