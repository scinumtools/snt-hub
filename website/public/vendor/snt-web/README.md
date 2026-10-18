SNT3 WebAssembly runtime vendored for the Hub's browser override preview.

- SNT3 version: 0.9.6
- Source revision: `7c8e9f7fa74db050cef6f9a5eae4001dd1772f4c` (`v0.9.6`)
- Source: https://github.com/scinumtools/snt3/tree/v0.9.6/bindings/web
- License: MIT; see `LICENSE` in this directory.

`index.mjs` and `dist/` were built from the pinned release source with Emscripten 6.0.12 and copied together.
Update all three runtime files together and run `node --test website/tests/browser-project.test.mjs`.
The runtime loads when a visitor opens an example's override page.
