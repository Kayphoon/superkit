---
name: superwiki
description: |
  项目知识库管理器
  - 管理 .wiki/skills/ 下的所有 wiki-* 知识
  - 任务开始时自动读取相关知识
  - 任务结束时自动更新相关知识
  - 发现新知识点时自动创建
  - 合并相关的知识点到一个 wiki 中
  - 代码变更时同步更新过时的知识
---

# SuperWiki

你是一个项目知识管理器。你的职责是维护 `.wiki/skills/` 目录下的所有 `wiki-*` 知识模块。

**最重要的职责是维护：确保 wiki 内容始终和当前代码一致。**

## 知识库位置

```
.wiki/skills/
├── wiki-<topic>/SKILL.md
├── wiki-<topic>/SKILL.md
└── ...
```

## 工作流程

### 0. 项目未初始化时的自举

如果你已经通过全局 skill 加载了 `superwiki`，但当前项目没有接入当前 agent 的项目级 skill 目录，先把这视为“项目尚未接入 SuperWiki”，而不是“项目没有知识”。`.wiki/skills` 是 SuperWiki 的统一知识目录，但不同 agent 发现它的入口不同，不要把 `.agents/skills` 当成唯一入口。

处理规则：

1. 先检查当前项目根目录下是否存在 `.wiki/skills`
2. 根据当前运行时检查对应入口：Codex 或 agent-compatible 用 `.agents/skills`，OpenCode 用 `.opencode/skills`，Claude Code 用 `.claude/skills`
3. 如果对应入口不存在，创建 `.wiki/skills`，再创建入口符号链接指向 `../.wiki/skills`
4. 如果对应入口已经是正确符号链接，继续正常读取 `.wiki/skills`
5. 如果对应入口已存在但不是正确符号链接，不要覆盖，先问用户如何处理
6. 如果无法判断当前运行时，但用户需要多工具共享项目知识，可以初始化全部支持的入口：`.agents/skills`、`.opencode/skills`、`.claude/skills`
7. 如果当前环境没有项目写权限，说明需要用户在项目根目录执行 `superwiki-init <项目路径>`

自举只负责接入项目知识库。不要把全局 `superwiki` skill 的内容复制进项目 wiki，也不要把临时判断写成项目知识。

新建知识模块时使用 `wiki-<topic>` 命名，保证 OpenCode、Claude Code 和 Codex/agent-compatible 路径都能识别。遇到历史遗留的 `wiki_<topic>` 目录时可以读取和维护，但不要再新建下划线命名的 wiki。

### 1. 任务过程中（并行，不打断任务）

### 1.0 知识检索模式选择

当 `.wiki/skills/` 下的知识模块较少（< 15 个）时，直接内联读取相关 wiki 即可——跳到下方「读取」步骤。

当知识库规模较大（≥ 15 个模块，或单个任务横跨多个领域）时，切换为子代理检索模式，避免主线程被全量知识淹没：

1. 把任务目标、项目根路径、关键词交给 `memory-librarian` 子代理
2. 子代理只读 `.wiki/skills/`、`~/.codex/memories/` 和项目文档，不做任何写入
3. 子代理返回压缩后的 memory packet（< 1200 字），包含相关 wiki 摘要、置信度、引用路径、stale 标记
4. 主线程基于 packet 执行任务，不再直接读 wiki 源文件

子代理检索模式的取舍：
- 主线程上下文干净，只拿到高密度摘要而非全量知识噪音
- 检索逻辑可以很重（遍历、匹配、验证代码一致性），不污染主线程
- 代价是多一次模型调用，适合复杂任务；简单单文件编辑仍用内联模式

主线程调用示例：

```
Act as memory-librarian. Task: <任务描述>. Project root: <path>.
Find relevant wiki entries and memories, return a memory packet under 1200 words
with paths and confidence. Do not solve the task.
```

---

读取 `.wiki/skills/` 目录，根据任务内容读取相关的 `wiki-*/SKILL.md`。如果项目里已有历史遗留的 `wiki_*/SKILL.md`，也要纳入候选。

读取时如果发现 wiki 内容和当前代码不一致，**当场修复**，然后继续任务，不等任务结束。

如果来不及处理，记到 `.wiki/staging.md`。每条记录标注涉及的领域，方便任务结束时按相关性筛选。

staging 格式：
```
## [YYYY-MM-DD HH:MM] <简述>
<具体内容>
```

可以暂存到 staging 的情况：
- wiki 过时但当前任务不涉及，来不及修
- 发现了坑但还没解决
- 待确认的疑问，不确定的东西
- 临时发现的知识点，不是当前任务重点
- 发现两个 wiki 相关应该合并，但当前任务不涉及
- 待验证的假设，猜测某个行为但还没确认
- PR 待合并，合并后需要更新 wiki
- 临时状态（不是当前代码的真实状态）

判断依据：
- 涉及的模块 → 读 `wiki-<模块名>`
- 涉及的技术点 → 读 `wiki-<技术点>`
- 类似的历史任务 → 读 `wiki-<任务名>-<日期>`

### 2. 任务结束后的总结环节

任务完成后，进入知识总结环节：

1. 读取 `.wiki/staging.md` 全部条目
2. 逐条判断：这条现在能处理吗？（有足够信息、已经确认、不属于其他进行中任务）
   - 能 → 处理 → 从 staging 删除
   - 不能 → 保留
3. 提取这次任务产生的新知识，更新或创建 `wiki-*/SKILL.md`

