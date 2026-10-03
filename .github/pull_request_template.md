
> [!IMPORTANT]
> **AgroTech 协作流程：Issue → Branch → Commit → Push → Pull Request → 项目负责人 Merge**
>
> 请勿直接操作 `main`；分支命名遵循项目约定即可，基础模板不做硬性 CI 拦截

## 关联 Issue

Closes #

<!--
原则上一个明确开发任务应先有对应 Issue
如果本 PR 不需要 Issue，请简要说明原因
-->

## 本次修改

- 

## 验证情况

- 编译 / 构建：
- 运行 / 仿真 / 真机：
- 其他验证：

## 已知问题

- 无 / 请填写

## Checklist

- [ ] 修改内容与本 PR 主题一致
- [ ] 已完成当前项目阶段所需的基本验证
- [ ] 相关 README / docs / 配置说明已同步（如需要）
- [ ] 合并后不会破坏 `main` 的基本可用性

## Merge 说明

- 单人开发任务：由本人自行通过 `Merge without waiting for requirements to be met (bypass rules)` 完成合并
- 多人协作任务：项目负责人(即仓库 Admin)的分支合并方式同上，非项目负责人则需要经过项目负责人的 review 后由项目负责人完成合并
- Delete Branch：原则上 PR 合并后应删除分支，除非该分支仍有后续开发任务
