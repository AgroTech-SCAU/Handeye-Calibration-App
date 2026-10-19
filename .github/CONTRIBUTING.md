
# AgroTech 项目协作指南

这份文档用于说明协会项目最基本的 Git / GitHub 协作流程，并提供常见误操作的自救方法

> [!IMPORTANT]
> ## 30 秒协作流程
>
> ```text
> 创建 / 认领 Issue
>        ↓
> 创建任务 Branch
>        ↓
> 开发 + 小步 Commit
>        ↓
> Push 自己的 Branch
>        ↓
> 创建 Pull Request
>        ↓
> 项目负责人检查并 Merge
> ```
>
> **不要直接在 `main` 开发或 Push**

## 1. 仓库角色

| 角色 | 常用 GitHub 权限 | 主要职责 |
| --- | --- | --- |
| 项目负责人 | Admin | 管理仓库、检查 PR、最终合并到 `main` |
| 项目成员 | Write | 开发、Push 开发分支、提交 PR |
| 协助管理成员 | Triage / Maintain | 按项目需要协助 Issue / PR / 仓库维护 |

基础模板不强制额外 Approval；某些高风险或成熟项目可以在此基础上追加 Review、CODEOWNERS、CI 等更严格规则

## 2. 第一次 Clone：可选开启本地防误操作提醒

GitHub Ruleset 才是最终保护；本地 Hook 只是为了更早、更友好地告诉你“操作错在哪里”

Linux / Ubuntu：

```bash
git clone <仓库 URL>
cd <仓库目录>
bash scripts/setup-git.sh
```

Windows PowerShell：

```powershell
git clone <仓库 URL>
cd <仓库目录>
.\scripts\setup-git.ps1
```

如果没有运行脚本，也可以正常开发；只是本地不会提前弹出 AgroTech 的提示，最终仍会由 GitHub Ruleset 保护 `main`

## 3. 开始任务：原则上先创建或认领 Issue

Bug、需求、功能、文档或明确的工程任务，原则上先形成 Issue，避免任务只存在于聊天记录里

推荐流程：

1. 打开仓库 `Issues`
2. 选择合适的 Issue Form：功能 / Bug / 一般任务
3. 如果已有对应 Issue，直接认领 / 确认由你处理，不要重复创建
4. 在 Issue 右侧 `Development` 区域选择 `Create a branch`，让 GitHub 自动建立 Issue 与 Branch 的关联

非常小的拼写修正等改动，可由项目负责人决定是否省略 Issue；不要为了流程本身制造无意义 Issue

## 4. Branch：一个分支解决一个主题

协会现有技术规范统一采用短生命周期任务分支；推荐格式：

```text
<type>/<scope>-<summary>
```

如果任务较简单，也可以使用：

```text
<type>/<short-description>
```

常用类型：

```text
feat/       新功能
fix/        Bug 修复
refactor/   重构
docs/       文档
chore/      工程维护
perf/       性能优化
```

示例：

```text
feat/auto-navigation
fix/fdcan-rx-callback
refactor/arm-interface
docs/development-flow
```

机械臂、嵌入式等专业项目可继续使用已有的 `adapter/`、`behavior/`、`contract/`、`deploy/`、`sdk/`、`chip/` 等领域类型

> 分支命名是团队协作约定，不在基础模板中通过 CI / Ruleset 硬性拦截；核心要求是：**不要直接在 `main` 开发，一个分支只解决一个清晰主题**

如果不从 Issue 页面创建分支，也可以手动：

```bash
git switch main
git pull --ff-only origin main
git switch -c feat/auto-navigation
```

## 5. 开发与 Commit

建议小步提交，每个 Commit 只表达一个相对清楚的修改：

```bash
git status
git add .
git commit -m "feat(nav): add auto navigation"
```

推荐 Commit 格式：

```text
<type>(<scope>): <summary>
```

示例：

```text
feat(nav): add auto navigation
fix(fdcan): avoid rx callback overwrite
refactor(arm): simplify planner interface
docs(flow): update deployment guide
```

## 6. Push 自己的 Branch

第一次 Push：

