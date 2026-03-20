-- 修改 province_code 字段长度从 6 改为 20
ALTER TABLE documents_projectmaster ALTER COLUMN province_code TYPE VARCHAR(20);
