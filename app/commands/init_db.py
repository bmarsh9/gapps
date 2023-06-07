from flask import current_app
from flask_script import Command
from app.models import *
from app import db
import datetime, os

class InitDbCommand(Command):
    """ Initialize the database."""

    def run(self):
        init_db()
        print('[INFO] Database has been initialized.')

def init_db():
    """ Initialize the database."""
    db.drop_all()
    db.create_all()
    create_default_users()
    create_default_roles()

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
