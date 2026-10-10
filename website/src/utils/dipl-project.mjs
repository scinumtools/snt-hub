/** Package a file-backed Hub setup for SNT's text-backed browser parser. */
import { existsSync, readFileSync, realpathSync } from 'node:fs';
import { resolve, sep } from 'node:path';

const hubRoot = existsSync(resolve(process.cwd(), 'projects'))
  ? process.cwd() : resolve(process.cwd(), '..');

function entries(manifest) {
  const result = [];
  let current;
  for (const line of manifest.split(/\r?\n/)) {
    const section = line.match(/^(code|overrides|sources)\[\]\s*$/);
    if (section) {
      current = { kind: section[1] };
      result.push(current);
      continue;
    }
    const property = line.match(/^\s+(file|name|filepath)\s*=\s*"([^"]+)"\s*$/);
    if (property && current) current[property[1]] = property[2];
  }
  return result;
}

function readWithin(root, base, relative) {
  const path = realpathSync(resolve(base, relative));
  if (!path.startsWith(root + sep)) throw new Error(`DIPL file escapes project bundle: ${relative}`);
  return { name: path.slice(hubRoot.length + 1).replaceAll(sep, '/'), text: readFileSync(path, 'utf8') };
}

function registerCode(input, file) {
  const lines = file.text.split(/\r?\n/);
  const declarations = lines.filter((line) => line.trim() && !line.trimStart().startsWith('#'));
  if (declarations.every((line) => line.startsWith('$unit '))) {
    // Keep declaration order: a custom unit may refer to earlier code values.
    input.code.push(file);
    return;
  }
  if (declarations[0]?.startsWith('$schema ')) {
    let schema;
    for (const line of lines) {
      const match = line.match(/^\$schema\s+(\S+)\s*$/);
      if (match) {
        schema = { name: match[1], text: '' };
        input.schemas.push(schema);
      } else if (schema) {
        schema.text += (line.startsWith('  ') ? line.slice(2) : line) + '\n';
      }
    }
    return;
  }
  input.code.push(file);
}

export function browserProject(projectId, setup) {
  if (!/^[a-z0-9-]+$/.test(projectId) || !/^[a-z0-9_]+$/.test(setup)) {
    throw new Error('Invalid project or setup ID');
  }
  const root = realpathSync(resolve(hubRoot, 'projects', projectId, 'dipl'));
  const directory = resolve(root, 'examples', setup);
  const manifest = entries(readWithin(root, directory, 'DIPfile').text);
  if (manifest.some((entry) => entry.kind === 'sources')) {
    return { supported: false, reason: 'This setup uses table sources that the current SNT browser runtime cannot load.' };
  }
  const input = { units: [], schemas: [], code: [], overrides: [] };
  for (const entry of manifest) {
    if (!entry.file) throw new Error(`Missing file in ${entry.kind} registration`);
    const file = readWithin(root, directory, entry.file);
    if (entry.kind === 'overrides') input.overrides.push(file);
    else registerCode(input, file);
  }
  return { supported: true, project: input };
}
