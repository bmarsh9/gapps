from flask import render_template, redirect, url_for, abort, flash, request, \
    current_app, jsonify
from . import main
from app.models import *
from flask_login import login_required,current_user
from app.utils.decorators import roles_required,roles_accepted
import arrow
import uuid

@main.route('/', methods=['GET'])
@login_required
def home():
    tenant = Tenant.query.first()
    return render_template("home.html",tenant=tenant)

@main.route('/controls-dashboard', methods=['GET'])
@login_required
def controls_dashboard():
    return render_template("controls_dashboard.html")

@main.route('/evidence', methods=['GET'])
@login_required
def evidence():
    projects = Project.query.all()
    evidence = Evidence.query.all()
    return render_template("evidence.html",
        evidence=evidence, projects=projects)

@main.route('/policies', methods=['GET'])
@login_required
def policies():
    projects = Project.query.all()
    policies = Policy.query.filter(Policy.visible == True).all()
    return render_template("policies.html",
        projects=projects, policies=policies)

@main.route('/policies/<int:id>', methods=['GET'])
@login_required
def view_policy(id):
    policy = Policy.query.get(id)
    labels = policy.get_template_variables()
    controls = Control.query.all()
    return render_template("view_policy.html", policy=policy,labels=labels,controls=controls)

@main.route('/controls', methods=['GET'])
@login_required
def controls():
    projects = Project.query.all()
    controls = Control.query.filter(Control.visible == True).all()
    frameworks = Framework.query.all()
    return render_template("controls.html",
        projects=projects, controls=controls,
        frameworks=frameworks)

@main.route('/controls/<int:id>', methods=['GET'])
@login_required
def view_control(id):
    control = Control.query.get(id)
    focus_areas = control.focus_areas.all()
    return render_template("view_control.html", control=control, focus_areas=focus_areas)

@main.route('/projects', methods=['GET'])
@login_required
def projects():
    projects = Project.query.all()
    frameworks = Framework.query.all()
    return render_template("projects.html", projects=projects, frameworks=frameworks)

@main.route('/projects/<int:id>', methods=['GET'])
@login_required
def view_project(id):
    project = Project.query.get(id)
    return render_template("view_project.html", project=project)

@main.route('/projects/<int:id>/settings', methods=['GET'])
@login_required
def view_settings_in_project(id):
    project = Project.query.get(id)
    return render_template("view_settings_in_project.html",
        project=project)

@main.route('/projects/<int:id>/settings', methods=['POST'])
@roles_required("admin")
def update_settings_in_project(id):
    project = Project.query.get(id)
    project.name = request.form["name"]
    project.description = request.form["description"]
    db.session.commit()
    return redirect(url_for("main.view_settings_in_project",id=project.id))

@main.route('/projects/<int:id>/controls', methods=['GET'])
@login_required
def view_controls_in_project(id):
    project = Project.query.get(id)
    controls = project.controls.all()
    return render_template("view_controls_in_project.html",
        project=project, controls=controls)

@main.route('/projects/<int:id>/controls/<int:cid>', methods=['GET'])
@login_required
def view_control_in_project(id, cid):
    project = Project.query.get(id)
    project_control = project.controls.filter(ProjectControl.id == cid).first()
    subcontrols = project_control.subcontrols.order_by(ProjectSubControl.id.desc()).all()
    evidence = Evidence.query.all()
    return render_template("view_control_in_project.html",
        project=project, project_control=project_control, subcontrols=subcontrols,
        evidence=evidence)

@main.route('/projects/<int:id>/policies', methods=['GET'])
@login_required
def view_policies_in_project(id):
    project = Project.query.get(id)
    policies = project.policies.all()
    return render_template("view_policies_in_project.html",
        project=project, policies=policies)

@main.route('/projects/<int:id>/policies/<int:cid>', methods=['GET'])
@login_required
def view_policy_in_project(id, cid):
    project = Project.query.get(id)
    policy = project.policies.filter(ProjectPolicy.id == cid).first()
    labels = policy.get_template_variables()
    return render_template("view_policy_in_project.html",
        project=project, policy=policy,labels=labels)

@main.route('/policies/external/<string:uuid>', methods=['GET'])
def view_rendered_policy(uuid):
    policy = ProjectPolicy.query.filter(ProjectPolicy.uuid == uuid).first()
    if not policy.public_viewable:
        if not current_user.is_authenticated:
            abort(404)
    tenant = Tenant.query.first()
    content = policy.translate_to_html()
    return render_template("view_rendered_policy.html", policy=policy, content=content, tenant=tenant)

@main.route('/labels', methods=['GET','POST'])
@login_required
def labels():
    if request.method == "POST":
        if not current_user.has_role("admin"):
            abort(401)
        key = request.form["key"]
        value = request.form["value"]
        pl = PolicyLabel(key=key,value=value,tenant_id=current_user.tenant_id)
        db.session.add(pl)
        db.session.commit()
        flash("Created new label", "success")
        return redirect(url_for("main.labels"))
    labels = PolicyLabel.query.all()
    return render_template("labels.html", labels=labels)

@main.route('/tags', methods=['GET','POST'])
@login_required
def tags():
    if request.method == "POST":
        if not current_user.has_role("admin"):
            abort(401)
        name = request.form["name"]
        Tag.add(current_user.tenant_id, name)
        flash("Created new tag", "success")
        return redirect(url_for("main.tags"))
    tags = Tag.query.all()
    return render_template("tags.html", tags=tags)

@main.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    tenant = Tenant.query.first()
    if request.method == "POST":
        if not current_user.has_role("admin"):
            abort(401)
        tenant.name = request.form.get("name")
        tenant.contact_email = request.form.get("email")
        db.session.commit()
        flash("Edited tenant settings","success")
        return redirect(url_for("main.settings"))
    return render_template("management/settings.html", tenant=tenant)
