# Superkit

Kayphoon 的 agent 工具箱：一份仓库，多个可安装的 skill，外加一个零依赖安装器。每个 skill 都是遵循 [Agent Skills 规范](https://agentskills.io) 的自包含目录（`SKILL.md` + 支持文件），各运行时的 skill 目录直接软链接到 `skills/<name>`。

## 包含的 skill

| skill | 用途 |
|---|---|
| `superwiki` | 项目知识库：手动调用接入项目（团队模式提交进 Git，个人模式只在本机），项目里生成自动触发的 `superwiki-auto` 负责日常检索与维护 `wiki-*`。附带 `superwiki-init` 与 `skills.sh`。 |
| `superspec` | 自上而下业务解构与单文件 HTML 规格师：推导端到端单向生命周期与阻断/降级边界，输出人类优先、AI 无歧义的三栏现代技术规格书。 |
| `explorer` | 本地代码库只读探查：把「在不熟悉的仓库里找代码」委派给原生子代理，返回带路径的结论。 |
| `librarian` | 外部资料只读研究员：查外部库、OSS、厂商 API 的官方文档与源码，回到钉到 commit 与代码行的证据。 |

`explorer` 与 `librarian` 是上游 MIT 许可内容的改编版，上游署名与许可全文随目录一起分发：见各自目录下的 `NOTICE.md` 与 `LICENSE.txt`。

## 安装

任何支持 skills 协议的 agent，一条命令装到项目里；`--skill` 可以只挑一个：

```bash
npx skills add Kayphoon/superkit
npx skills add Kayphoon/superkit --skill superwiki -a codex
```

本仓库自带零依赖安装器，直接装到用户级目录。npm 上的包发布前，用 GitHub 协议：

```bash
# 全部 skill
npx github:Kayphoon/superkit install

# 只装指定的
npx github:Kayphoon/superkit install superwiki explorer

# 装到 Codex 的 skills 目录
npx github:Kayphoon/superkit install --target codex

# 装到某个项目而不是用户目录
npx github:Kayphoon/superkit install --project ./my-repo
```

等 `@kayphoon/superkit` 发布到 npm 之后，同样的命令可以缩短成：

```bash
npx @kayphoon/superkit install
npx @kayphoon/superkit install superwiki explorer
npx @kayphoon/superkit install --target codex
npx @kayphoon/superkit install --project ./my-repo
```

其他命令：

```bash
npx @kayphoon/superkit list          # 列出可用 skill 和安装状态
npx @kayphoon/superkit info superwiki
npx @kayphoon/superkit remove explorer
```

安装完成后新开一次会话，让运行时重新发现 skill。

## 安装位置

默认写入用户级的 agent-compatible 目录 `~/.agents/skills`。`--target` 可选 `agents`（默认）、`codex`、`claude`、`opencode`、`cursor`，可重复指定；加 `--project <dir>` 时改为写进项目的对应目录。

安装器默认复制文件，所以升级包之后不会影响已安装的副本；要覆盖已有同名目录显式加 `--force`，要建立符号链接（开发场景）加 `--link`，只想看会发生什么就加 `--dry-run`。

## 使用 superwiki

全局的 `superwiki` 只能手动调用。在项目里调用一次，它会问你选哪种模式，然后生成项目级的 `superwiki-auto`：

```bash
superwiki-init --team /path/to/project       # 知识写在 .agents/skills/，提交进 Git 与团队共享
superwiki-init --personal /path/to/project   # 知识写在 .wiki/skills/，只在本机
```

之后 `superwiki-auto` 会被自动触发，负责查和存 `wiki-*` 知识模块。重复运行同一命令即升级：模板生成的文件按模板重写，模板已删除的文件一并移除，项目专属约定 `superwiki-auto/references/local.md` 和全部 `wiki-*` 保留。

写入前脚本会检查所有要用到的路径：入口被占用、团队与个人模式互转、旧的项目版 `superwiki/` 还在，都会以 `❌` 退出，一个文件也不写。

如果本机之前装过旧版全局 `superwiki`，直接让 agent 按单体迁移手册 [MIGRATE.md](MIGRATE.md) 检查并升级到手动触发的新版。

## Codex 原生 agents

原生 Codex Flash agents（`flash_explorer` / `flash_librarian`）和它们的安装器是另一件事，在独立仓库 [Kayphoon/codex-flash-agents](https://github.com/Kayphoon/codex-flash-agents) 维护：

```bash
curl -fsSL https://raw.githubusercontent.com/Kayphoon/codex-flash-agents/main/install.sh | sh
```

本仓库的 `install-codex.sh` 和 `superkit codex install` 只是兼容桥，提示迁移后转交独立仓库安装器，安装参数和失败退出码保留。兼容桥每次使用独立的临时 npm 缓存，结束后清理。

## 仓库结构

```text
skills/<name>/        每个 skill 的自包含目录
bin/                  安装器 CLI
tests/                安装器测试
install-codex.sh      Codex agents 迁移桥
MIGRATE.md            旧版 superwiki 单体迁移手册（可直接交给 agent 执行）
AGENTS.md             在本仓库工作时的约定
```

本机工作目录（`evaluations/`、`backups/`）和独立的 `codex-flash-agents/` 不进本仓库。

## 许可证

本仓库的安装器与文档以 MIT 许可发布，见 [LICENSE](LICENSE)。`explorer`、`librarian` 内容改编自 [oh-my-openagent](https://github.com/code-yeongyu/oh-my-openagent)，其 MIT 许可与第三方声明随各自 skill 目录保留。
