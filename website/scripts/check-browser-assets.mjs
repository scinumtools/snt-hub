import { existsSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../public/vendor/snt-web/', import.meta.url));
for (const name of ['index.mjs', 'dist/dipl_web.mjs', 'dist/dipl_web.wasm']) {
  const path = root + name;
  if (!existsSync(path) || statSync(path).size === 0) {
    throw new Error(`Missing SNT browser runtime asset: public/vendor/snt-web/${name}`);
  }
}
