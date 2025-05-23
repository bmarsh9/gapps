from flask import current_app, abort
from app import models, db
from itsdangerous import (
    TimedJSONWebSignatureSerializer as Serializer,
    BadSignature,
    SignatureExpired,
)
from sqlalchemy import or_
import re


class Response:
    def __init__(self, message: str, success: bool):
        self.message = message
        self.success = success

    def __repr__(self):
        return f"Response(message='{self.message}', success={self.success})"


def get_class_by_tablename(table):
    """Return class reference mapped to table.
    :use: current_app.db_tables["users"]
    'User' -> User
    """
    tables = {}
    for c in dir(models):
        if c == table:
            return getattr(models, c)


def perform_pwd_checks(password, password_two=None):
    if not password:
        return False
    if password_two:
        if password != password_two:
            return False
    if len(password) < 12:
        return False
    return True


def verify_jwt(token):
    if not token:
        current_app.logger.warning("Empty token when verifying JWT")
        return False
    s = Serializer(current_app.config["SECRET_KEY"])
    try:
        data = s.loads(token)
    except SignatureExpired:
        current_app.logger.warning("SignatureExpired while verifying JWT")
        return False
    except BadSignature:
        current_app.logger.warning("BadSignature while verifying JWT")
        return False
    return data


def generate_jwt(data={}, expiration=6000):
    s = Serializer(current_app.config["SECRET_KEY"], expires_in=expiration)
    return s.dumps(data).decode("utf-8")


def request_to_json(request):
    data = {
        "headers": dict(request.headers),
        "body": request.get_json(silent=True),
        "args": request.args.to_dict(),
    }
    for property in ["origin", "method", "mimetype", "referrer", "remote_addr", "url"]:
        data[property] = getattr(request, property)
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
        tenant.create_project(name, user.id, description=description, controls=[])
        return True
    framework = models.Framework.find_by_name(fw_name, tenant.id)
    if not framework:
        abort(422, f"Framework not found:{fw_name}")

    # check if framework has initialized controls
    if not framework.has_controls():
        framework.init_controls()

    if fw_name == "soc2":
        category_list = []
        criteria_list = [
            "security",
            "availability",
            "confidentiality",
            "integrity",
            "privacy",
        ]
        criteria = payload.get("criteria", {})
        for key, value in criteria.items():
            if key in criteria_list and value is True:
                category_list.append(key)

        filter_list = []
        for category in category_list:
            filter_list.append(models.Control.category == category)
        controls = (
            models.Control.query.filter(or_(*filter_list))
            .filter(models.Control.framework_id == framework.id)
            .filter(models.Control.is_custom == False)
            .all()
        )
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
            level_list = [1, 2, 3, 4, 5]
        filter_list = []
        for level in level_list:
            filter_list.append(models.Control.level == level)
        controls = (
            models.Control.query.filter(or_(*filter_list))
            .filter(models.Control.framework_id == framework.id)
            .all()
        )
    elif fw_name == "cmmc_v2":
        level_list = []
        if payload.get("level-1"):
            level_list.append(1)
        if payload.get("level-2"):
            level_list.append(2)
        if payload.get("level-3"):
            level_list.append(3)
        if not level_list:
            level_list = [1, 2, 3]
        filter_list = []
        for level in level_list:
            filter_list.append(models.Control.level == level)
        controls = (
            models.Control.query.filter(or_(*filter_list))
            .filter(models.Control.framework_id == framework.id)
            .all()
        )
    else:
        controls = (
            models.Control.query.filter(models.Control.framework_id == framework.id)
            .order_by(models.Control.id.asc())
            .all()
        )

    tenant.create_project(
        name, user.id, framework.id, description=description, controls=controls
    )
    return True


def generate_layout(dict):
    return {**current_app.config["LAYOUT"], **dict}


def get_users_from_text(text, resolve_users=False, tenant=None):
    """
    Given text with emails (@admin@example.com) in it, this function
    will return a list of found emails (or resolved user objects)
    """
    data = []
    emails = re.findall("[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    if not resolve_users:
        return emails
    for email in emails:
        if user := models.User.find_by_email(email):
            data.append(user)
    return data


def apply_rule(value, rule):
    """
    Usage:
        value = 10
        rule = {'value': 5, 'operator': 'gt'}
        print(apply_rule(value, rule))  # Output: True

        value = True
        rule = ['OR',{'value': True, 'operator': 'eq'}, {'value': True, 'operator': 'neq'}]
        print(apply_rule(value, rule))  # Output: True
    """

    def apply_comparison_rule(value, rule):
        rule_value = rule["value"]
        operator = rule["operator"]

        comparison_functions = {
            "eq": lambda x, y: x == y,
            "neq": lambda x, y: x != y,
            "contains": lambda x, y: y in x if isinstance(x, str) else False,
            "lt": lambda x, y: x < y,
            "gt": lambda x, y: x > y,
            "lte": lambda x, y: x <= y,
            "gte": lambda x, y: x >= y,
            "startswith": lambda x, y: x.startswith(y) if isinstance(x, str) else False,
            "endswith": lambda x, y: x.endswith(y) if isinstance(x, str) else False,
        }

        if operator not in comparison_functions:
            raise ValueError(f"Unsupported operator: {operator}")

        try:
            return comparison_functions[operator](value, rule_value)
        except TypeError:
            raise ValueError("Value and rule value must be comparable")

    if isinstance(rule, dict):
        return apply_comparison_rule(value, rule)
    elif isinstance(rule, list):
        if len(rule) < 2:
            raise ValueError(
                "Rule list must contain at least two elements (logical operator and comparison rule(s))"
            )

        logical_operator = rule[0].upper()

        if logical_operator == "AND":
            return all(apply_rule(value, sub_rule) for sub_rule in rule[1:])
        elif logical_operator == "OR":
            return any(apply_rule(value, sub_rule) for sub_rule in rule[1:])
        else:
            raise ValueError(f"Unsupported logical operator: {logical_operator}")
    else:
        raise ValueError(
            "Rule must be either a dictionary (comparison rule) or a list (logical operator and comparison rule(s))"
        )
