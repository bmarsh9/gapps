from flask import current_app
from flask_script import Command
from flask_migrate import Migrate
from alembic import command
from app.models import *
from app import db
import datetime, os

class InitDbCommand(Command):
    """ Initialize the database."""

    def run(self):
        init_db()
        print('[INFO] Database has been initialized.')

class CreateDbCommand(Command):
    """ Migrate the database."""

    def run(self):
        create_db()
        print('[INFO] Database has been created.')

class MigrateDbCommand(Command):
    """ Migrate the database."""

    def run(self):
        migrate_db()
        print('[INFO] Database has been migrated.')

def init_db():
    """ Initialize the database. Will delete and recreate"""
    db.drop_all()
    db.create_all()
    create_default_users()
    create_default_roles()

def create_db():
    """ Create the database. Will not update models if they already exist"""
    db.create_all()
    create_default_users()
    create_default_roles()

def migrate_db():
    """ Migrate the database."""
    config = Migrate(current_app, db).get_config()
    print(config)
    command.upgrade(config, 'head')
#    migrate = Migrate()
#    migrate.init_app(current_app, db)

def create_default_users():
    """ Create users """
    default_user = current_app.config.get("DEFAULT_EMAIL","admin@example.com")
    default_password = current_app.config.get("DEFAULT_PASSWORD","admin")
    if not User.query.filter(User.email == default_user).first():
        user = User.add(
            default_user,
            password=default_password,
            confirmed=True,
            built_in=True,
            super=True
        )
    return True

def create_default_roles():
    """ Create roles """
    for role in ["Admin","Editor","Viewer","User","Vendor"]:
        r = Role(name=role.lower(),label=role)
        db.session.add(r)
        db.session.commit()
    return True
