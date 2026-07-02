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
