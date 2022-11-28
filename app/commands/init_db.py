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
    create_default_tenant()
    create_default_users()
#    create_base_controls()
#    create_base_policies()

def create_default_tenant():
    if not Tenant.query.filter(Tenant.name == current_app.config['DEFAULT_TENANT_LABEL']).first():
        tenant = Tenant(name=current_app.config['DEFAULT_TENANT_LABEL'])
        db.session.add(tenant)
        db.session.commit()
    return True

def create_default_users():
    """ Create users """
    default_user = current_app.config.get("DEFAULT_EMAIL","admin@example.com")
    default_password = current_app.config.get("DEFAULT_PASSWORD","admin")
    tenant = Tenant.query.filter(Tenant.name == current_app.config['DEFAULT_TENANT_LABEL']).first()
    if not User.query.filter(User.email == default_user).first():
        user = User.add(
            default_user,
            password=default_password,
            confirmed=True,
            tenant_id=tenant.id,
            roles=["Admin", "User"],
            create_role=True
        )
    return True

def create_base_controls():
    with open("app/files/base_controls/soc2_controls.json") as f:
        controls=json.load(f)
        f = Framework(name="soc2", description="Framework for soc2")
        for control in controls:
            c = Control(
                name=control["name"],
                description=control["name"],
                ref_code=control["ref_code"],
                system_level=control["system_level"],
                category=control["category"],
                subcategory=control["subcategory"],
                dti=control["dti"],
                dtc=control["dtc"],
                meta=control["meta"]
            )
            for area in control["focus_areas"]:
                fa = ControlListFocusArea(
                    name=area["name"],
                    description=area["description"],
                    ref_code=area["ref_code"],
                    mitigation=area["mitigation"],
                    meta=area["meta"]
                )
                c.focus_areas.append(fa)
            f.controls.append(c)
        db.session.add(f)
        db.session.commit()
    return True

def create_base_policies():
    for filename in os.listdir("app/files/base_policies/"):
        if filename.endswith(".html"):
            with open(f"app/files/base_policies/{filename}") as f:
                name = filename.split(".")[0]
                p = Policy(name=name,
                    description=f"Content for the {name} policy",
                    content=f.read(),
                    template=f.read()
                )
                db.session.add(p)
    db.session.commit()
    return True
