from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0020_remove_userprofile_can_contract_manage"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE EXTENSION IF NOT EXISTS pg_trgm;

            CREATE INDEX IF NOT EXISTS idx_counterparty_party_name_trgm
            ON documents_counterparty USING gin (party_name gin_trgm_ops);

            CREATE INDEX IF NOT EXISTS idx_counterparty_credit_code_trgm
            ON documents_counterparty USING gin (credit_code gin_trgm_ops);

            CREATE INDEX IF NOT EXISTS idx_counterparty_party_type_trgm
            ON documents_counterparty USING gin (party_type gin_trgm_ops);

            CREATE INDEX IF NOT EXISTS idx_counterparty_status_trgm
            ON documents_counterparty USING gin (status gin_trgm_ops);

            CREATE INDEX IF NOT EXISTS idx_counterparty_industry_trgm
            ON documents_counterparty USING gin (industry gin_trgm_ops);

            CREATE INDEX IF NOT EXISTS idx_counterparty_contact_name_trgm
            ON documents_counterparty USING gin (contact_name gin_trgm_ops);

            CREATE INDEX IF NOT EXISTS idx_counterparty_contact_phone_trgm
            ON documents_counterparty USING gin (contact_phone gin_trgm_ops);

            CREATE INDEX IF NOT EXISTS idx_counterparty_registration_address_trgm
            ON documents_counterparty USING gin (registration_address gin_trgm_ops);

            CREATE INDEX IF NOT EXISTS idx_counterparty_former_name_trgm
            ON documents_counterparty USING gin (former_name gin_trgm_ops);

            CREATE INDEX IF NOT EXISTS idx_contract_counterparty_name_snapshot_trgm
            ON documents_contractmaster USING gin (counterparty_name_snapshot gin_trgm_ops);

            CREATE INDEX IF NOT EXISTS idx_counterparty_scope_remark_tsv
            ON documents_counterparty
            USING gin (
                to_tsvector(
                    'simple',
                    coalesce(business_scope, '') || ' ' || coalesce(remark, '')
                )
            );
            """,
            reverse_sql="""
            DROP INDEX IF EXISTS idx_counterparty_scope_remark_tsv;
            DROP INDEX IF EXISTS idx_contract_counterparty_name_snapshot_trgm;
            DROP INDEX IF EXISTS idx_counterparty_former_name_trgm;
            DROP INDEX IF EXISTS idx_counterparty_registration_address_trgm;
            DROP INDEX IF EXISTS idx_counterparty_contact_phone_trgm;
            DROP INDEX IF EXISTS idx_counterparty_contact_name_trgm;
            DROP INDEX IF EXISTS idx_counterparty_industry_trgm;
            DROP INDEX IF EXISTS idx_counterparty_status_trgm;
            DROP INDEX IF EXISTS idx_counterparty_party_type_trgm;
            DROP INDEX IF EXISTS idx_counterparty_credit_code_trgm;
            DROP INDEX IF EXISTS idx_counterparty_party_name_trgm;
            """,
        ),
    ]
