
# Main 分支保护规则说明

本目录用于存放 AgroTech 项目的 GitHub Rulesets 配置

当前统一使用：

```text
.github/rulesets/main-protection.json
```

项目负责人创建仓库后，只需要导入一次该文件并启用即可

## 1. 当前规则做什么

`main-protection.json` 只保护 `main`：

- 禁止直接更新 `main`
- 禁止删除 `main`
- 禁止 Force Push
- 所有修改必须通过 Pull Request
- 普通成员可以正常创建 / Push 开发分支并提交 PR
- Repository Admin 可以在 **Pull Request 场景**下完成最终合并
- 基础模板不强制额外 Approval，也不要求 CODEOWNERS

协会项目通常约定：

```text
项目负责人 = Repository Admin
项目成员   = Write
```

因此可以理解为：

> 成员负责提交修改，项目负责人负责最终合并

## 2. 为什么不强制 Approval

协会既有多人项目，也有负责人单独维护的项目；如果基础模板统一要求至少 1 人 Approval，单人项目会被迫找其他人做形式审批

因此基础模板采用：

```text
必须 PR
+ 只有负责人能最终更新 main
+ 不强制额外 Approval
```

成熟项目、高风险项目可以根据需要另外增加 Review、CODEOWNERS、CI 等要求

## 3. Repository Admin 为什么仍然不能直接 Push main

Ruleset 的 bypass 为：

```text
Repository Admin
→ Allow for pull requests only
```

负责人可以在 PR 场景下绕过 `Restrict updates` 完成合并，但不会因此获得直接 Push `main` 的正常通道

GitHub 在负责人合并时可能显示“bypass rules”“Merge without waiting for requirements”等类似提示，这是正常行为

## 4. 正常协作流程

```text
Issue
  ↓
任务 Branch
  ↓
Commit + Push
  ↓
Pull Request
  ↓
项目负责人 Merge
```

推荐分支示例：

```text
feat/auto-navigation
fix/pick-timeout
refactor/arm-interface
docs/deployment-flow
```

分支命名属于协作约定，基础模板不通过 Ruleset / CI 硬性限制

## 5. Push main 被拒绝怎么办

如果执行：

```bash
git push origin main
```

GitHub 返回 `GH013`、protected branch、rule violation，或者 Git 本地提示 `fetch first / pull first / non-fast-forward`，不要先假设账号坏了

### 情况 A：还没有 Commit

直接创建任务 Branch：

```bash
git switch -c feat/your-work
```

再正常 Commit / Push

### 情况 B：已经在 main 上 Commit，而且提交有用

> [!CAUTION]
> **先保存提交，不要先 `reset --hard`**

```bash
git switch -c feat/your-work
git push -u origin HEAD
```

确认 GitHub 上已经看到新 Branch 与提交后，再恢复本地 `main`：

```bash
git switch main
git fetch origin
git reset --hard origin/main
```

即使已经连续 Commit 多次，也可以用同样方法整体保留

完整说明见 [`../CONTRIBUTING.md`](../CONTRIBUTING.md)

## 6. 可选的本地防误操作提醒

模板附带：

```text
.githooks/pre-commit
.githooks/pre-push
scripts/setup-git.sh
scripts/setup-git.ps1
```

Git 不会在 Clone 后自动启用仓库自带 Hook，因此需要每份 Clone 主动运行一次 setup 脚本

Linux / Ubuntu：

```bash
bash scripts/setup-git.sh
```

Windows PowerShell：

```powershell
.\scripts\setup-git.ps1
```

Hook 只是为了更早提示，**不是安全边界**；即使成员完全没有启用 Hook，GitHub Ruleset 仍会保护 `main`

## 7. 初始化方式

项目负责人创建公开项目仓库后：

1. 进入仓库 `Settings`
2. 打开 `Rules → Rulesets`
3. `New ruleset → Import a ruleset`
4. 导入 `.github/rulesets/main-protection.json`
5. 检查 Target 为 `main`
6. 检查 Bypass 为 `Repository admin → Allow for pull requests only`
7. 检查已启用 `Restrict updates`、`Restrict deletions`、`Require a pull request before merging`、`Block force pushes`
8. 点击 `Create`

完成后无需再额外配置审批人、CODEOWNERS 或第二套 Ruleset
