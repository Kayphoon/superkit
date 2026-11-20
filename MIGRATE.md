# SuperWiki 旧版迁移指南（Agent 执行手册）

本文件是自包含的单体迁移指南，供 coding agent 直接读取并执行。

**背景**：新版 `superwiki` 已拆分为两部分——项目日常使用随仓库共享的 `superwiki-auto`，全局 `superwiki` 改为纯手动触发（`disable-model-invocation: true`）。如果本机仍残留旧版全局 `superwiki`（无 `VERSION`、会自动触发去读 `.wiki/skills`），它会与项目里的 `superwiki-auto` 同时触发并给出矛盾结果。

**执行原则**：先只读扫描，列出清单并取得用户明确确认后，再执行清理或安装。未确认前不删除任何文件、不执行安装。

---

## 1. 只读扫描

在当前工作目录运行下面这段只读 Node.js 脚本（零依赖，兼容 macOS / Linux / Windows；Bash/Zsh 可用 `node --input-type=module <<'EOF' ... EOF`，Windows PowerShell 可用 `@' ... '@ | node --input-type=module`）：

```js
import { lstatSync, readFileSync, readlinkSync, statSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join, resolve } from 'node:path';

const repoRoot = process.cwd();
const home = homedir();
const codexHome = process.env.CODEX_HOME ? resolve(process.env.CODEX_HOME) : join(home, '.codex');

const readFm = (t) => /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/.exec(t)?.[1] ?? null;

function inspectDir(dir) {
  let version = null;
  try { version = readFileSync(join(dir, 'VERSION'), 'utf8').trim() || null; } catch {}
  let skill = null;
  try { skill = readFileSync(join(dir, 'SKILL.md'), 'utf8'); } catch {}
  let hasLegacyInit = false;
  try { statSync(join(dir, 'references', 'initialization.md')); hasLegacyInit = true; } catch {}

  const fm = skill ? readFm(skill) : null;
  const manualOnly = Boolean(fm && /^disable-model-invocation:\s*true\s*$/m.test(fm));
  const looksLikeSuperwiki = Boolean(
    hasLegacyInit ||
      (fm && /^name:\s*['"]?superwiki['"]?\s*$/m.test(fm)) ||
      (skill && (skill.includes('SuperWiki') || skill.includes('.wiki/skills')))
  );

  if (version && manualOnly) return { status: 'new', version, hasLegacyInit };
  if (looksLikeSuperwiki || (version && !manualOnly)) return { status: 'old', version, hasLegacyInit };
  return { status: 'unknown', version, hasLegacyInit };
}

function inspectEntry(label, scope, p) {
  let lst;
  try { lst = lstatSync(p); } catch (e) {
    return e?.code === 'ENOENT' ? null : { label, scope, path: p, kind: 'error', status: 'unknown' };
  }
  if (lst.isSymbolicLink()) {
    const linkTarget = readlinkSync(p);
    try {
      const st = statSync(p);
      if (!st.isDirectory()) return { label, scope, path: p, kind: 'symlink', linkTarget, status: 'unknown' };
      return { label, scope, path: p, kind: 'symlink', linkTarget, ...inspectDir(p) };
    } catch {
      return { label, scope, path: p, kind: 'symlink', linkTarget, status: 'broken-link' };
    }
  }
  if (lst.isDirectory()) return { label, scope, path: p, kind: 'directory', ...inspectDir(p) };
  return { label, scope, path: p, kind: 'file', status: 'unknown' };
}

const candidates = [
  ['agents', 'global', join(home, '.agents', 'skills', 'superwiki')],
  ['codex', 'global', join(codexHome, 'skills', 'superwiki')],
  ['claude', 'global', join(home, '.claude', 'skills', 'superwiki')],
  ['opencode', 'global', join(home, '.config', 'opencode', 'skills', 'superwiki')],
  ['cursor', 'global', join(home, '.cursor', 'skills', 'superwiki')],
  ['omo', 'global', join(home, '.omo', 'agent', 'skills', 'superwiki')],
  ['alma', 'global', join(home, '.config', 'alma', 'skills', 'superwiki')],
  ['project:.agents', 'project', join(repoRoot, '.agents', 'skills', 'superwiki')],
  ['project:.claude', 'project', join(repoRoot, '.claude', 'skills', 'superwiki')],
  ['project:.opencode', 'project', join(repoRoot, '.opencode', 'skills', 'superwiki')],
  ['project:.cursor', 'project', join(repoRoot, '.cursor', 'skills', 'superwiki')],
  ['project:.codex', 'project', join(repoRoot, '.codex', 'skills', 'superwiki')],
];

const seen = new Set();
const findings = [];
for (const [label, scope, p] of candidates) {
  const key = process.platform === 'win32' ? p.toLowerCase() : p;
  if (seen.has(key)) continue;
  seen.add(key);
  const r = inspectEntry(label, scope, p);
  if (r) findings.push(r);
}

console.log(`CWD: ${repoRoot}`);
for (const autoRel of ['.agents/skills/superwiki-auto/SKILL.md', '.wiki/skills/superwiki-auto/SKILL.md']) {
  try {
    const fm = readFm(readFileSync(join(repoRoot, autoRel), 'utf8')) || '';
    const mode = /^\s*superwiki-mode:\s*['"]?([^'"\r\n]+)['"]?\s*$/m.exec(fm)?.[1] || 'unknown';
    const tmpl = /^\s*superwiki-template:\s*['"]?([^'"\r\n]+)['"]?\s*$/m.exec(fm)?.[1] || 'unknown';
    console.log(`Project superwiki-auto: OK (${autoRel}, mode=${mode}, template=${tmpl})`);
  } catch {}
}
console.log('');
if (!findings.length) {
  console.log('未发现任何全局或项目残留的 superwiki 入口。');
} else {
  for (const f of findings) {
    const ver = f.version ? ` version=${f.version}` : '';
    const link = f.kind === 'symlink' ? ` -> ${f.linkTarget}` : '';
    const initTag = f.hasLegacyInit ? ' [has references/initialization.md]' : '';
    console.log(`[${f.status}] (${f.scope}/${f.label}, ${f.kind}) ${f.path}${link}${ver}${initTag}`);
  }
}
```

