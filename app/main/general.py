from flask import (
    render_template,
    redirect,
    url_for,
    abort,
    flash,
    request,
    current_app,
    jsonify,
)
from . import main
from app.models import *
from flask_login import current_user
from app.utils.decorators import login_required
from app.models import Role, Logs
from app.utils.authorizer import Authorizer
from app.utils import misc


@main.route("/admin/users", methods=["GET"])
@login_required
def users():
    Authorizer(current_user).can_user_manage_platform()
    tenants = Tenant.query.all()
    return render_template("management/users.html", tenants=tenants)


@main.route("/admin/settings", methods=["GET"])
@login_required
def settings():
    Authorizer(current_user).can_user_manage_platform()
    return render_template("management/settings.html")


@main.route("/logs", methods=["GET"])
@login_required
def logs():
    Authorizer(current_user).can_user_manage_platform()
    return render_template("logs.html")


@main.route("/tenants/<string:id>/logs", methods=["GET"])
@login_required
def get_logs_for_tenant(id):
    Authorizer(current_user).can_user_access_tenant(id)
    return render_template("tenant_logs.html")


@main.route("/users", methods=["GET"])
@login_required
def tenant_users():
    roles = Role.query.all()
    return render_template("management/tenant_users.html", roles=roles)


@main.route("/tenants", methods=["GET"])
@login_required
def tenants():
    return render_template("management/tenants.html")


@main.route("/users/<string:uid>/password", methods=["POST"])
@login_required
def change_password(uid):
    result = Authorizer(current_user).can_user_manage_user(uid)
    user = result["extra"]["user"]
    password = request.form["password"]
    password2 = request.form["password2"]
    if not misc.perform_pwd_checks(password, password_two=password2):
        flash("Password did not pass checks", "warning")
        return redirect(url_for("main.user_profile", uid=uid))
    user.set_password(password, set_pwd_change=True)
    db.session.commit()
    flash("Successfully changed password of:{}".format(user.email))
    Logs.add(
        message=f"{current_user.email} changed password of {user.email}",
        user_id=user.id,
    )
    return redirect(url_for("main.user_profile", uid=uid))


@main.route("/users/<string:uid>", methods=["GET", "POST"])
@login_required
def user_profile(uid):
    result = Authorizer(current_user).can_user_manage_user(uid)
    user = result["extra"]["user"]
    if request.method == "POST":
        user.first_name = request.form["first"]
        user.last_name = request.form["last"]
        user.username = request.form["username"]
        user.is_active = True if request.form["active"] == "yes" else False
        db.session.commit()
        flash("Updated user")
        Logs.add(
            message=f"{current_user.email} updated the settings of user:{user.email}",
            user_id=user.id,
        )
        return redirect(url_for("main.user_profile", uid=user.id))
    return render_template("management/user_profile.html", user=user)
