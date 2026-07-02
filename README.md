# SuperWiki

项目知识库管理器。以 skill 形式存储项目知识，每个知识模块用 `wiki-` 前缀命名。

## 快速开始

```bash
# 1. 在项目中创建知识库目录
mkdir -p .wiki/skills

# 2. 创建符号链接（按使用的 agent 选择）
mkdir -p .agents
ln -s ../.wiki/skills .agents/skills

mkdir -p .opencode
ln -s ../.wiki/skills .opencode/skills

mkdir -p .claude
ln -s ../.wiki/skills .claude/skills
```

也可以直接运行：

```bash
superwiki-init /path/to/project
```

如果要同时启用 Codex 自动 memory hook：

```bash
superwiki-init --hook /path/to/project
```

如果 agent 已经能加载全局 `superwiki` skill，但所在项目没有接入项目级 skill 目录，应先初始化这个项目的 `.wiki/skills` 和对应运行时入口。Codex/agent-compatible 使用 `.agents/skills -> ../.wiki/skills`，OpenCode 使用 `.opencode/skills -> ../.wiki/skills`，Claude Code 使用 `.claude/skills -> ../.wiki/skills`。已有冲突路径时不要覆盖，先让用户确认。

## 配置

### OpenCode

OpenCode 会发现项目内 `.opencode/skills`、`.claude/skills`、`.agents/skills`，也会发现全局的 `~/.config/opencode/skills`、`~/.claude/skills`、`~/.agents/skills`。项目内推荐使用 `.opencode/skills -> ../.wiki/skills`。

### Codex

Codex/agent-compatible 项目内推荐使用 `.agents/skills -> ../.wiki/skills`。

### Claude Code

Claude Code 项目内推荐使用 `.claude/skills -> ../.wiki/skills`。

## 使用

### 加载 SuperWiki

```
skill(name="superwiki")
```

### 委派任务时带上

```python
task(category="deep", load_skills=["superwiki"], prompt="...")
```

## memory-librarian 子代理

当项目知识库规模变大时，主线程内联读 wiki 会污染上下文。superwiki 附带一个 `memory-librarian` 自定义代理（`agents/memory-librarian.toml`），做只读检索后返回压缩摘要。

它的工作方式：

- 主线程把任务目标交给 memory-librarian
- memory-librarian 遍历 `.wiki/skills/` 和 `~/.codex/memories/`，匹配相关条目
- 只返回一个 < 1200 字的 memory packet（摘要 + 置信度 + 引用路径 + stale 标记）
- 主线程基于 packet 执行任务，不直接读 wiki 源文件

安装脚本 `skills.sh` 会自动把 `memory-librarian.toml` 链接到 `~/.codex/agents/`。使用时在主线程里写：

```
Act as memory-librarian. Task: <任务>. Project root: <path>.
Return a memory packet under 1200 words. Do not solve the task.
```

## 自动 memory hook

`hooks/superwiki-memory-hook.py` 是一个 Codex `UserPromptSubmit` command hook。它在用户提交消息后、主线程正式回答前运行，读取当前项目的 `.wiki/skills/wiki-*/SKILL.md`，结合用户 prompt 和最近 transcript 做轻量匹配，然后通过 `additionalContext` 注入一个小型 `<superwiki-memory-packet>`。

这个 hook 不会直接启动 `memory-librarian` 子代理。Codex 当前 hook 只稳定支持 `type: "command"`；在 hook 里嵌套启动 Codex/agent 容易递归、变慢、增加不确定性。因此自动 hook 只负责快速召回，复杂任务仍由主线程按需派 `memory-librarian` 深检索。

项目级安装方式：

```bash
superwiki-init --hook /path/to/project
```

这会创建：

```text
.codex/hooks/superwiki-memory-hook.py -> <superwiki>/hooks/superwiki-memory-hook.py
.codex/hooks.json
```

新增或变更 hook 后，需要在 Codex 里用 `/hooks` 审核并信任。已有 `.codex/hooks.json` 时，初始化脚本不会覆盖，会提示你手动合并 `hooks/hooks.json`。

如果希望对所有已接入 `.wiki/skills` 的项目全局启用，先运行 `skills.sh` 安装全局 hook 脚本，再把 `hooks/hooks.global.json` 合并到 `~/.codex/hooks.json`。hook 在没有 `.wiki/skills` 的项目中会安静退出。

常用环境变量：

```bash
SUPERWIKI_HOOK_DISABLE=1          # 临时关闭注入
SUPERWIKI_HOOK_MAX_ENTRIES=4      # 最多注入几个 wiki
SUPERWIKI_HOOK_MAX_CHARS=6000     # memory packet 字符上限
```

## 知识结构

```
.wiki/skills/
├── wiki-domain-status/SKILL.md     # 域名状态映射
├── wiki-csv-encoding/SKILL.md      # CSV 编码处理
├── wiki-rule-u08/SKILL.md          # 规则 U08
└── wiki-fix-xxx-20260611/SKILL.md  # 修复记录
```

历史遗留的 `wiki_` 前缀目录可以继续读取和维护，新建知识模块统一使用 `wiki-`，这样 OpenCode、Claude Code 和 Codex/agent-compatible 入口都能复用。

## 命名

| 类型 | 格式 | 示例 |
|------|------|------|
| 技术点 | `wiki-<技术点>` | `wiki-csv-encoding` |
| 模块 | `wiki-<模块名>` | `wiki-domain-status` |
| 规则 | `wiki-rule-<名>` | `wiki-rule-u08` |
| 修复 | `wiki-fix-<简述>-<日期>` | `wiki-fix-status-20260611` |
| 决策 | `wiki-decision-<简述>` | `wiki-decision-use-python` |
