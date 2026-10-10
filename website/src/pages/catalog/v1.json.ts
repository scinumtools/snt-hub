import hubVersion from '../../../../VERSION?raw';

const records = import.meta.glob('../../../../projects/*/project.json', { eager: true, import: 'default' });
const setupRecords = import.meta.glob('../../../../projects/*/setups.json', { eager: true, import: 'default' });

export const GET = () => {
  const projects = Object.values(records).map((record: any) => {
    const setup = Object.entries(setupRecords).find(([path]) => path.includes(`/projects/${record.id}/`));
    return {
      id: record.id,
      name: record.name,
      source_url: record.source_url,
      source_revision: record.source_revision,
      hub: record.hub,
      setups: setup ? (setup[1] as any).setups : {},
    };
  });
  return new Response(JSON.stringify({
    schema_version: 1,
    hub_version: hubVersion.trim(),
    hub_repository: 'https://github.com/scinumtools/snt-hub.git',
    hub_revision: process.env.GITHUB_SHA ?? 'unreleased',
    projects,
  }, null, 2) + '\n', { headers: { 'Content-Type': 'application/json; charset=utf-8' } });
};
