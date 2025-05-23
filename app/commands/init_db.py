from flask import current_app
from flask_script import Command
from flask_migrate import Migrate
from alembic import command
from app.models import *
from app import db


class InitDbCommand(Command):
    """Initialize the database."""

    def run(self):
        init_db()
        print("[INFO] Database has been initialized.")


class CreateDbCommand(Command):
    """Migrate the database."""

    def run(self):
        create_db()
        print("[INFO] Database has been created.")


class MigrateDbCommand(Command):
    """Migrate the database."""

    def run(self):
        migrate_db()
        print("[INFO] Database has been migrated.")


class DataImportCommand(Command):
    """Perform data import tasks"""

    def run(self):
        raise ValueError("Not implemented")


class ForceDropTablesCommand(Command):
    """Force Drop all tables in the database"""

    def run(self):
        force_drop_all_tables()


def init_db():
    """Initialize the database. Will delete and recreate"""
    db.drop_all()
    db.create_all()
    create_default_users()
    create_default_roles()


def create_db():
    """Create the database. Will not update models if they already exist"""
    db.create_all()
    create_default_users()
    create_default_roles()


def migrate_db():
    """Migrate the database."""
    config = Migrate(current_app, db).get_config()
    command.upgrade(config, "head")


def create_default_users():
    """Create users"""
    # Create default tenant and add the user

    default_user = current_app.config.get("DEFAULT_EMAIL", "admin@example.com")
    default_password = current_app.config.get("DEFAULT_PASSWORD", "admin1234567")
    if not User.query.filter(User.email == default_user).first():
        user = User.add(
            default_user,
            password=default_password,
            confirmed=True,
            built_in=True,
            super=True,
            require_pwd_change=True,
            return_user_object=True,
        )
        Tenant.create(user, "Default", default_user, is_default=True, init_data=True)
    return True


def create_default_roles():
    """Create roles"""
    for role in Role.VALID_ROLE_NAMES:
        r = Role(name=role.lower(), label=role)
        db.session.add(r)
        db.session.commit()
    return True


def force_drop_all_tables():
    meta = db.metadata
    meta.reflect(bind=db.engine)
    meta.drop_all(bind=db.engine)
