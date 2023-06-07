from flask import current_app
from app import models, db
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)
from sqlalchemy import or_
import re

def get_class_by_tablename(table):
    """Return class reference mapped to table.
    :use: current_app.db_tables["users"]
    'User' -> User
    """
    tables = {}
    for c in dir(models):
        if c == table:
            return getattr(models,c)

def perform_pwd_checks(password, password_two=None):
    if not password:
        return False
    if password_two:
        if password != password_two:
            return False
    if len(password) < 8:
        return False
    return True

def verify_jwt(token):
    s = Serializer(current_app.config['SECRET_KEY'])
    try:
        data = s.loads(token)
    except SignatureExpired:
        current_app.logger.warning("SignatureExpired while verifying JWT")
        return False
    except BadSignature:
        current_app.logger.warning("BadSignature while verifying JWT")
        return False
    return data

def generate_jwt(data={}, expiration = 6000):
    s = Serializer(current_app.config['SECRET_KEY'], expires_in = expiration)
    return s.dumps(data).decode('utf-8')

def request_to_json(request):
    data = {
        "headers":dict(request.headers),
        "body":request.get_json(silent=True),
        "args":request.args.to_dict(),
    }
    for property in ["origin","method","mimetype","referrer","remote_addr","url"]:
        data[property] = getattr(request,property)
    return data

def project_creation(tenant, payload, user):
    """
    handles project creation from payload
    """
    name = payload.get("name")
    if not name:
        return False
    description = payload.get("description")
    fw_name = payload.get("framework")

    if fw_name == "empty":
        tenant.create_project(name, user,
            description=description, controls=[])
        return True
    framework = models.Framework.find_by_name(fw_name, tenant.id)
    if not framework:
        return False
    if fw_name == "soc2":
        category_list = []
        if payload.get("criteria-1"):
            category_list.append("security")
        if payload.get("criteria-2"):
            category_list.append("availability")
        if payload.get("criteria-3"):
            category_list.append("confidentiality")
        if payload.get("criteria-4"):
            category_list.append("integrity")
        if payload.get("criteria-5"):
            category_list.append("privacy")

        filter_list = []
        for category in category_list:
            filter_list.append(models.Control.category == category)
        controls = models.Control.query.filter(or_(*filter_list)).filter(models.Control.framework_id == framework.id).all()
    elif fw_name == "cmmc":
        level_list = []
        if payload.get("level-1"):
            level_list.append(1)
        if payload.get("level-2"):
            level_list.append(2)
        if payload.get("level-3"):
            level_list.append(3)
        if payload.get("level-4"):
            level_list.append(4)
        if payload.get("level-5"):
            level_list.append(5)
        if not level_list:
            level_list = [1,2,3,4,5]
        filter_list = []
        for level in level_list:
            filter_list.append(models.Control.level == level)
        controls = models.Control.query.filter(or_(*filter_list)).filter(models.Control.framework_id == framework.id).all()
    elif fw_name == "cmmc_v2":
        level_list = []
        if payload.get("level-1"):
            level_list.append(1)
        if payload.get("level-2"):
            level_list.append(2)
        if payload.get("level-3"):
            level_list.append(3)
        if not level_list:
            level_list = [1,2,3]
        filter_list = []
        for level in level_list:
            filter_list.append(models.Control.level == level)
        controls = models.Control.query.filter(or_(*filter_list)).filter(models.Control.framework_id == framework.id).all()
    else:
        controls = models.Control.query.filter(models.Control.framework_id == framework.id).order_by(models.Control.id.asc()).all()

    tenant.create_project(name, user,
        framework, description=description, controls=controls)
    return True

def generate_layout(dict):
    return {**current_app.config["LAYOUT"], **dict}

def get_users_from_text(text, resolve_users=False, tenant=None):
    data = []
    usernames = re.findall("(?<![@\w])@(\w{1,25})", text)
    if not resolve_users:
        return usernames
    for username in usernames:
        if user := models.User.find_by_username(username):
            if tenant:
                if tenant.has_user(user):
                    data.append(user)
            else:
                data.append(user)
    return data
