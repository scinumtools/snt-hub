import assert from 'node:assert/strict';
import test from 'node:test';
import { readdirSync } from 'node:fs';

import { browserProject } from '../src/utils/dipl-project.mjs';
import { loadDIPL } from '../public/vendor/snt-web/index.mjs';

test('browser project packages evaluate and accept representative overrides', async () => {
  const web = await loadDIPL();
  const cases = [
    ['arepo', 'current_sheet_2d', 'hydrodynamics.courant_factor = 0.25', 'hydrodynamics.courant_factor', 0.25],
    ['quantum-espresso', 'si_scf', 'system.ecutwfc = 16', 'system.ecutwfc', 16],
    ['lammps', 'lj_melt', 'dynamics.run_steps = 5', 'dynamics.run_steps', 5],
    ['wrf', 'hill_2d', 'domains.dx = 1500', 'domains.dx', 1500],
  ];
  for (const [project, setup, override, path, expected] of cases) {
    const packaged = browserProject(project, setup);
    assert.equal(packaged.supported, true);
    assert.equal(web.validateProject(packaged.project, override).valid, true);
    const original = web.parseProject(packaged.project);
    const description = original.describe(path);
    assert.ok(description.declaredType, `${project}/${setup}: missing datatype for override editor`);
    assert.ok(Array.isArray(description.options), `${project}/${setup}: missing allowed options for override editor`);
    assert.ok('condition' in description, `${project}/${setup}: missing condition for override editor`);
    const changed = original.withOverride(override);
    const actual = Number(changed.describe(path).valueText);
    assert.ok(Number.isFinite(actual), `${project}/${setup}: override did not produce a numeric value`);
    assert.ok(Math.abs(actual - expected) <= 1e-8 * Math.max(1, Math.abs(expected)),
      `${project}/${setup}: expected ${expected}, got ${actual}`);
    changed.dispose();
    original.dispose();
  }
  assert.equal(browserProject('arepo', 'mhd_shock_tube').supported, false);
});

test('every browser-supported published example evaluates', async () => {
  const web = await loadDIPL();
  let supported = 0;
  let sourceBacked = 0;
  for (const project of ['arepo', 'lammps', 'quantum-espresso', 'wrf']) {
    const directory = new URL(`../../projects/${project}/dipl/examples/`, import.meta.url);
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      const packaged = browserProject(project, entry.name);
      if (!packaged.supported) {
        sourceBacked++;
        continue;
      }
      const result = web.validateProject(packaged.project);
      assert.equal(result.valid, true, `${project}/${entry.name}: ${result.diagnostic?.message}`);
      supported++;
    }
  }
  assert.equal(supported, 48);
  assert.equal(sourceBacked, 7);
});
