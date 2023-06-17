from flask import render_template, redirect, url_for, abort, flash, request, \
    current_app, jsonify
from . import main
from app.models import *
from flask_login import current_user
from app.utils.decorators import roles_required, is_super, login_required
from app.models import Role,User,Logs
from app.email import send_email
from app.utils.authorizer import Authorizer
from app.utils import misc


@main.route('/admin/users', methods=['GET'])
@login_required
def users():
    Authorizer(current_user).can_user_manage_platform()
    tenants = Tenant.query.all()
    return render_template('management/users.html',tenants=tenants)

@main.route('/admin/settings', methods=['GET'])
@login_required
def settings():
    Authorizer(current_user).can_user_manage_platform()
    return render_template("management/settings.html")

@main.route('/jobs', methods=['GET'])
@login_required
def jobs():
    Authorizer(current_user).can_user_manage_platform()
    return render_template("jobs.html")

@main.route('/tasks', methods=['GET'])
@login_required
def tasks():
    Authorizer(current_user).can_user_manage_platform()
    return render_template("tasks.html")

@main.route('/logs', methods=['GET'])
@login_required
def logs():
    Authorizer(current_user).can_user_manage_platform()
    return render_template("logs.html")

@main.route('/users', methods=['GET'])
@login_required
def tenant_users():
    roles = Role.query.all()
    return render_template('management/tenant_users.html', roles=roles)

@main.route('/tenants', methods=['GET'])
@login_required
def tenants():
    return render_template('management/tenants.html')

@main.route('/users/<int:uid>/password', methods=['POST'])
@login_required
def change_password(uid):
    result = Authorizer(current_user).can_user_manage_user(uid)
    user = result["extra"]["user"]
    password = request.form["password"]
    password2 = request.form["password2"]
    if not misc.perform_pwd_checks(password, password_two=password2):
        flash("Password did not pass checks", "warning")
        return redirect(url_for("main.user_profile",uid=uid))
    user.set_password(password)
    db.session.commit()
    flash("Successfully changed password of:{}".format(user.email))
    Logs.add(f"{current_user.email} changed password of {user.email}",
        namespace="events")
    return redirect(url_for("main.user_profile", uid=uid))

@main.route('/users/<int:uid>', methods=['GET','POST'])
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
        Logs.add(f"{current_user.email} updated the settings of user:{user.email}",
            namespace="events")
        return redirect(url_for("main.user_profile",uid=user.id))
    return render_template('management/user_profile.html',user=user)
