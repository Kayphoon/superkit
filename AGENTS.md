# Superkit

Kayphoon 的 agent 工具箱。本目录就是 git 仓库根（`Kayphoon/superkit`）：`skills/` 放各个 skill，`bin/` 是安装器 CLI，`tests/` 是安装器测试。

## 目录布局

| 路径 | 是什么 |
|---|---|
| `skills/<name>/` | 一个 skill 的完整目录，`SKILL.md` 是入口，按需带 `references/`、`tests/` |
| `bin/superkit.mjs` | 零依赖安装器 CLI |
| `tests/` | 安装器测试 |
| `install-codex.sh` | 指向 `codex-flash-agents` 的迁移桥 |
| `evaluations/` | 按日期归档的评测实验（只在本机，已 gitignore） |
| `backups/` | 大改前的 tar.gz 快照（只在本机，已 gitignore） |
| `codex-flash-agents/` | 独立仓库 `Kayphoon/codex-flash-agents`，有自己的 `.git`，不并入本仓库 |

## 每个 skill 只有一份

`skills/<name>/` 是唯一副本，GitHub 上的同名独立仓库已归档，只保留重定向。不要再复制一份到别处。历史方面，`superwiki` 和 `superspec` 是通过 `git subtree` 并入的，各自的提交记录都在本仓库历史里。

## 改动是实时生效的

各运行时的 skill 目录软链接到 `skills/<name>`：`~/.agents/skills`、`~/.codex/skills`、`~/.config/opencode/skills`、`~/.cursor/skills`、`~/.omo/agent/skills`、`~/.config/alma/skills`，另有 `~/oc/superwiki`。所以在这里编辑 `SKILL.md`，下次新会话就会读到。

移动或重命名 skill 目录前，先用 `find ~ -maxdepth 6 -type l -lname '*xkfnb/superkit*' -not -path '*/Library/*'` 列出所有指向它的链接，移动后用 `ln -sfn` 逐个改指，再逐个确认链接可达。

## 编写 skill

新建或修改 `SKILL.md`、`references/` 里的 agent 文本前，先加载 `writing-for-agents` skill。新 skill 放在 `skills/<name>/`，然后在 README 的 skill 表里补一行。

全局入口和项目入口分开是刻意设计：一个 skill 如果只该由人手动调用，就在 frontmatter 写 `disable-model-invocation: true`，Codex 另在 `agents/openai.yaml` 写 `policy: allow_implicit_invocation: false`；需要 agent 自动触发的，就用不带前缀的名字做成独立 skill（参考 `superwiki` 与它生成的项目级 `superwiki-auto`），不要用同名覆盖。

`explorer`、`librarian`，以及 `codex-flash-agents` 里的角色正文，改编自 MIT 许可的 oh-my-openagent。`NOTICE.md` 和 `LICENSE.txt` 要始终跟着目录走；修改行为文本时，在 `NOTICE.md` 的改编说明里补上这次改了什么。

## 验证

- 安装器与新包名：`npm test`
- `skills/superwiki/`：`python3 -m pytest tests`
- `skills/explorer/`、`skills/librarian/`：`python3 tests/test_self_contained.py`
- `codex-flash-agents/`：`cd codex-flash-agents && npm test`

改了哪个目录，就跑哪个目录的测试。

## 评测与备份

- 新的评测实验放在 `evaluations/YYYY-MM-DD-<主题>/`，沿用 `protocol.md`（方案）、`status.md`（当前状态）、`report.md`（结论）三件套。旧报告里的 `xkfnb/skills` 路径是改名前的历史记录，保持原样。`evaluations/` 不公开。
- 批量删除或重构 skill 之前，先在 `backups/` 打快照：`<内容>-YYYYMMDD.tar.gz`。
