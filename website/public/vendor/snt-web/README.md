SNT3 WebAssembly runtime vendored for the Hub's browser override preview.

- SNT3 version: 0.9.3
- Source revision: `592869c39d8dd015b14e71552184cb4b5dfee5ed`
- Source: https://github.com/scinumtools/snt3/tree/main/bindings/web
- License: MIT; see `LICENSE` in this directory.

`index.mjs` and `dist/` were copied from the adjacent SNT3 WebAssembly build.
Update all three runtime files together and run `node --test website/tests/browser-project.test.mjs`.
The runtime loads when a visitor opens an example's override page.
