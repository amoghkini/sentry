# Generated by Django 5.0.8 on 2024-09-06 08:37

from django.db import migrations

from sentry.new_migrations.migrations import CheckedMigration


class Migration(CheckedMigration):
    # This flag is used to mark that a migration shouldn't be automatically run in production.
    # This should only be used for operations where it's safe to run the migration after your
    # code has deployed. So this should not be used for most operations that alter the schema
    # of a table.
    # Here are some things that make sense to mark as post deployment:
    # - Large data migrations. Typically we want these to be run manually so that they can be
    #   monitored and not block the deploy for a long period of time while they run.
    # - Adding indexes to large tables. Since this can take a long time, we'd generally prefer to
    #   run this outside deployments so that we don't block them. Note that while adding an index
    #   is a schema change, it's completely safe to run the operation after the code has deployed.
    # Once deployed, run these manually via: https://develop.sentry.dev/database-migrations/#migration-deployment

    is_post_deployment = False

    dependencies = [
        ("sentry", "0757_add_scopes_to_apiapplication"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterUniqueTogether(
                    name="spanattributeextractionruleconfig",
                    unique_together=None,
                ),
                migrations.RemoveField(
                    model_name="spanattributeextractionruleconfig",
                    name="project",
                ),
                migrations.DeleteModel(
                    name="SpanAttributeExtractionRuleCondition",
                ),
                migrations.DeleteModel(
                    name="SpanAttributeExtractionRuleConfig",
                ),
            ],
            database_operations=[],
        )
    ]
