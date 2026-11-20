---
name: superwiki
description: 为项目接入知识库（团队/个人模式）、升级项目里的 superwiki-auto、全库审计。
disable-model-invocation: true
---

# SuperWiki（管理入口）

日常的知识检索与维护由各项目里的 `superwiki-auto` 自动完成。本 skill 只在用户手动调用时做三件事：**接入**、**升级**、**审计**。代码是唯一真相来源。

本 skill 目录下的 `superwiki-init` 是唯一的接入与升级工具，`templates/superwiki-auto/` 是项目入口的模板，`VERSION` 是模板版本。

## 1. 判断项目现状

在项目根目录按顺序检查，第一条命中即为现状：

| 现状 | 结论 |
|---|---|
| `.agents/skills/superwiki-auto/` 存在，且 `.agents/skills` 是实体目录 | 团队模式，已接入 |
| `.wiki/skills/superwiki-auto/` 存在 | 个人模式，已接入 |
| `.agents/skills/` 是实体目录，里面有 `wiki-*` 或旧的项目版 `superwiki/` | 团队模式旧版，走升级里的迁移 |
| `.wiki/skills/` 存在 | 个人模式旧版，走升级里的迁移 |
| 以上都没有 | 未接入 |

把结论告诉用户，再按用户的意图进入下面某一节。

## 2. 接入

用户没说模式时问一次：**团队模式**（知识提交进 Git，同事拉代码就能用）还是**个人模式**（只在本机，不进团队仓库）。然后运行：

```bash
<本 skill 目录>/superwiki-init --team <PROJECT_ROOT>
<本 skill 目录>/superwiki-init --personal <PROJECT_ROOT>
```

- 团队模式下，团队里有人用 Claude Code 时加 `--claude`，用 Cursor 时加 `--cursor`，为它们提交指向 `.agents/skills` 的入口。
- 个人模式默认接入全部运行时入口；用户只用部分工具时，用 `--codex`、`--opencode`、`--claude`、`--cursor` 收窄。
- 脚本先检查全部路径，发现冲突就以 `❌` 退出、不写任何文件。把它列出的冲突原样告诉用户，等用户决定；入口冲突可以用运行时参数跳过对应入口后重试。
- 完成后提醒用户新开会话。团队模式提醒用户审阅并提交新增文件。

## 3. 升级

先读项目知识目录里（团队模式 `.agents/skills/`，个人模式 `.wiki/skills/`）`superwiki-auto/SKILL.md` frontmatter 的 `metadata.superwiki-template`，和本 skill 的 `VERSION` 比较。相同就告诉用户已是最新；不同就用同一模式重新运行 `superwiki-init`：模板生成的文件按模板重写，模板已删除的文件一并移除，`references/local.md` 和全部 `wiki-*` 保留。团队模式升级后，用 `git diff` 把变化给用户审阅。

旧版迁移：

- **团队模式旧版**（项目里有自己的 `superwiki/`）：逐段对比它和 `templates/superwiki-auto/`。只适用于本项目的规则整理进 `local.md` 的草稿；通用的改进单独列给用户，建议合并回本仓库模板。用户确认后删除旧的 `superwiki/` 目录，再运行 `superwiki-init --team`，最后把 `local.md` 草稿写进去。旧目录与全局 `superwiki` 同名，会和本 skill 抢同一个名字，所以脚本在它还在时会拒绝运行。
- **个人模式旧版**（只有 `.wiki/skills`）：直接运行 `superwiki-init --personal`。
- 想在团队模式与个人模式之间切换：脚本会拒绝。先和用户确认，再手动把 `wiki-*` 移到目标知识目录、删掉原来的知识目录和入口，然后用目标模式运行。

## 4. 审计

用户要求全库审计或大批量合并时，先完整读取项目里 `superwiki-auto/references/writing.md` 与 `review.md`，主线程按它们执行，写入仍由主线程完成。

需要独立复核时，完整读取 [审计角色](references/roles/wiki-auditor.md)，把它的**完整正文逐字粘入**当前运行时的原生只读子代理提示词，再补上：项目根目录与知识目录的绝对路径、待审的写入范围（目标路径、变更类型、草稿 `name` + `description`）、返回格式。提示词本身就是子代理的全部行为来源，它只依据粘入的正文工作。运行时没有子代理能力时，如实说明，并在主线程按同一角色步骤自审。

## 边界

- 只在用户手动调用时运行；不暂存、不提交、不推送，不修改全局 skill、agent、模型或权限配置。
- 不引入 hook、常驻服务、后台任务或自动注入。
