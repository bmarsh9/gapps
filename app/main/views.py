from flask import (
    render_template,
    redirect,
    url_for,
    abort,
    flash,
    request,
    current_app,
    jsonify,
    session,
    send_from_directory,
)
from . import main
from flask_login import current_user
from app.utils.decorators import *
from app.utils.misc import generate_layout
from app.utils.authorizer import Authorizer


@main.route("/test", methods=["GET"])
@login_required
def test():
    if request.args.get("2"):
        return render_template("policy_center.html")
    return render_template("test.html")


@main.route("/assessments/<string:id>/manage", methods=["GET"])
@login_required
def get_assessment_for_edit_mode(id):
    result = Authorizer(current_user).can_user_manage_assessment(id)
    return render_template("kanban.html", assessment=result["extra"]["assessment"])


@main.route("/assessments/<string:id>", methods=["GET"])
@login_required
def view_assessment(id):
    """
    Endpoint is for vendors to load and respond to assessments
    See view_assessment_overview for the endpoint for InfoSec
    to review assessments
    """
    result = Authorizer(current_user).can_user_respond_to_assessment(id)
    if not result["extra"]["assessment"].is_assessment_published():
        flash("Assessment is not published", "warning")
        return redirect(url_for("main.home"))
    return render_template("kanban_view.html", assessment=result["extra"]["assessment"])


@main.route("/assessments/<string:id>/review", methods=["GET"])
@login_required
def view_assessment_overview(id):
    """
    Endpoint is for InfoSec to review assessments
    See view_assessment for the endpoint that vendors use
    to respond to assessments
    """
    result = Authorizer(current_user).can_user_manage_assessment(id)
    return render_template(
        "assessment_overview.html", assessment=result["extra"]["assessment"]
    )


@main.route("/forms/<string:id>", methods=["GET"])
@login_required
def view_form(id):
    result = Authorizer(current_user).can_user_read_form(id)
    return render_template("view_form.html", form=result["extra"]["form"])


@main.route("/", methods=["GET"])
@login_required
def home():
    return render_template("home.html")


@main.route("/projects/<string:pid>/reports/<path:filename>", methods=["GET"])
@login_required
def download_report(pid, filename):
    result = Authorizer(current_user).can_user_access_project(pid)
    return send_from_directory(
        directory=current_app.config["UPLOAD_FOLDER"], path=filename, as_attachment=True
    )


@main.route("/frameworks", methods=["GET"])
@login_required
def frameworks():
    return render_template("frameworks.html")


@main.route("/tenants/<string:id>/risk", methods=["GET"])
@login_required
def risks(id):
    Authorizer(current_user).can_user_access_risk_module(id)
    return render_template("risk_register.html")


@main.route("/assessments", methods=["GET"])
@login_required
def assessments():
    return render_template("assessments.html")


@main.route("/policies", methods=["GET"])
@login_required
def policies():
    return render_template("policies.html")


@main.route("/tenants/<string:id>/policy-center", methods=["GET"])
@login_required
def view_policy_center(id):
    Authorizer(current_user).can_user_access_tenant(id)
    policy_id = request.args.get("policy-id")
    return render_template("pc.html", tenant_id=id, policy_id=policy_id)


@main.route("/projects", methods=["GET"])
@login_required
def projects():
    return render_template("projects.html")


@main.route("/projects/<string:pid>", methods=["GET"])
@login_required
def view_project(pid):
    result = Authorizer(current_user).can_user_access_project(pid)
    return render_template("view_project.html", project=result["extra"]["project"])


@main.route("/projects/<string:pid>/controls/<string:cid>", methods=["GET"])
@login_required
def view_control_in_project(pid, cid):
    result = Authorizer(current_user).can_user_read_project_control(cid)
    return render_template(
        "view_control_in_project.html",
        project=result["extra"]["control"].project,
        project_control=result["extra"]["control"],
    )


@main.route("/projects/<string:id>/policy-center", methods=["GET"])
@login_required
def view_policy_center_for_project(id):
    result = Authorizer(current_user).can_user_read_project(id)
    policy_id = request.args.get("policy-id")
    return render_template(
        "policy_center.html", project=result["extra"]["project"], policy_id=policy_id
    )


@main.route("/labels", methods=["GET"])
@login_required
def labels():
    return render_template("labels.html")


@main.route("/tags", methods=["GET"])
@login_required
def tags():
    return render_template("tags.html")


@main.route("/vendors/<string:id>", methods=["GET"])
@login_required
def get_vendor(id):
    result = Authorizer(current_user).can_user_access_vendor(id)
    vendor = result["extra"]["vendor"]
    return render_template("view_vendor.html", vendor=vendor)


@main.route("/applications/<string:id>", methods=["GET"])
@login_required
def get_application(id):
    result = Authorizer(current_user).can_user_access_application(id)
    application = result["extra"]["application"]
    return render_template("view_application.html", application=application)


@main.route("/search-vendors", methods=["GET"])
@login_required
def search_vendor():
    # TODO - auth
    return render_template("search_vendor.html")
