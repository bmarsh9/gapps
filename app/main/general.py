from flask import render_template, redirect, url_for, abort, flash, request, \
    current_app, jsonify
from . import main
from app.models import *
from flask_login import login_required,current_user
from app.utils.decorators import roles_required
from app.models import Role,User,Logs
from app.email import send_email

@main.route('/users', methods=['GET'])
@roles_required("admin")
def users():
    users = User.query.all()
    return render_template('management/users.html',users=users)

@main.route('/users/<int:id>/password', methods=['GET','POST'])
@login_required
def change_password(id):
    if not (user := User.query.get(id)):
        flash("User does not exist!")
        return redirect(url_for("main.users"))
    if not current_user.has_role("admin") and not current_user == user:
        flash("You do not have access to this resource","warning")
        return redirect(url_for("main.users"))
    if request.method == "POST":
        new_password = request.form["password"]
        repeat_password = request.form["password2"]
        if new_password != repeat_password:
            flash("Passwords do not match! Please try again","warning")
            return redirect(url_for("main.change_password",id=id))
        user.set_password(new_password)
        db.session.commit()
        flash("Successfully changed password of:{}".format(user.email))
        Logs.add_log("{} changed password of {}".format(current_user.email,user.email),namespace="events")
        return redirect(url_for("main.users"))
    return render_template('change_password.html',user=user)

@main.route('/users/<int:id>', methods=['GET','POST'])
@login_required
def user_profile(id):
    if not (user := User.query.get(id)):
        flash("User does not exist!")
        return redirect(url_for("main.users"))
    if not current_user.has_role("admin") and not current_user.id == id:
        flash("You do not have access to this resource","warning")
        return redirect(url_for("main.home"))
    if request.method == "POST":
        if current_user.has_role("admin"):
            roles =  request.form.getlist('roles[]')
            user.set_roles_by_name(roles)
        user.first_name = request.form["first"]
        user.last_name = request.form["last"]
        user.username = request.form["username"]
        user.is_active = True if request.form["active"] == "yes" else False
        db.session.commit()
        flash("Updated user")
        Logs.add_log("{} updated the settings of user:{}".format(current_user.email,user.email),namespace="events")
        return redirect(url_for("main.user_profile",id=user.id))
    roles = user.get_roles_for_form()
    return render_template('management/user_profile.html',user=user,roles=roles)

@main.route('/users/invite', methods=['GET','POST'])
@roles_required("admin")
def add_user():
    url = None
    if request.method == "POST":
        email = request.form["email"]
        token = User().generate_invite_token(email)
        link = "{}{}?token={}".format(request.host_url,"register",token)
        title = f"Invitation to {current_app.config['APP_NAME']}"
        content = f"You have been invited to {current_app.config['APP_NAME']}. Please click the button below to begin."
        send_email(
            'User Invitation',
            sender=current_app.config['MAIL_USERNAME'],
            recipients=[email],
            text_body=render_template(
                'email/button_template.txt',
                title=title,
                content=content,
                button_link=link
            ),
            html_body=render_template(
                'email/button_template.html',
                title=title,
                content=content,
                button_link=link
            )
        )
        flash("The user will receive an email invite.")
        Logs.add_log("{} invited {} to the platform".format(current_user.email,email),namespace="events")
        return redirect(url_for("main.add_user"))
    return render_template('management/add_user.html', url=url)
