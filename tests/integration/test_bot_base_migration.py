"""Migration up/down/up for the bot_base tables (real PostgreSQL).

Loads the migration module directly and runs it through alembic's Operations
context, isolated from the conftest ``create_all`` (which already built the
tables — so we drop them first to exercise a clean upgrade). Validates the
chain anchors on the always-present core root and the revision id is ≤ 32 chars.
"""
import importlib.util
import os

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect


def _load_migration():
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "migrations",
        "versions",
        "20260610_1000_create_bot_base.py",
    )
    spec = importlib.util.spec_from_file_location("create_bot_base", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


migration = _load_migration()
_TABLES = ("bot_base_link", "bot_base_session", "bot_base_link_token")


def _has_tables(connection) -> bool:
    existing = set(inspect(connection).get_table_names())
    return all(table in existing for table in _TABLES)


@pytest.fixture
def migration_connection(app):
    from vbwd.extensions import db

    connection = db.engine.connect()
    transaction = connection.begin()
    operations = Operations(MigrationContext.configure(connection))
    # create_all() already built the tables; drop them so upgrade runs clean.
    for table in reversed(_TABLES):
        if inspect(connection).has_table(table):
            operations.drop_table(table)
    try:
        yield connection
    finally:
        transaction.rollback()
        connection.close()


@pytest.mark.integration
def test_revision_anchors_on_core_root_and_id_is_short():
    assert migration.revision == "20260610_1000_create_bot_base"
    assert migration.down_revision == "vbwd_001"
    assert len(migration.revision) <= 32


@pytest.mark.integration
def test_up_down_up(migration_connection):
    assert not _has_tables(migration_connection)
    context = MigrationContext.configure(migration_connection)
    with Operations.context(context):
        migration.upgrade()
    assert _has_tables(migration_connection)
    with Operations.context(context):
        migration.downgrade()
    assert not _has_tables(migration_connection)
    with Operations.context(context):
        migration.upgrade()
    assert _has_tables(migration_connection)
