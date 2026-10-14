// Use the same public API resolution as the pinned Hypit launcher for Provider mock tests.
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const cfg = JSON.parse(readFileSync(new URL('../.local/config.json', import.meta.url), 'utf8'));
const requireFromHypit = createRequire(join(cfg.hypitRoot, 'package.json'));
const { register } = await import(pathToFileURL(requireFromHypit.resolve('tsx/esm/api')).href);
register();
const { installDistributionPackageResolution } = await import(pathToFileURL(
  join(cfg.hypitRoot, 'packages/loader/src/node/distribution-resolution.ts')).href);
installDistributionPackageResolution([cfg.hypitRoot]);
