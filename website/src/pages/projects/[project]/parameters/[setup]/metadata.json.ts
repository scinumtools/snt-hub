import type { APIRoute } from 'astro';

export function getStaticPaths() {
  const exports = import.meta.glob('../../../../../../../projects/*/docs/semantic/*.json', { eager: true, import: 'default' });
  return Object.entries(exports).map(([path, metadata]) => {
    const match = path.match(/\/projects\/([^/]+)\/docs\/semantic\/([^/]+)\.json$/);
    if (!match) throw new Error(`Unexpected semantic metadata path: ${path}`);
    return { params: { project: match[1], setup: match[2] }, props: { metadata } };
  });
}

export const GET: APIRoute = ({ params, props }) => new Response(JSON.stringify(props.metadata), {
  headers: {
    'content-type': 'application/json; charset=utf-8',
    'content-disposition': `attachment; filename="${params.project}-${params.setup}-metadata.json"`,
  },
});
