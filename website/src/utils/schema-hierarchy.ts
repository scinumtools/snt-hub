export type SchemaMember = {
  name: string;
  relative_path: string;
  kind: string;
  type: string | null;
  units: string | null;
  schema_refs: string[];
  options: string[];
  condition: string | null;
  metadata: { description: string };
  members: SchemaMember[];
};

export type SchemaHierarchy = {
  schema: 'snt-schema-hierarchy/1';
  definitions_available: boolean;
  applications_complete: boolean;
  definitions: { id: string; name: string; metadata: { description: string }; members: SchemaMember[] }[];
  applications: { path: string; kind: string; schema_ids: string[]; inherited_from_collection: boolean | null }[];
  values: { path: string; applied_schema_ids: string[]; contributing_schema_id: string | null }[];
};

export const memberCount = (members: SchemaMember[]): number =>
  members.reduce((count, member) => count + 1 + memberCount(member.members), 0);

export const memberSearch = (members: SchemaMember[]): string =>
  members.map((member) => [member.name, member.metadata.description, ...member.schema_refs, memberSearch(member.members)].join(' ')).join(' ');

export const schemaReferences = (members: SchemaMember[]): string[] =>
  [...new Set(members.flatMap((member) => [...member.schema_refs, ...schemaReferences(member.members)]))];
