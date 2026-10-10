import type { APIRoute } from 'astro';
import { browserProject } from '../../../../../utils/dipl-project.mjs';

export function getStaticPaths() {
  const reports = import.meta.glob('../../../../../../../projects/*/docs/parameters/*.json');
  return Object.keys(reports).map((path) => {
    const match = path.match(/\/projects\/([^/]+)\/docs\/parameters\/([^/]+)\.json$/);
    if (!match) throw new Error(`Unexpected parameter report path: ${path}`);
    return { params: { project: match[1], setup: match[2] } };
  });
}

export const GET: APIRoute = ({ params }) => {
  const data = browserProject(params.project!, params.setup!);
  return new Response(JSON.stringify(data), {
    headers: { 'content-type': 'application/json; charset=utf-8' },
  });
};
