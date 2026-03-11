# 项目主数据与统一字典中心设计说明

## 目标
建立统一字典中心，支撑多业务模块的下拉字段与标准编码管理，同时完善项目主数据表的字段规则、校验与审计要求，确保后续扩展成本最低。

## 统一字典中心设计

### 字典类型表（DictType）
- 用途：维护字典分类（例如项目机构、业务板块、数据状态等）
- 关键字段
  - `code`：字典类型编码（唯一）
  - `name`：字典类型名称
  - `group`：字典分组（可选）
  - `description`：说明（可选）
  - `is_active`：启用/停用
  - `sort_order`：排序
  - `version`：版本（可选）
  - `effective_start` / `effective_end`：生效期（可选）

### 字典项表（DictItem）
- 用途：维护字典类型下的具体值
- 关键字段
  - `dict_type`：所属字典类型
  - `code`：字典项编码
  - `name`：字典项名称
  - `value`：字典项值（可选）
  - `parent_code`：上级编码（用于省市联动）
  - `is_active`：启用/停用
  - `sort_order`：排序
  - `version`：版本（可选）
  - `effective_start` / `effective_end`：生效期（可选）
  - `remark`：备注

### 推荐字典类型编码
- `ORG`：项目机构
- `BUSINESS_UNIT`：业务板块
- `DEPT`：项目承担部门
- `PROJECT_TYPE`：项目类型
- `ORG_MODE`：项目组织模式
- `DATA_STATUS`：数据状态
- `PROVINCE`：省
- `CITY`：市（使用 `parent_code` 关联省）

## 项目主数据设计

### 业务规则（采纳后）
- `project_year` 从 `project_code` 第 3-6 位自动生成
- `parent_pj_code` 顶层允许为空
- `project_name` 全局唯一（按管理要求）
- `province_code` / `city_code` 使用 6 位行政区划编码
- 执行层字段改为布尔值：`is_execution_level`

### 字段列表（核心）
- `project_code`：项目主数据编码（`PJ` + 10 位数字）
- `project_name`：项目名称（全局唯一）
- `org_name` / `org_code`：项目机构名称与编码
- `parent_pj_code`：上级 PJ 编码（可空）
- `province_code` / `city_code`：省市编码（6位）
- `business_unit` / `dept` / `project_type` / `org_mode` / `data_status`
- `is_execution_level`：是否为执行层（是/否）
- `project_year`：项目年份（自动生成）
- `status`：启用/停用/作废
- `remark`：备注
- 审计字段：`created_at` / `created_by` / `updated_at` / `updated_by`
- 数据维护字段：`is_deleted`（软删除）、`data_version`（乐观锁）

## 日志与导入导出

### 日志
记录新增、删除、变更、导入的日志：
- 记录修改前/后值
- 操作人、时间、来源

### Excel 导入导出
- 支持 Excel 模板导出
- 支持批量导入
- 记录导入人、导入时间、导入成功/失败数量
- 导入错误需返回行号与错误原因（后续扩展）

## UI 规范（中文友好）
- 字体栈：`PingFang SC / Microsoft YaHei / Noto Sans SC / Source Han Sans SC`
- 标题 18–24px，正文 14–16px，表格 13–14px
- 表格横向滚动：支持超宽字段展示

