export type BriefInline = { type: string; value?: string; target?: string };
export type BriefNode = {
  type: string;
  id?: string;
  roles?: string[];
  title?: BriefInline[];
  content?: BriefInline[];
  children?: BriefNode[];
  rows?: BriefInline[][][];
};
export type BriefDocument = {
  schema: string;
  metadata: { title?: string; subtitle?: string; date?: string; institution?: string };
  children: BriefNode[];
};
export type Field = { label: string; value: string };
export type Parameter = {
  id: string;
  path: string;
  name: string;
  group: string;
  value: string;
  type: string;
  units: string;
  shape: string;
  description: string;
  primary: Field[];
  metadata: Field[];
  provenance: Field[];
  notes: string[];
  internal: boolean;
};

export const inlineText = (items: BriefInline[] = []): string => items.map((item) => item.value ?? '').join('');

function fields(node: BriefNode): Field[] {
  return (node.rows ?? []).map((row) => ({
    label: inlineText(row[0]),
    value: inlineText(row[1]),
  }));
}

export const field = (rows: Field[], label: string): string =>
  rows.find((row) => row.label === label)?.value ?? '';

export function parametersFromBriefpp(report: BriefDocument): Parameter[] {
  if (report.schema !== 'briefpp/1') throw new Error(`Unsupported Brief++ schema: ${report.schema}`);
  const section = report.children.find((node) => node.type === 'section' && inlineText(node.title) === 'Parameters');
  if (!section) throw new Error('Brief++ report has no Parameters section');
  return (section.children ?? []).filter((node) => node.type === 'section').map((node) => {
    const path = inlineText(node.title);
    const tables = (node.children ?? []).filter((child) => child.type === 'table');
    const byRole = (role: string) => tables.flatMap((table) => table.roles?.includes(role) ? fields(table) : []);
    const primary = byRole('snt-primary');
    const metadata = byRole('snt-metadata');
    return {
      id: node.id ?? '',
      path,
      name: path.split('.').at(-1) ?? path,
      group: path.split('.')[0],
      value: field(primary, 'Value'),
      type: field(primary, 'Type'),
      units: field(primary, 'Units'),
      shape: field(primary, 'Shape'),
      description: field(metadata, 'Description'),
      primary,
      metadata,
      provenance: byRole('snt-source'),
      notes: (node.children ?? []).filter((child) => child.type === 'paragraph').map((child) => inlineText(child.content)).filter(Boolean),
      internal: /(^|\.)export\./.test(path),
    };
  });
}

type TreeNode = { label: string; parameter?: Parameter; children: Map<string, TreeNode> };

const escape = (value: string): string => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');

export function parameterTreeHtml(parameters: Parameter[]): string {
  const root: TreeNode = { label: '', children: new Map() };
  for (const parameter of parameters) {
    let node = root;
    for (const segment of parameter.path.split('.')) {
      if (!node.children.has(segment)) node.children.set(segment, { label: segment, children: new Map() });
      node = node.children.get(segment)!;
    }
    node.parameter = parameter;
  }
  const descendants = (node: TreeNode): Parameter[] => [
    ...(node.parameter ? [node.parameter] : []),
    ...[...node.children.values()].flatMap(descendants),
  ];
  const render = (node: TreeNode, depth: number): string => {
    const entries = descendants(node);
    const internalOnly = entries.every((entry) => entry.internal);
    const ownLink = node.parameter ? `<a class="tree-link" href="#${escape(node.parameter.id)}" data-path="${escape(node.parameter.path.toLowerCase())}" data-internal="${node.parameter.internal}">${escape(node.label)}</a>` : '';
    if (!node.children.size) return `<li${internalOnly ? ' data-internal-only="true"' : ''}>${ownLink}</li>`;
    return `<li${internalOnly ? ' data-internal-only="true"' : ''}><details class="tree-branch"${depth === 0 ? ' open' : ''}><summary><span>${escape(node.label.replaceAll('_', ' '))}</span><small>${entries.filter((entry) => !entry.internal).length || entries.length}</small></summary>${ownLink}<ul>${[...node.children.values()].map((child) => render(child, depth + 1)).join('')}</ul></details></li>`;
  };
  return `<ul class="parameter-tree">${[...root.children.values()].map((node) => render(node, 0)).join('')}</ul>`;
}
