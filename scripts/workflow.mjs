#!/usr/bin/env node
import { existsSync, readFileSync, realpathSync } from 'node:fs';
import { cp, lstat, mkdir, mkdtemp, readFile, readdir, rm, symlink, writeFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { homedir, tmpdir } from 'node:os';
import { dirname, isAbsolute, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const localFile = join(repo, '.local/config.json');
const provider = join(repo, 'packages/provider-haiyi');
const upstream = JSON.parse(readFileSync(join(repo, 'upstream.json'), 'utf8'));
const skillHome = resolve(process.env.CODEX_HOME || join(homedir(), '.codex'), 'skills');
const [command = 'help', ...input] = process.argv.slice(2);

function exec(binary, args, options = {}) {
  const result = spawnSync(binary, args, { stdio: 'inherit', ...options });
  if (result.error) throw new Error(`Cannot run ${binary}: ${result.error.message}`);
  if (result.status !== 0) throw new Error(`${binary} exited with status ${result.status ?? result.signal}`);
  return result;
}

function flag(args, name) {
  const index = args.indexOf(name);
  if (index === -1) return undefined;
  if (!args[index + 1] || args[index + 1].startsWith('--')) throw new Error(`${name} needs a value`);
  return args[index + 1];
}

function parseSetup(args) {
  const allowed = new Set(['--hypit-root', '--ffmpeg', '--ffprobe', '--base-url', '--install']);
  for (let index = 0; index < args.length; index++) {
    if (!allowed.has(args[index])) throw new Error(`Unknown setup option: ${args[index]}`);
    if (args[index] !== '--install') { flag(args.slice(index), args[index]); index++; }
  }
}

async function json(path) { return JSON.parse(await readFile(path, 'utf8')); }
async function saveJson(path, data) {
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, JSON.stringify(data, null, 2) + '\n');
}
async function config() {
  if (!existsSync(localFile)) throw new Error('Run setup first. See README.md.');
  return json(localFile);
}

function executable(name, selected) {
  if (selected) {
    const path = resolve(selected);
    if (!existsSync(path)) throw new Error(`${name} not found: ${path}`);
    return path;
  }
  const windows = process.platform === 'win32';
  const result = spawnSync(windows ? 'where.exe' : 'which', [name], { encoding: 'utf8' });
  const first = result.stdout?.trim().split(/\r?\n/)[0];
  if (result.status !== 0 || !first) throw new Error(`Install ${name} or pass --${name} /absolute/path.`);
  return first;
}

async function attachDependencies(hypitRoot) {
  const target = join(hypitRoot, 'node_modules');
  if (!existsSync(join(target, 'typescript/bin/tsc'))) throw new Error('Hypit dependencies missing; install with pnpm 10.33.0 in its root.');
  const modules = join(provider, 'node_modules');
  await mkdir(modules, { recursive: true });
  async function linkDependency(path, source) {
    let stat;
    try { stat = await lstat(path); } catch (error) { if (error.code !== 'ENOENT') throw error; }
    if (stat) {
      if (realpathSync(path) === realpathSync(source)) return;
      throw new Error(`Dependency ${path} points to another installation; it will not be replaced.`);
    }
    await mkdir(dirname(path), { recursive: true });
    await symlink(source, path, process.platform === 'win32' ? 'junction' : 'dir');
  }
  for (const name of await readdir(target)) {
    if (name.startsWith('.')) continue;
    if (name.startsWith('@')) {
      for (const member of await readdir(join(target, name))) {
        await linkDependency(join(modules, name, member), join(target, name, member));
      }
    } else await linkDependency(join(modules, name), join(target, name));
  }
  // The Hypit root package is a workspace self-reference and is absent from root node_modules.
  await linkDependency(join(modules, '@hypit/hypit'), hypitRoot);
}

async function compile(cfg) {
  await attachDependencies(cfg.hypitRoot);
  exec(process.execPath, [join(cfg.hypitRoot, 'node_modules/typescript/bin/tsc'), '-p', join(provider, 'tsconfig.json')]);
}

function commitAt(root) {
  const result = spawnSync('git', ['-C', root, 'rev-parse', 'HEAD'], { encoding: 'utf8' });
  if (result.status !== 0) throw new Error('Hypit root must be the selected contributor checkout.');
  return result.stdout.trim();
}

async function setup(args) {
  parseSetup(args);
  const [major, minor] = process.versions.node.split('.').map(Number);
  if (major < 22 || (major === 22 && minor < 15)) throw new Error('Node >=22.15 is required.');
  let hypitRoot = flag(args, '--hypit-root');
  if (args.includes('--install') && hypitRoot) throw new Error('Choose --install or --hypit-root, not both.');
  if (args.includes('--install')) {
    hypitRoot = join(repo, '.local/hypit');
    await mkdir(dirname(hypitRoot), { recursive: true });
    if (!existsSync(hypitRoot)) {
      exec('git', ['clone', '--no-checkout', upstream.repository, hypitRoot]);
      exec('git', ['-C', hypitRoot, 'checkout', '--detach', upstream.commit]);
    }
    if (commitAt(hypitRoot) !== upstream.commit) throw new Error('Existing .local/hypit has a different commit; it will not be reset.');
    // Fixed command/arguments only; cwd carries the directory without shell interpolation.
    const version = spawnSync('pnpm', ['--version'], { encoding: 'utf8', shell: process.platform === 'win32' });
    if (version.status !== 0 || version.stdout.trim() !== upstream.packageManager.split('@').at(-1)) {
      throw new Error(`Install ${upstream.packageManager} before setup --install.`);
    }
    exec('pnpm', ['install', '--frozen-lockfile'], { cwd: hypitRoot, shell: process.platform === 'win32' });
  }
  if (!hypitRoot) throw new Error('Pass --hypit-root /path/to/hypit, or --install.');
  hypitRoot = resolve(hypitRoot);
  if (commitAt(hypitRoot) !== upstream.commit) throw new Error(`Use pinned Hypit commit ${upstream.commit}; your checkout will not be changed.`);
  const cli = join(hypitRoot, 'bin/hypit.mjs');
  if (!existsSync(cli)) throw new Error('Hypit launcher not found.');
  const ffmpeg = executable('ffmpeg', flag(args, '--ffmpeg'));
  const ffprobe = executable('ffprobe', flag(args, '--ffprobe'));
  exec(ffmpeg, ['-version'], { stdio: 'ignore' });
  exec(ffprobe, ['-version'], { stdio: 'ignore' });
  const baseUrl = (flag(args, '--base-url') || process.env.HAIYI_BACKEND_URL || 'https://art.huya.info').replace(/\/$/, '');
  const url = new URL(baseUrl);
  if (url.protocol !== 'https:' && !(url.protocol === 'http:' && ['localhost', '127.0.0.1'].includes(url.hostname))) {
    throw new Error('Haiyi endpoint must use HTTPS (loopback HTTP is allowed).');
  }
  const cfg = { format: 'hypit-haiyi.local@1', repositoryRoot: repo, hypitRoot, cli, ffmpeg, ffprobe, baseUrl };
  await compile(cfg);
  await saveJson(localFile, cfg);
  console.log('Hypit + Haiyi configuration ready. No generation tasks submitted.');
}

async function installSkill(args) {
  const directorOnly = args.length === 1 && args[0] === '--director-only';
  if (args.length && !directorOnly) throw new Error('install-skill accepts only --director-only.');
  const cfg = directorOnly ? null : await config();
  for (const name of directorOnly ? ['video-director'] : ['video-director', 'hypit-haiyi']) {
    const destination = join(skillHome, name);
    await mkdir(destination, { recursive: true });
    await cp(join(repo, 'skills', name), destination, { recursive: true, force: true });
    console.log(`Installed bundled skill: ${destination}`);
  }
  if (directorOnly) return;
  const target = join(skillHome, 'hypit-haiyi');
  const hypitSkill = join(skillHome, 'hypit');
  if (!existsSync(join(hypitSkill, 'SKILL.md'))) {
    const original = join(cfg.hypitRoot, 'skills/hypit');
    if (!existsSync(join(original, 'SKILL.md'))) throw new Error('Upstream Hypit skill missing.');
    await cp(original, hypitSkill, { recursive: true, force: false });
  }
  const haiyiSkill = join(skillHome, 'haiyi-aigc');
  await saveJson(join(target, 'references/local-setup.json'), {
    format: 'hypit-haiyi.skill-local@1', repositoryRoot: repo,
    workflowScript: join(repo, 'scripts/workflow.mjs'), configFile: localFile,
    hypitRoot: cfg.hypitRoot, hypitSkill, directorSkill: join(skillHome, 'video-director'),
    haiyiSkill: existsSync(join(haiyiSkill, 'SKILL.md')) ? haiyiSkill : null,
  });
  const routing = '<!-- hypit-haiyi-routing:start -->\n## 本地统一视频入口\n\n当用户要求制作、继续或修改完整视频时，优先读取相邻的 [Hypit + 海艺统一技能](../hypit-haiyi/SKILL.md)，复用其已有 Provider 与配置。单独图片、音乐、语音或媒体工具任务仍按当前技能处理；用户明确选择其他流程时遵循用户选择。配置账号不代表授权付费生成。\n<!-- hypit-haiyi-routing:end -->';
  for (const base of [hypitSkill, haiyiSkill]) {
    const path = join(base, 'SKILL.md');
    if (!existsSync(path)) continue;
    const original = await readFile(path, 'utf8');
    if (original.includes('<!-- hypit-haiyi-routing:start -->')) continue;
    const backup = join(repo, '.local/skill-backups', `${base === hypitSkill ? 'hypit' : 'haiyi-aigc'}-SKILL.md`);
    if (!existsSync(backup)) { await mkdir(dirname(backup), { recursive: true }); await writeFile(backup, original); }
    await writeFile(path, original.replace(/(^# [^\r\n]+\r?\n)/m, `$1\n${routing}\n`));
  }
  console.log('Unified workflow and director module ready.');
}

async function initProject(path, cfg) {
  if (!path) throw new Error('init needs a new project directory.');
  const project = resolve(path);
  if (existsSync(project) && (await readdir(project)).length) throw new Error('Target must be new or empty; existing project files will not be replaced.');
  await mkdir(project, { recursive: true });
  await cp(join(repo, 'templates/project'), project, { recursive: true, force: false });
  await mkdir(join(project, 'packages'), { recursive: true });
  await symlink(provider, join(project, 'packages/provider-haiyi'), process.platform === 'win32' ? 'junction' : 'dir');
  const profilePath = join(project, 'hypit.runtime.json');
  const profile = await json(profilePath);
  for (const name of ['media.local', 'html.local']) {
    profile.endpoints[name].config.ffmpegPath = cfg.ffmpeg;
    profile.endpoints[name].config.ffprobePath = cfg.ffprobe;
  }
  profile.endpoints['haiyi.default'].config.baseUrl = cfg.baseUrl;
  await saveJson(profilePath, profile);
  await writeFile(join(project, '.gitignore'), '.hypit/\nnode_modules/\npackages/provider-haiyi\n.env*\ntokens.json\n');
  await writeFile(join(project, 'BRIEF.md'), '# 制作目标\n\n记录用户目标、时长、画幅、素材范围和已接受的付费范围。当前仅为示例模板，尚未授权付费生成。\n');
  await writeFile(join(project, 'TREATMENT.md'), '# 创作方案\n\n使用 video-director 明确创作主张、故事/论证、表演、画面与声音，再设计分镜和素材依赖。正式采用的台词只保存在 Author Source 的 <script> 中。\n');
  await writeFile(join(project, 'PROGRESS.md'), '# 当前进展\n\n项目已建立，尚未提交生成任务。\n\n下一步：完成 Brief 和分镜，修改 Source，运行 check 和 plan。\n');
  console.log(`Project ready: ${project}`);
  return project;
}

async function childEnvironment(baseUrl) {
  const env = { ...process.env };
  if (env.HAIYI_API_TOKEN) return env;
  const configHome = process.platform === 'win32'
    ? (env.APPDATA || join(homedir(), 'AppData/Roaming'))
    : (env.XDG_CONFIG_HOME || join(homedir(), '.config'));
  const tokenFile = env.HAIYI_TOKEN_FILE || join(configHome, 'haiyi-skills/tokens.json');
  if (existsSync(tokenFile)) {
    try {
      const store = await json(tokenFile);
      const token = store[baseUrl];
      if (typeof token === 'string' && token.trim()) env.HAIYI_API_TOKEN = token;
    } catch { throw new Error('Haiyi credential store is unreadable; use Haiyi login or HAIYI_API_TOKEN.'); }
  }
  return env;
}

async function invoke(cfg, action, args) {
  const project = resolve(flag(args, '--project') || process.cwd());
  if (!existsSync(join(project, 'package.json'))) throw new Error('Select a video project using --project.');
  const manifest = await json(join(project, 'package.json'));
  if (!manifest.hypit?.project) throw new Error('Selected directory is not a Hypit video project.');
  const augmented = [...args];
  if (!args.includes('--project')) augmented.push('--project', project);
  if (['check', 'plan', 'pricing', 'build'].includes(action) && !args.includes('--package-root')) {
    augmented.push('--package-root', repo);
  }
  let profileFile;
  if (['plan', 'pricing', 'build', 'doctor'].includes(action)) {
    profileFile = resolve(flag(args, '--runtime') || join(project, 'hypit.runtime.json'));
    if (!args.includes('--runtime')) augmented.push('--runtime', profileFile);
  }
  const baseUrl = profileFile ? (await json(profileFile)).endpoints?.['haiyi.default']?.config?.baseUrl || cfg.baseUrl : cfg.baseUrl;
  const env = await childEnvironment(baseUrl);
  if (['build', 'pricing'].includes(action) && !env.HAIYI_API_TOKEN) {
    throw new Error('Haiyi is not authenticated. Use explicit Haiyi login or set HAIYI_API_TOKEN.');
  }
  exec(process.execPath, [cfg.cli, action, ...augmented], { env });
}

async function verify(cfg) {
  await compile(cfg);
  exec(process.execPath, ['--import', pathToFileURL(join(repo, 'scripts/test-bootstrap.mjs')).href,
    '--test', join(provider, 'test/provider.test.ts')]);
  const temp = await mkdtemp(join(tmpdir(), 'hypit-haiyi-verify-'));
  try {
    const project = await initProject(temp, cfg);
    // Plan checks credential presence without validating it or submitting tasks.
    // An inert placeholder keeps validation independent of the user's stored account.
    const env = { ...process.env, HAIYI_API_TOKEN: 'offline-validation-placeholder' };
    for (const stem of ['haiyi-image', 'haiyi-text-video']) {
      exec(process.execPath, [cfg.cli, 'check', join(project, `${stem}.svml`), '--project', project, '--package-root', repo], { env });
      exec(process.execPath, [cfg.cli, 'plan', join(project, `${stem}.svrun`), '--project', project, '--package-root', repo,
        '--runtime', join(project, 'hypit.runtime.json')], { env });
    }
    console.log('Provider mock tests, both Source checks and both plans passed. No live generation performed.');
  } finally {
    // temp was allocated by this process; rm removes the project junction, not its target.
    await rm(temp, { recursive: true, force: true });
  }
}

async function info() {
  const cfg = await config();
  const env = await childEnvironment(cfg.baseUrl);
  console.log(JSON.stringify({ repositoryRoot: repo, hypitRoot: cfg.hypitRoot, hypitCommit: commitAt(cfg.hypitRoot),
    providerCompiled: existsSync(join(provider, 'dist/activation.js')),
    ffmpegPresent: existsSync(cfg.ffmpeg), ffprobePresent: existsSync(cfg.ffprobe),
    unifiedSkillInstalled: existsSync(join(skillHome, 'hypit-haiyi/SKILL.md')),
    directorSkillInstalled: existsSync(join(skillHome, 'video-director/SKILL.md')),
    credentialAvailable: Boolean(env.HAIYI_API_TOKEN), credentialValidity: 'not checked',
    liveGenerationVerified: false }, null, 2));
}

try {
  if (command === 'setup') await setup(input);
  else if (command === 'install-skill') await installSkill(input);
  else if (command === 'init') {
    if (input.length !== 1) throw new Error('init needs exactly one new project directory.');
    await initProject(input[0], await config());
  }
  else if (command === 'verify') { if (input.length) throw new Error('verify takes no arguments.'); await verify(await config()); }
  else if (command === 'info') await info();
  else if (['check', 'plan', 'pricing', 'build', 'doctor'].includes(command)) await invoke(await config(), command, input);
  else if (command === 'hypit') {
    const cfg = await config();
    // Passthrough retains native CLI semantics. Inspect the selected profile for its account.
    let profileFile = flag(input, '--runtime');
    if (!profileFile && input[0] === 'runtime' && input[2] && !input[2].startsWith('--')) profileFile = input[2];
    const project = flag(input, '--project');
    if (!profileFile && project && existsSync(join(resolve(project), 'hypit.runtime.json'))) profileFile = join(resolve(project), 'hypit.runtime.json');
    const baseUrl = profileFile ? (await json(resolve(profileFile))).endpoints?.['haiyi.default']?.config?.baseUrl || cfg.baseUrl : cfg.baseUrl;
    exec(process.execPath, [cfg.cli, ...input], { env: await childEnvironment(baseUrl) });
  }
  else if (command === 'help' || command === '--help') {
    console.log('Hypit + Haiyi workflow\n\nsetup --hypit-root <dir> | --install [--ffmpeg <path> --ffprobe <path> --base-url <url>]\ninstall-skill [--director-only]\ninfo\ninit <new-project-dir>\nverify\ncheck <source> --project <dir>\nplan|pricing|build <run> --project <dir> [--follow]\ndoctor --project <dir>\nhypit <native Hypit arguments>\n\nOnly build submits generation tasks. Read README.md before paid execution.');
  }
  else throw new Error(`Unknown workflow command: ${command}`);
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
