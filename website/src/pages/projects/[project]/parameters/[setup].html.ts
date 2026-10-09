export function getStaticPaths() {
  const reports = import.meta.glob('../../../../../../projects/*/docs/parameters/*.json');
  return Object.keys(reports).map((path) => {
    const match = path.match(/\/projects\/([^/]+)\/docs\/parameters\/([^/]+)\.json$/);
    if (!match) throw new Error(`Unexpected parameter report path: ${path}`);
    return { params: { project: match[1], setup: match[2] } };
  });
}

export function GET({ params }: { params: { project: string; setup: string } }) {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  const destination = `${base}/projects/${encodeURIComponent(params.project)}/parameters/${encodeURIComponent(params.setup)}/`;
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=${destination}"><link rel="canonical" href="${destination}"><title>Parameter reference moved</title></head><body><p>This parameter reference has moved to <a href="${destination}">${destination}</a>.</p></body></html>`;
  return new Response(html, { headers: { 'Content-Type': 'text/html; charset=utf-8' } });
}