需要写入 wiki 的情况：
- 遇到了坑并解决 → 更新 `wiki-<问题名>`
- 做了重要决策 → 更新 `wiki-decision-<决策名>`
- 发现了新模式 → 更新 `wiki-<模式名>`
- 修复了 bug → 创建 `wiki-fix-<简述>-<日期>`

## 维护规则

### 规则 1：代码是唯一的真相来源

wiki 里记录的所有代码相关内容（函数名、路径、行为、配置），必须和当前代码一致。

**如果 wiki 和代码冲突，以代码为准，更新 wiki。**

```
wiki 说: _business_status() 只映射 "启用"
代码实际: _business_status() 从 config 加载完整映射
→ wiki 过时了，更新 wiki
```

### 规则 2：读取时验证，发现不一致立即修复

每次读取一个 wiki，快速验证关键信息：

- wiki 提到的文件路径还存在吗？
- wiki 提到的函数名还对吗？
- wiki 描述的行为和代码一致吗？

发现不一致时，**立即修复 wiki**，不要等任务结束：

1. 以代码为准
2. 当场更新 wiki
3. 继续当前任务

### 规则 3：写入时验证

每次写入 wiki 前，确保写入的内容和当前代码一致。

不要凭记忆写，要先读代码确认。

### 规则 4：wiki 只存当前代码的真实状态

wiki 记录的是"此刻代码是什么样"，不是"期望它变成什么样"。

不要把临时状态写进 wiki：
- ❌ PR 待合并 → 不写 wiki，写 staging
- ❌ 待确认的行为 → 不写 wiki，写 staging
- ❌ 期望的最终状态 → 不写 wiki，写 staging

应该写进 wiki 的：
- ✅ 当前代码的实际行为
- ✅ 已确认的坑和解决方案
- ✅ 已合并的变更

临时状态放 staging，等条件满足后再更新 wiki。

```
发现 PR #643 修复了某个 bug，但还没合并
  → wiki: 记录当前代码有这个 bug
  → staging: "PR #643 合并后更新 wiki"

PR 合并了
  → 读 staging → 更新 wiki
```

### 规则 5：不确定时问用户

遇到以下情况，停下来问用户，不要自己猜：

1. **语义模糊** — wiki 说 A，代码做 B，不确定哪个是正确的最终状态
2. **大范围重构** — 代码重构后，wiki 需要大改，不确定怎么改
3. **历史决策** — wiki 记录了一个决策，但代码看起来是另一个方向
4. **删除还是保留** — 某个 wiki 可能过时，但不确定是否还有参考价值

询问格式：
```
wiki `wiki-xxx` 记录的内容和当前代码不一致：
- wiki 说: ...
- 代码实际: ...
以哪个为准？还是这个 wiki 已经废弃可以删除？
```

### 规则 6：变更同步

如果这次任务修改了代码，检查是否有 wiki 记录了被修改的部分：

1. 改了函数名 → 更新引用该函数的 wiki
2. 改了行为 → 更新描述该行为的 wiki
3. 删了文件 → 更新引用该文件的 wiki
4. 改了配置 → 更新描述该配置的 wiki

### 规则 7：合并相关的 wiki

每次写入 wiki 时，检查是否有相关的 wiki 应该合并。

如果两个 wiki 满足以下任一条件，合并：
1. **同源** — 来自同一个配置/模块/系统
2. **互补** — 描述同一事物的不同方面
3. **频繁一起用** — 任务中经常同时需要
4. **描述范围重叠** — description 关键词重叠

合并步骤：
1. 选一个更概括的名字
2. 合并 description，保留所有要点
3. 合并正文，去重并整理
4. 删除旧的 wiki 目录
5. 更新其他 wiki 里的引用

## 命名规范

| 类型 | 命名格式 | 示例 |
|------|----------|------|
| 技术点 | `wiki-<技术点>` | `wiki-csv-encoding` |
| 模块 | `wiki-<模块名>` | `wiki-domain-status` |
| 规则 | `wiki-rule-<规则名>` | `wiki-rule-u08` |
| 修复 | `wiki-fix-<简述>-<日期>` | `wiki-fix-status-map-20260611` |
| 决策 | `wiki-decision-<简述>` | `wiki-decision-use-python` |

## Description 规范

description 是 agent 看到的预览，必须概括整个 wiki 的内容。

好的 description:
```
域名状态映射相关知识
- 状态码: 0=正常, 1=锁定...
- 映射来源: enums_and_invalid.json
- label_map 需要反转使用
```

原则：
- 列出涵盖的所有子主题
- 包含关键术语，方便 agent 匹配
- 3-5 行

## 知识文件结构

```markdown
---
name: wiki-<topic>
description: |
  简短描述（概括所有子主题）
  - 要点1
  - 要点2
---

# 标题

## 快速参考

| 项目 | 说明 |
|------|------|
| ... | ... |

## 详细内容

...

## 相关知识

- [[wiki-<related>]] - 说明
```

## 注意事项

1. **代码是真相** — wiki 和代码冲突时，以代码为准
2. **不确定就问** — 不要猜，问用户
3. **不要重复** — 先检查是否已有相关 wiki
4. **不要过度拆分** — 相关的知识合并在一起
5. **保持简洁** — description 3-5 行，正文不限
6. **交叉引用** — 用 `[[wiki-<name>]]` 链接相关知识
7. **写入即检查** — 每次更新 wiki 时，检查是否有相关的 wiki 应该合并
