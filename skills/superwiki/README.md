# SuperWiki

项目知识库：把项目里踩过的坑、模块约定、历史决策写成 `wiki-*` skill，让 agent 在干活时自动查、干完自动存。代码始终是唯一真相来源。

分成两个 skill：

| skill | 放在哪 | 触发方式 | 负责 |
|---|---|---|---|
| `superwiki` | 你本机的全局 skill 目录 | 只能手动调用（`/superwiki`、`@superwiki`、`$superwiki`） | 接入项目、升级、全库审计 |
| `superwiki-auto` | 每个接入的项目里 | 自动触发 | 日常检索与维护 `wiki-*` |

## 两种模式

| | 团队模式 `--team` | 个人模式 `--personal` |
|---|---|---|
| 知识位置 | `.agents/skills/wiki-*` | `.wiki/skills/wiki-*` |
| 进不进 Git | 进，同事拉代码就能用，不用装任何东西 | 不进，`.wiki/` 和入口链接写入 `.git/info/exclude` |
| 运行时入口 | Codex / OpenCode 直接读 `.agents/skills`；`--claude`、`--cursor` 额外提交指向它的链接 | 默认给全部运行时建指向 `.wiki/skills` 的链接 |
| 草稿 `.wiki/staging.md` | `.gitignore` 写入 `/.wiki/staging.md` | 随 `.wiki/` 一起被排除 |

## 安装

```bash
./skills.sh   # 把 superwiki 链接到 ~/.agents/skills
```

其他运行时的全局 skill 目录按需自行链接到本仓库。安装后新开会话。

## 接入与升级

在 agent 里手动调用 `superwiki`，它会判断项目现状、问你选哪种模式，然后运行 `superwiki-init`。也可以直接运行：

```bash
superwiki-init --team /path/to/project
superwiki-init --team --claude /path/to/project   # 团队里有人用 Claude Code
superwiki-init --personal /path/to/project
```

重复运行同一模式就是升级：模板生成的文件按模板重写，模板已删除的文件一并移除，`superwiki-auto/references/local.md`（项目专属约定）和全部 `wiki-*` 保留。模板版本见 `VERSION`，写在生成的 `SKILL.md` 的 `metadata.superwiki-template` 里。

脚本写入前会检查所有要用到的路径：入口位置被占用、团队与个人模式互转、旧的项目版 `superwiki/` 还在，都会以 `❌` 退出，一个文件也不写。项目在仓库子目录里时，忽略规则照样写到正确的位置。

## 仓库结构

```text
SKILL.md                         全局 superwiki：接入、升级、审计（手动调用）
agents/openai.yaml               Codex 的手动调用设置
superwiki-init                   接入与升级脚本
skills.sh                        全局 skill 链接安装器
VERSION                          模板版本
templates/superwiki-auto/        项目入口模板
  SKILL.md.tmpl                  检索、自主维护、边界（生成时去掉 .tmpl，避免模板被当成 skill 发现）
  references/writing.md          写入与草稿维护协议
  references/review.md           审核与冲突处理
  references/local.md            项目专属约定（只在首次生成）
references/roles/wiki-auditor.md 全库审计时委派给只读子代理的角色正文
tests/                           脚本行为测试：python3 -m pytest tests
```

修改模板后提升 `VERSION`，再在各项目里重新运行 `superwiki-init` 升级。

## 边界

不引入 hook、常驻服务、后台任务或自动注入；不暂存、不提交、不推送；不修改全局 agent、模型或权限配置。