```bash
git push -u origin HEAD
```

之后：

```bash
git push
```

请不要执行：

```bash
git push origin main
git push -f origin main
git push --force origin main
```

如果 GitHub 拒绝向 `main` Push，这是保护规则正常生效，不代表账号或仓库损坏

## 7. 创建 Pull Request

Push 后创建 PR：

```text
你的任务 Branch
        ↓
       main
```

仓库会自动填入 PR Template；至少说明：

- 关联哪个 Issue（通常使用 `Closes #...`）
- 本次修改做了什么
- 如何验证
- 有什么已知问题

如果 PR 使用 `Closes #123` 等 GitHub Closing Keyword，PR 合并后对应 Issue 可以自动关闭

## 8. 谁负责 Merge

### 普通成员的 PR

```text
成员开发 Branch
     ↓
创建 PR
     ↓
项目负责人检查
     ↓
Merge → main
```

普通项目成员负责提交修改，项目负责人负责最终合并；若确需其他成员承担最终合并职责，应正式调整其 Repository 权限或项目规则，而不是只用口头“授权合并”代替权限配置

### 项目负责人自己的修改

单人项目或负责人自己开发时，也走：

```text
负责人 Branch → PR → 检查 Diff → Merge → main
```

基础 Ruleset 不强制找第二个人形式审批；负责人合并时 GitHub 可能显示规则 bypass 提示，这是 `Repository Admin → Allow for pull requests only` 的正常行为

## 9. ❗误在 main 上 Commit 了：先救提交，再恢复 main

> [!CAUTION]
> **如果你已经在 `main` 上产生了有用 Commit：不要第一时间 `reset --hard`，也不要因为终端提示“pull / fetch first”就盲目 Pull**

假设你已经在本地 `main` 连续 Commit 了多次，这些 Commit 都可以整体保留下来

### 第一步：立刻从当前状态创建新 Branch

```bash
git switch -c feat/your-work
```

这一步不会删除你刚才的 Commit；无论已经 Commit 1 次还是很多次，当前提交记录都会跟随新 Branch 保留下来

### 第二步：先 Push 新 Branch 到远端

```bash
git push -u origin HEAD
```

到 GitHub 页面确认这个 Branch 和 Commit 都已经存在

### 第三步：再恢复本地 main

```bash
git switch main
git fetch origin
git reset --hard origin/main
```

现在：

- 你的有用 Commit 已经安全保存在新 Branch 和远端
- 本地 `main` 恢复为 GitHub 上的正式 `main`
- 接下来从新 Branch 创建 PR 即可

如果你对当前状态不确定，**先停止执行 reset / rebase / force push，保留现场并询问项目负责人**

## 10. 如果还没有 Commit，只是在 main 改了文件

通常可以直接把当前修改带到新 Branch：

```bash
git switch -c feat/your-work
```

然后正常：

```bash
git add .
git commit -m "feat: describe your change"
git push -u origin HEAD
```

## 11. PR 冲突怎么办

如果 PR 提示与 `main` 冲突，不要强推 `main`

优先使用容易理解的 merge 方式同步：

```bash
git fetch origin
git switch <你的分支>
git merge origin/main
```

手动解决冲突后：

```bash
git add .
git commit
git push
```

涉及不熟悉的核心代码、URDF / TF、硬件参数、接口契约等冲突时，不要盲目覆盖，先找相关负责人确认

## 12. PR 合并后

同步本地：

```bash
git switch main
git pull --ff-only origin main
```

确认任务分支已经不再需要后：

```bash
git branch -d <分支名>
```

远程分支可以在 GitHub PR 合并后删除

## 13. 一分钟记忆版

```text
先有任务 / Issue
      ↓
任务 Branch
      ↓
小步 Commit
      ↓
Push Branch
      ↓
Pull Request
      ↓
负责人 Merge
```

遇到 `main` Push 被拒绝时，先判断：

```text
还没 Commit → 直接切新 Branch
已经 Commit → 先切新 Branch并 Push 保存 → 再恢复 main
```

Ruleset 的具体说明见：[`rulesets/README.md`](rulesets/README.md)
