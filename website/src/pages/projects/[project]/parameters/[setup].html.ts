export function getStaticPaths() {
  const reports = import.meta.glob('../../../../../../projects/*/docs/parameters/*.html', { query: '?raw', import: 'default' });
  return Object.keys(reports).map((path) => {
    const match = path.match(/\/projects\/([^/]+)\/docs\/parameters\/([^/]+)\.html$/);
    if (!match) throw new Error(`Unexpected parameter report path: ${path}`);
    return { params: { project: match[1], setup: match[2] }, props: { path } };
  });
}

export async function GET({ props, params }: { props: { path: string }, params: { project: string, setup: string } }) {
  const reports = import.meta.glob('../../../../../../projects/*/docs/parameters/*.html', { query: '?raw', import: 'default' });
  const raw = await reports[props.path]() as string;
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  const page = raw
    .replace('</head>', `<meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="${base}/parameter-report.css"></head>`)
    .replace('<body>', `<body><nav class="hub-report-nav"><a href="${base}/projects/${params.project}/">← ${params.project.toUpperCase()} parameters</a><a href="${base}/">{?SNT.HUB}</a></nav>`);
  return new Response(page, { headers: { 'Content-Type': 'text/html; charset=utf-8' } });
}
