export type GraphParameter = {
  id: string;
  path: string;
  value: string;
  description: string;
  internal: boolean;
  schema: string;
  reads: string[];
};

export type GraphNode = {
  id: string;
  label: string;
  kind: 'root' | 'group' | 'parameter' | 'schema';
  path?: string;
  parameterId?: string;
  value?: string;
  description?: string;
  count?: number;
  sourceUrl?: string;
};

export type GraphLink = {
  source: string;
  target: string;
  kind: 'hierarchy' | 'schema' | 'dependency';
};

export function buildParameterGraph(parameters: GraphParameter[], includeInternals = false, schemaSources: Record<string, string> = {}) {
  const entries = parameters.filter((parameter) => includeInternals || !parameter.internal);
  const parameterPaths = new Set(entries.map((parameter) => parameter.path));
  const nodes = new Map<string, GraphNode>();
  const links: GraphLink[] = [];
  const linkIds = new Set<string>();
  const rootId = 'root:model';
  nodes.set(rootId, { id: rootId, label: 'DIPL model', kind: 'root' });

  const addLink = (source: string, target: string, kind: GraphLink['kind']) => {
    const key = `${kind}\0${source}\0${target}`;
    if (!linkIds.has(key)) {
      links.push({ source, target, kind });
      linkIds.add(key);
    }
  };

  for (const parameter of entries) {
    let prefix = '';
    let parent = rootId;
    for (const segment of parameter.path.split('.')) {
      prefix = prefix ? `${prefix}.${segment}` : segment;
      const isParameter = parameterPaths.has(prefix);
      const id = `${isParameter ? 'parameter' : 'group'}:${prefix}`;
      if (!nodes.has(id)) {
        nodes.set(id, { id, label: segment, kind: isParameter ? 'parameter' : 'group', path: prefix });
      }
      addLink(parent, id, 'hierarchy');
      parent = id;
    }
    const node = nodes.get(`parameter:${parameter.path}`)!;
    node.parameterId = parameter.id;
    node.value = parameter.value;
    node.description = parameter.description;

    if (parameter.schema) {
      const schemaId = `schema:${parameter.schema}`;
      if (!nodes.has(schemaId)) nodes.set(schemaId, { id: schemaId, label: parameter.schema, kind: 'schema', count: 0, sourceUrl: schemaSources[parameter.schema] });
      nodes.get(schemaId)!.count = (nodes.get(schemaId)!.count ?? 0) + 1;
      addLink(schemaId, node.id, 'schema');
    }
  }

  for (const parameter of entries) {
    for (const read of parameter.reads) {
      if (parameterPaths.has(read)) {
        addLink(`parameter:${read}`, `parameter:${parameter.path}`, 'dependency');
      }
    }
  }

  return { nodes: [...nodes.values()], links };
}
