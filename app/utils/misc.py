from flask import current_app
from app import models, db
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)
from sqlalchemy import or_

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

def project_creation(payload, user):
    """
    handles project creation from payload
    """
    name = payload.get("name")
    if not name:
        return False
    description = payload.get("description")
    framework = payload.get("framework")

    table = models.Framework.find_by_name(framework)
    if not table:
        return False
    if framework == "soc2":
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
        controls = models.Control.query.filter(or_(*filter_list)).filter(models.Control.framework_id == table.id).all()
    elif framework == "empty":
        controls = []
    else:
        controls = models.Control.query.filter(models.Control.framework_id == table.id).all()

    models.Project.create(name=name,description=description,
        owner_id=user.id,tenant_id=user.tenant_id,
        controls=controls)
    return True
