-- 统一字典中心初始化（字典类型）
INSERT INTO documents_dicttype (code, name, "group", description, is_active, sort_order, version, created_at, updated_at)
VALUES
('ORG', '项目机构', '基础字典', '项目机构字典', true, 10, '', NOW(), NOW()),
('BUSINESS_UNIT', '业务板块', '基础字典', '业务板块字典', true, 20, '', NOW(), NOW()),
('DEPT', '项目承担部门', '基础字典', '项目承担部门字典', true, 30, '', NOW(), NOW()),
('PROJECT_TYPE', '项目类型', '基础字典', '项目类型字典', true, 40, '', NOW(), NOW()),
('ORG_MODE', '项目组织模式', '基础字典', '项目组织模式字典', true, 50, '', NOW(), NOW()),
('DATA_STATUS', '数据状态', '基础字典', '数据状态字典', true, 60, '', NOW(), NOW()),
('PROVINCE', '省', '行政区划', '省级行政区划', true, 70, '', NOW(), NOW()),
('CITY', '市', '行政区划', '市级行政区划', true, 80, '', NOW(), NOW());

-- 数据状态示例（可按需扩展）
INSERT INTO documents_dictitem (dict_type_id, code, name, value, parent_code, is_active, sort_order, version, remark, created_at, updated_at)
SELECT id, 'ENABLED', '启用', '启用', '', true, 1, '', '默认启用', NOW(), NOW()
FROM documents_dicttype WHERE code = 'DATA_STATUS';

INSERT INTO documents_dictitem (dict_type_id, code, name, value, parent_code, is_active, sort_order, version, remark, created_at, updated_at)
SELECT id, 'DISABLED', '停用', '停用', '', true, 2, '', '默认停用', NOW(), NOW()
FROM documents_dicttype WHERE code = 'DATA_STATUS';

INSERT INTO documents_dictitem (dict_type_id, code, name, value, parent_code, is_active, sort_order, version, remark, created_at, updated_at)
SELECT id, 'INVALID', '作废', '作废', '', true, 3, '', '默认作废', NOW(), NOW()
FROM documents_dicttype WHERE code = 'DATA_STATUS';
