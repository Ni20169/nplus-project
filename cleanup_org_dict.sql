-- Cleanup script for legacy ORG dictionary data
-- Safe to run multiple times.

BEGIN;

-- Optional check: inspect ORG dict type before deletion.
SELECT id, code, name
FROM documents_dicttype
WHERE code = 'ORG';

-- Optional check: inspect ORG dict items before deletion.
SELECT di.id, di.code, di.name
FROM documents_dictitem di
JOIN documents_dicttype dt ON dt.id = di.dict_type_id
WHERE dt.code = 'ORG'
ORDER BY di.sort_order, di.code;

-- Delete ORG dict items first to satisfy foreign key constraints.
DELETE FROM documents_dictitem
WHERE dict_type_id IN (
    SELECT id FROM documents_dicttype WHERE code = 'ORG'
);

-- Delete ORG dict type.
DELETE FROM documents_dicttype
WHERE code = 'ORG';

COMMIT;

-- Verify cleanup result.
SELECT id, code, name
FROM documents_dicttype
WHERE code = 'ORG';

SELECT di.id, di.code, di.name
FROM documents_dictitem di
JOIN documents_dicttype dt ON dt.id = di.dict_type_id
WHERE dt.code = 'ORG';