### 判定说明

- `new`：含 `VERSION` 且 frontmatter 含 `disable-model-invocation: true`（新版，仅手动触发，不会冲突）。
- `old`：旧版 `superwiki`，需要升级或清理。
- `broken-link`：失效软链接，需要清理。
- `unknown`：无法识别的同名内容，不要擅自删除，单独列出交由用户决定。

若没有任何 `old`、`broken-link` 或 `unknown` 条目，直接告知用户"当前环境已干净，无需操作"，结束流程。

---

## 2. 汇报清单并请求确认

把扫描到的每一项整理成表格展示给用户（路径、范围、类型与链接目标、状态），再请用户二选一：

- **方案 A（推荐）：清理旧版并升级到全局新版 `superwiki`**
  - 适合会在其他项目接入或升级知识库的同事。新版仅支持手动触发，不会干扰项目的 `superwiki-auto`。
- **方案 B：仅清理旧版，不装全局版**
  - 适合只在已接入 `superwiki-auto` 的项目里工作的同事；项目已自包含，无需全局安装。

若存在指向本地源码仓库的软链接（例如开发者的 `superkit` 目录），明确标注为开发链接，不删除其源目录。

---

## 3. 按确认方案执行

### 清理旧版与断链

仅移除用户确认的 `old` 和 `broken-link` 条目：

- **软链接**：只删除链接本身，绝不删除其目标目录。
  - 选方案 A 时，若某运行时目录的软链接本身指向 `~/.agents/skills/superwiki`，保留该软链接，等升级完成后复核即可；选方案 B 时连同软链接一起删除。
- **实体目录**：只删除对应的 `superwiki` 目录本身（包括项目工作区内残留的未跟踪 `.agents/skills/superwiki` 等旧副本）。
- **未知条目**：除非用户明确指定删除，否则保留不动。

### 安装全局新版（仅方案 A）

默认安装到 `~/.agents/skills`：

```bash
npx --yes github:Kayphoon/superkit install superwiki --force
```

如果用户使用的工具依赖专属目录（例如原旧版作为实体目录装在 `~/.claude/skills`、`~/.codex/skills`、`~/.config/opencode/skills` 或 `~/.cursor/skills`，且没有软链接指向 `~/.agents/skills`），按需追加 `--target`（可重复指定）：

```bash
npx --yes github:Kayphoon/superkit install superwiki --force --target agents --target claude
```

若 `npx` 因网络、代理或权限失败，保留已完成的旧版清理（不影响项目正常使用 `superwiki-auto`），将完整报错和上述重试命令交给用户稍后执行。

---

## 4. 复核与收尾

重新运行第 1 节的只读扫描脚本，确认：

1. 不再有任何 `old` 或 `broken-link` 条目；
2. 选方案 A 时，已安装条目状态为 `new`，并报告其 `version`（当前预期 `2026.11.20`）；
3. 若当前位于已接入 `superwiki-auto` 的项目，确认 `superwiki-auto` 保持正常。

最后提醒用户：**重新开启一次新会话**，让运行时重新发现最新的 skill 列表。

---

## 边界

- 只处理 `superwiki` 的检测、清理与安装；不暂存、不提交、不推送、不切换分支。
- 不修改任何 `wiki-*` 知识模块、`superwiki-auto` 或项目业务代码。
