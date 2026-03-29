---
name: workspace-instructions
persona: 项目数据平台协作 AI
applyTo:
  - '**/*'
description: |
  本指令文件为本项目 AI agent 提供协作、代码生成、文档维护等建议，确保遵循项目约定与最佳实践。
  - 遵循 Django + 前端分层架构，前后端职责分明。
  - 权限点严格控制，普通用户仅可查项目，无权限需跳转新增页并提示。
  - 分页、导航、数据展示优先在模板和 JS 层优化，避免后端大改。
  - 代码、文档、SQL、脚本等均需注重可维护性与一致性。
  - 发现已有 agent/skill/指令，优先复用并链接，不重复造轮子。
  - 重要约定、架构、命名、权限、分页等，优先链接相关 agent/skill/文档。
  - 生成内容应简明、注释充分，便于后续维护。
  - 复杂/分区场景可用 applyTo 精细指定。
workflow:
  1. 检查是否已有 agent/skill/指令，优先链接。
  2. 发现项目约定、架构、权限、分页等知识，整理为可链接的知识点。
  3. 生成内容时，遵循分层、权限、分页等约定，必要时引用 agent/skill。
  4. 复杂场景建议细分 applyTo，便于后续扩展。
  5. 生成后建议示例 prompt，便于用户理解和复用。
examples:
  - 优化分页导航体验，参考 .github/agents/project-list-pagination.agent.md
  - 新增权限点，遵循权限约定，见 /memories/permissions-preferences.md
  - 生成 SQL 脚本，注重可维护性与一致性
  - 维护文档时，优先链接已有知识点
