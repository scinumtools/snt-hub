export const integrationLevels = [
  {
    number: '01',
    name: 'Parameter model',
    description: 'A DIPL model describes inputs, units, and constraints. It can be inspected and checked even before a code consumes it.',
    signal: 'Model available',
  },
  {
    number: '02',
    name: 'External adapter',
    description: 'SNT evaluates the model; an adapter writes the code’s familiar input files. The original solver stays unchanged.',
    signal: 'Arepo today',
  },
  {
    number: '03',
    name: 'Code integration',
    description: 'A code uses evaluated SNT parameters through an API or generated static inputs as part of its own workflow.',
    signal: 'A project choice',
  },
] as const;

export const supportStatuses = [
  {
    key: 'independent',
    label: 'Independent',
    cue: 'Unofficial',
    description: 'Developed by SNT contributors or code users. The original code’s maintainers have not reviewed or endorsed this integration.',
    evidence: 'Repository, contributor, source revision, and a clear statement of scope.',
  },
  {
    key: 'maintainer-reviewed',
    label: 'Maintainer reviewed',
    cue: 'Reviewed',
    description: 'A code maintainer has publicly reviewed the stated integration or a defined part of it. Review alone does not make it an upstream feature.',
    evidence: 'A linked review, issue, pull request, or statement describing what was examined.',
  },
  {
    key: 'official',
    label: 'Official support',
    cue: 'Upstream',
    description: 'The code project publicly adopts or supports the integration. The record states which versions and workflows that support covers.',
    evidence: 'An upstream release, documentation, merged change, or explicit maintainer announcement.',
  },
] as const;

export const validationStatuses = [
  {
    key: 'prototype',
    label: 'Prototype',
    description: 'A model or adapter exists. Its behavior is still being explored and the claimed examples have not reached a stronger check.',
  },
  {
    key: 'settings-parity',
    label: 'Settings parity',
    description: 'For a stated set of pinned examples, generated active native settings agree with reference inputs under documented comparison rules.',
  },
  {
    key: 'build-tested',
    label: 'Build tested',
    description: 'The pinned source builds with the generated configuration in a documented environment. This does not assess simulation results.',
  },
  {
    key: 'science-validated',
    label: 'Science validated',
    description: 'Representative solver results meet documented scientific comparisons and acceptance criteria for a defined scope.',
  },
] as const;

export const supportLabels: Record<string, string> = Object.fromEntries(
  supportStatuses.map(({ key, label }) => [key, label]),
);
export const validationLabels: Record<string, string> = Object.fromEntries(
  validationStatuses.map(({ key, label }) => [key, label]),
);
