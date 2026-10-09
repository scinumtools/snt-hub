![{?SNT.HUB} logo](docs/snt-hub-logo.svg)

# SNT Hub

A central registry of scientific codes and reusable DIPL layers for generating native simulation inputs.

## The initiative

SNT Hub is the landing place for the [SNT initiative](https://scinumtools.github.io/snt3/initiative.html): one optional parameter layer for many established scientific codes. A DIPL model describes values, units, constraints, and dependencies. SNT3 evaluates it, and a code-specific adapter generates the input files the original solver already understands. Each project record separates maintainer support from evidence about generated settings, builds, and scientific results.

| Explore | What it covers |
| --- | --- |
| [SNT3 source](https://github.com/scinumtools/snt3) | Toolkit implementation and examples |
| [SNT3 documentation](https://scinumtools.github.io/snt3/) | Guides and APIs |
| [Initiative overview](https://scinumtools.github.io/snt3/initiative.html) | Goals and collaboration path |
| [DIPL specification](https://scinumtools.github.io/snt3/dipl/index.html) | Language syntax and semantics |
| [Adapter guide](https://scinumtools.github.io/snt3/modules/dip/adapters.html) | Generating native files from evaluated models |

## Website

The static landing site is built with Astro from [website/](website/). Its project cards are rendered at build time from each project's `project.json`, beginning with [Arepo](projects/arepo/project.json).

```sh
cd website
npm ci
npm run dev
```

`npm run build` writes the GitHub Pages artifact to `website/dist/`. The Pages workflow builds on changes to the website or project records. In repository Settings → Pages, select **GitHub Actions** as the publishing source. Astro is configured for `https://scinumtools.github.io/snt-hub/`.

## Project integrations

Each integration has a pinned original-code submodule, a sibling DIPL implementation, and a registry record in its own directory. Start with [projects/arepo/](projects/arepo/). After cloning, run `git submodule update --init --recursive` before testing an adapter.

The [proposal](PROPOSAL/PROPOSAL.md) describes the registry statuses and intended source/adapter layout.
