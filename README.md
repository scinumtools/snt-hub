# snt-hub
A central registry of scientific codes, developers, and reusable DIPL layers for generating native simulation input files and initial conditions.

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
