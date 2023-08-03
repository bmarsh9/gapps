from flask import render_template, redirect, url_for, flash, \
    current_app, send_from_directory
from . import main
from app.models import *
from flask_login import current_user
from app.utils.decorators import *
from app.utils.misc import generate_layout
from app.utils.authorizer import Authorizer
import arrow
import uuid
import os


@main.route('/', methods=['GET'])
@login_required
def home():
    return render_template("home.html")

@main.route('/projects/<int:pid>/reports/<path:filename>', methods=['GET'])
@login_required
def download_report(pid, filename):
    result = Authorizer(current_user).can_user_access_project(pid)
    uploads = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])
    return send_from_directory(directory=uploads,
        path=filename, as_attachment=True)

@main.route('/questionnaires', methods=['GET'])
@login_required
def questionnaires():
    return render_template("forms/questionnaires.html")

@main.route('/questionnaires/<int:qid>', methods=['GET'])
@login_required
def view_questionnaire(qid):
    result = Authorizer(current_user).can_user_manage_questionnaire(qid)
    questionnaire = result["extra"]["questionnaire"]
    template = "forms/build_form.html"
    if questionnaire.published:
        template = "forms/review_form.html"
    return render_template(template, questionnaire=questionnaire)

@main.route('/questionnaires/<int:qid>/render', methods=['GET'])
@login_required
def render_questionnaire(qid):
    result = Authorizer(current_user).can_user_render_questionnaire(qid)
    return render_template("forms/render_form.html", questionnaire=result["extra"]["questionnaire"])

@main.route('/frameworks', methods=['GET'])
@login_required
def frameworks():
    return render_template("frameworks.html")

@main.route('/frameworks/<string:name>', methods=['GET'])
@login_required
def view_framework(name):
    if not Tenant.query.first():
        flash("Please create a tenant")
        return redirect(url_for("main.tenants"))
    framework = Framework.query.filter(func.lower(Framework.name) == func.lower(name)).first()
    return render_template("view_framework.html",
        framework=framework)

@main.route('/evidence', methods=['GET'])
@login_required
def evidence():
    return render_template("evidence.html")

@main.route('/policies', methods=['GET'])
@login_required
def policies():
    return render_template("policies.html")

@main.route('/policies/<int:pid>', methods=['GET'])
@login_required
def view_policy(pid):
    result = Authorizer(current_user).can_user_read_policy(pid)
    policy = result["extra"]["policy"]
    labels = policy.get_template_variables()
    controls = policy.tenant.controls.all()
    return render_template("view_policy.html",
        policy=policy,labels=labels,
        controls=controls)

@main.route('/controls', methods=['GET'])
@login_required
def controls():
    return render_template("controls.html")

@main.route('/projects', methods=['GET'])
@login_required
def projects():
    return render_template("projects.html")

@main.route('/projects/<int:pid>', methods=['GET'])
@login_required
def view_project(pid):
    result = Authorizer(current_user).can_user_access_project(pid)
    return render_template("view_project.html", project=result["extra"]["project"])

@main.route('/projects/<int:pid>/controls/<int:cid>', methods=['GET'])
@login_required
def view_control_in_project(pid, cid):
    result = Authorizer(current_user).can_user_read_project_control(cid)
    return render_template("view_control_in_project.html",
        project=result["extra"]["control"].project, project_control=result["extra"]["control"])

@main.route('/projects/<int:pid>/controls/<int:cid>/subcontrols/<int:sid>', methods=['GET'])
@login_required
def view_subcontrol_in_project(pid, cid, sid):
    result = Authorizer(current_user).can_user_read_project_subcontrol(sid)
    subcontrol = result["extra"]["subcontrol"]
    layout = generate_layout({"header":True,"container":False,
        "sidebar":False,"sidebar-open":False,"x-padding":"px-8","y-padding":"pt-2"
    })
    return render_template("view_subcontrol_in_project.html",
        project=subcontrol.p_control.project, project_subcontrol=subcontrol,
        layout=layout)

@main.route('/projects/<int:pid>/policies/<int:ppid>', methods=['GET'])
@login_required
def view_policy_in_project(pid, ppid):
    result = Authorizer(current_user).can_user_read_project_policy(ppid)
    policy = result["extra"]["policy"]
    labels = policy.get_template_variables()
    return render_template("view_policy_in_project.html",
        project=policy.project, policy=policy, labels=labels)

@main.route('/policies/<int:pid>/view', methods=['GET'])
@login_required
def view_rendered_policy(pid):
    result = Authorizer(current_user).can_user_read_project_policy(pid)
    project_policy = result["extra"]["policy"]
    rendered_version = int(version) if (version := request.args.get('version', None)) else len(project_policy.policy.policy_versions)
    return render_template("view_rendered_policy.html",
        policy=project_policy, content=project_policy.translate_to_html(rendered_version), rendered_version=rendered_version)

@main.route('/labels', methods=['GET'])
@login_required
def labels():
    return render_template("labels.html")

@main.route('/tags', methods=['GET'])
@login_required
def tags():
    return render_template("tags.html")
