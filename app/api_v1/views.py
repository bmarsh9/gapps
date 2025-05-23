from flask import (
    jsonify,
    request,
    current_app,
    abort,
    render_template,
    Response,
)
from . import api
from app import models, db
from flask_login import current_user
from app.utils.decorators import login_required
from app.utils.misc import project_creation, get_users_from_text
from sqlalchemy import func
from app.email import send_email
from app.utils.reports import Report
from app.utils.authorizer import Authorizer
import arrow


@api.route("/assessments/<string:qid>", methods=["GET"])
@login_required
def get_assessment(qid):
    result = Authorizer(current_user).can_user_read_assessment(qid)
    data = result["extra"]["assessment"].as_dict()
    available_guests = request.args.get("available-guests")
    if available_guests:
        data["guests"] = result["extra"]["assessment"].get_available_guests()
    return jsonify(data)


@api.route("/assessments/<string:qid>/guests")
@login_required
def get_guests_for_assessment(qid):
    result = Authorizer(current_user).can_user_read_assessment(qid)
    return jsonify(result["extra"]["assessment"].get_available_guests())


@api.route("/assessments/<string:qid>/publish", methods=["PUT"])
@login_required
def publish_assessment(qid):
    result = Authorizer(current_user).can_user_manage_assessment(qid)
    data = request.get_json()
    result["extra"]["assessment"].published = data.get("enabled")
    return jsonify({"message": "ok"})


@api.route("/assessments/<string:qid>/guests", methods=["PUT"])
@login_required
def update_assessment_guests(qid):
    result = Authorizer(current_user).can_user_manage_assessment(qid)
    data = request.get_json()
    result["extra"]["assessment"].set_guests(
        data.get("guests"), send_notification=False
    )
    return jsonify(result["extra"]["assessment"].as_dict())


@api.route("/assessments/<string:qid>/form", methods=["PUT"])
@login_required
def update_assessment_form(qid):
    result = Authorizer(current_user).can_user_manage_assessment(qid)
    data = request.get_json()
    result["extra"]["assessment"].form = data.get("form", {})
    db.session.commit()
    return jsonify(result["extra"]["assessment"].as_dict())


@api.route("/assessments/<string:qid>/submission", methods=["PUT"])
@login_required
def update_assessment_submission(qid):
    result = Authorizer(current_user).can_user_respond_to_assessment(qid)
    assessment = result["extra"]["assessment"]
    data = request.get_json()
    if submit := request.args.get("submit", False):
        assessment.submitted = True
    assessment.submission = data.get("form", {})
    db.session.commit()
    return jsonify(assessment.as_dict())


@api.route("/tenants/<string:tid>/assessments", methods=["GET"])
@login_required
def get_assessments(tid):
    result = Authorizer(current_user).can_user_access_tenant(tid)
    data = []
    for assessment in result["extra"]["tenant"].get_assessments_for_user(current_user):
        data.append(assessment.as_dict())
    return jsonify(data)


@api.route("/tenants/<string:tid>/forms", methods=["GET"])
@login_required
def get_forms(tid):
    result = Authorizer(current_user).can_user_access_tenant(tid)
    data = []

    for form in result["extra"]["tenant"].get_form_templates():
        data.append(form.as_dict())
    return jsonify(data)


@api.route("/forms/<string:id>", methods=["GET"])
@login_required
def get_form(id):
    result = Authorizer(current_user).can_user_read_form(id)
    return jsonify(result["extra"]["form"].as_dict())


@api.route("/tenants/<string:tid>/forms", methods=["POST"])
@login_required
def create_form(tid):
    result = Authorizer(current_user).can_user_manage_tenant(tid)
    data = request.get_json()
    form = result["extra"]["tenant"].create_form(
        name=data.get("name"), description=data.get("description")
    )
    return jsonify(form.as_dict())


@api.route("/tenants/<string:id>/frameworks", methods=["GET"])
@login_required
def get_frameworks(id):
    data = []
    result = Authorizer(current_user).can_user_access_tenant(id)
    for framework in result["extra"]["tenant"].frameworks.all():
        data.append(framework.as_dict())
    return jsonify(data)


@api.route("/projects/<string:id>/reports", methods=["POST"])
@login_required
def generate_report_for_project(id):
    result = Authorizer(current_user).can_user_read_project(id)
    report = Report().generate(result["extra"]["project"])
    return jsonify({"name": report})


@api.route("/projects/<string:id>/scratchpad", methods=["GET"])
@login_required
def get_scratchpad_for_project(id):
    result = Authorizer(current_user).can_user_read_project_scratchpad(id)
    return jsonify({"notes": result["extra"]["project"].notes})


@api.route("/projects/<string:id>/scratchpad", methods=["PUT"])
@login_required
def update_scratchpad_for_project(id):
    result = Authorizer(current_user).can_user_write_project_scratchpad(id)
    data = request.get_json()
    result["extra"]["project"].notes = data["data"]
    db.session.commit()
    return jsonify({"message": "ok"})


@api.route("/projects/<string:id>/comments", methods=["POST"])
@login_required
def add_comment_for_project(id):
    result = Authorizer(current_user).can_user_access_project(id)
    data = request.get_json()
    if not data.get("data"):
        return jsonify({"message": "empty comment"}), 400

    tagged_users = get_users_from_text(
        data["data"], resolve_users=True, tenant=result["extra"]["project"].tenant
    )
    comment = models.ProjectComment(message=data["data"], owner_id=current_user.id)
    result["extra"]["project"].comments.append(comment)
    db.session.commit()
    # TODO - move to background task
    # if tagged_users:
    #     link = f"{current_app.config['HOST_NAME']}projects/{id}?tab=comments"
    #     title = f"{current_app.config['APP_NAME']}: Mentioned by {current_user.get_username()}"
    #     content = f"{current_user.get_username()} mentioned you in a comment for the {result['extra']['project'].name} project. Please click the button to begin."
    #     send_email(
    #         title,
    #         recipients=[user.email for user in tagged_users],
    #         text_body=render_template(
    #             "email/basic_template.txt",
    #             title=title,
    #             content=content,
    #             button_link=link,
    #         ),
    #         html_body=render_template(
    #             "email/basic_template.html",
    #             title=title,
    #             content=content,
    #             button_link=link,
    #         ),
    #     )
    return jsonify(comment.as_dict())


@api.route("/projects/<string:pid>/comments/<string:cid>", methods=["DELETE"])
@login_required
def delete_comment_for_project(pid, cid):
    result = Authorizer(current_user).can_user_delete_project_comment(cid)
    db.session.delete(result["extra"]["comment"])
    db.session.commit()
    return jsonify({"message": "ok"})


@api.route("/projects/<string:pid>/comments", methods=["GET"])
@login_required
def get_comments_for_project(pid):
    result = Authorizer(current_user).can_user_access_project(pid)
    data = [
        comment.as_dict()
        for comment in result["extra"]["project"]
        .comments.order_by(models.ProjectComment.date_added.asc())
        .all()
    ]
    return jsonify(data)


@api.route("/projects/<string:pid>/findings", methods=["GET"])
@login_required
def get_findings_for_project(pid):
    result = Authorizer(current_user).can_user_manage_project(pid)
    data = [finding.as_dict() for finding in result["extra"]["project"].findings.all()]
    return jsonify(data)


@api.route("/projects/<string:pid>/matrix/summary", methods=["GET"])
@login_required
def get_resp_matrix_summary_for_project(pid):
    result = Authorizer(current_user).can_user_access_project(pid)
    data = {"total": 0, "owners": [], "operators": []}
    _query = result["extra"]["project"].subcontrols(as_query=True)
    data["total"] = _query.count()
    for record in (
        _query.with_entities(
            models.ProjectSubControl.operator_id,
            func.count(models.ProjectSubControl.operator_id),
        )
        .group_by(models.ProjectSubControl.operator_id)
        .all()
    ):
        if record[0]:
            if user := models.User.query.get(record[0]):
                data["operators"].append(
                    {"email": user.email, "user_id": user.id, "subcontrols": record[1]}
                )
    for record in (
        _query.with_entities(
            models.ProjectSubControl.owner_id,
            func.count(models.ProjectSubControl.owner_id),
        )
        .group_by(models.ProjectSubControl.owner_id)
        .all()
    ):
        if record[0]:
            if user := models.User.query.get(record[0]):
                data["owners"].append(
                    {"email": user.email, "user_id": user.id, "subcontrols": record[1]}
                )
    return jsonify(data)


@api.route("/projects/<string:pid>/matrix/users/<string:uid>", methods=["GET"])
@login_required
def get_resp_matrix_for_user(pid, uid):
    result = Authorizer(current_user).can_user_access_project(pid)
    if uid == 0:
        uid = None
    data = {"owner": [], "operator": []}
    _query = result["extra"]["project"].subcontrols(as_query=True)
    data["owner"] = [
        x.as_dict()
        for x in _query.filter(models.ProjectSubControl.owner_id == uid).all()
    ]
    data["operator"] = [
        x.as_dict()
        for x in _query.filter(models.ProjectSubControl.operator_id == uid).all()
    ]
    return jsonify(data)


@api.route("/projects/<string:pid>/members")
@login_required
def get_members_for_project(pid):
    result = Authorizer(current_user).can_user_access_project(pid)
    project = result["extra"]["project"]
    users = []
    for user in project.tenant.get_members():
        record = {"id": user["id"], "email": user["email"], "member": False}
        if member := project.has_member(user["email"]):
            record["member"] = True
            record["access_level"] = member.access_level
        users.append(record)
    return jsonify(users)


@api.route("/projects/<string:pid>/members", methods=["POST"])
@login_required
def add_members_for_project(pid):
    result = Authorizer(current_user).can_user_manage_project(pid)
    data = request.get_json()
    for record in data["members"]:
        if user := models.User.query.get(record["id"]):
            result["extra"]["project"].add_member(user, record.get("access_level"))
    return jsonify({"message": "ok"})


@api.route("/projects/<string:pid>/members/<string:uid>/access", methods=["PUT"])
@login_required
def update_access_level_for_user_in_project(pid, uid):
    result = Authorizer(current_user).can_user_manage_project(pid)
    data = request.get_json()
    result["extra"]["project"].update_member_access(uid, data["access_level"])
    return jsonify({"message": "ok"})


@api.route("/projects/<string:pid>/members/<string:uid>", methods=["DELETE"])
@login_required
def delete_user_from_project(pid, uid):
    result = Authorizer(current_user).can_user_manage_project(pid)
    result["extra"]["project"].remove_member(models.User.query.get(uid))
    return jsonify({"message": "ok"})


@api.route("/tenants/<string:tid>/frameworks", methods=["GET"])
@login_required
def get_frameworks_for_tenant(tid):
    result = Authorizer(current_user).can_user_read_tenant(tid)
    data = []
    for framework in result["extra"]["tenant"].frameworks.all():
        data.append(framework.as_dict())
    return jsonify(data)


@api.route("/tenants/<string:tid>/controls", methods=["POST"])
@login_required
def create_control_for_tenant(tid):
    Authorizer(current_user).can_user_manage_tenant(tid)
    payload = request.get_json()
    models.Control.create(payload, tid)
    return jsonify({"message": "ok"})


@api.route("/tenants/<string:tid>/policies", methods=["GET"])
@login_required
def get_policies_for_tenant(tid):
    result = Authorizer(current_user).can_user_read_tenant(tid)
    data = []
    for policy in result["extra"]["tenant"].policies.all():
        data.append(policy.as_dict())
    return jsonify(data)


@api.route("/tenants/<string:tid>/policies", methods=["POST"])
@login_required
def create_policy_for_tenant(tid):
    result = Authorizer(current_user).can_user_manage_tenant(tid)
    payload = request.get_json()
    policy = models.Policy(
        name=payload["name"],
        description=payload.get("description"),
        ref_code=payload.get("code"),
    )
    result["extra"]["tenant"].policies.append(policy)
    db.session.commit()
    return jsonify(policy.as_dict())


@api.route("/tenants/<string:tid>/load-frameworks", methods=["PUT"])
@login_required
def reload_tenant_frameworks(tid):
    result = Authorizer(current_user).can_user_admin_tenant(tid)
    result["extra"]["tenant"].create_base_frameworks()
    return jsonify({"message": "ok"})


@api.route("/tenants/<string:tid>/load-policies", methods=["PUT"])
@login_required
def reload_tenant_policies(tid):
    result = Authorizer(current_user).can_user_admin_tenant(tid)
    result["extra"]["tenant"].create_base_policies()
    return jsonify({"message": "ok"})


@api.route("/projects/<string:pid>", methods=["GET"])
@login_required
def get_project(pid):
    with_summary = False
    if request.args.get("summary"):
        with_summary = True
    result = Authorizer(current_user).can_user_access_project(pid)
    return jsonify(result["extra"]["project"].as_dict(with_summary=with_summary))


@api.route("/projects/<string:pid>", methods=["PUT"])
@login_required
def update_project(pid):
    result = Authorizer(current_user).can_user_manage_project(pid)
    data = request.get_json()
    if data.get("name"):
        result["extra"]["project"].name = data.get("name")
    if data.get("description"):
        result["extra"]["project"].description = data.get("description")
    db.session.commit()
    return jsonify(result["extra"]["project"].as_dict())


@api.route("/projects/<string:pid>", methods=["DELETE"])
@login_required
def delete_project(pid):
    result = Authorizer(current_user).can_user_manage_project(pid)
    db.session.delete(result["extra"]["project"])
    db.session.commit()
    return jsonify({"message": "ok"})


@api.route("/policies/<string:pid>", methods=["GET"])
@login_required
def get_policy(pid):
    result = Authorizer(current_user).can_user_read_policy(pid)
    return jsonify(result["extra"]["policy"].as_dict())


@api.route("/policies/<string:pid>", methods=["PUT"])
@login_required
def update_policy(pid):
    result = Authorizer(current_user).can_user_manage_policy(pid)
    data = request.get_json()
    policy = result["extra"]["policy"]
    policy.name = data["name"]
    policy.ref_code = data["ref_code"]
    policy.description = data["description"]
    policy.template = data["template"]
    policy.content = data["content"]
    db.session.commit()
    return jsonify(policy.as_dict())


@api.route("/frameworks/<string:fid>", methods=["GET"])
@login_required
def get_framework(fid):
    result = Authorizer(current_user).can_user_read_framework(fid)
    return jsonify(result["extra"]["framework"].as_dict())


@api.route("/evidence/<string:eid>", methods=["GET"])
@login_required
def get_evidence(eid):
    result = Authorizer(current_user).can_user_read_evidence(eid)
    return jsonify(result["extra"]["evidence"].as_dict())


@api.route("/evidence/<string:id>/file", methods=["GET"])
@login_required
def get_file_for_evidence(id):
    result = Authorizer(current_user).can_user_read_evidence(id)
    evidence = result["extra"]["evidence"]
    file_bytes = evidence.get_file(as_blob=True)
    return Response(
        file_bytes,
        mimetype="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={evidence.file_name}"},
    )


@api.route("/evidence/<string:eid>", methods=["PUT"])
@login_required
def update_evidence(eid):
    result = Authorizer(current_user).can_user_manage_evidence(eid)
    evidence = result["extra"]["evidence"]
    evidence.update(
        name=request.form.get("name"),
        description=request.form.get("description"),
        content=request.form.get("content"),
        collected_on=request.form.get("collected"),
        file=request.files.get("file"),
    )
    return jsonify(evidence.as_dict())


@api.route("/evidence/<string:eid>", methods=["DELETE"])
@login_required
def delete_evidence(eid):
    result = Authorizer(current_user).can_user_manage_evidence(eid)
    result["extra"]["evidence"].delete()
    return jsonify({"message": "ok"})


@api.route("/evidence/<string:eid>/controls", methods=["PUT"])
@login_required
def add_evidence_to_controls(eid):
    result = Authorizer(current_user).can_user_manage_evidence(eid)
    payload = request.get_json()
    result["extra"]["evidence"].associate_with_controls(payload)
    return jsonify({"message": "ok"})


@api.route("/policies/<string:pid>", methods=["DELETE"])
@login_required
def delete_policy(pid):
    result = Authorizer(current_user).can_user_manage_policy(pid)
    db.session.delete(result["extra"]["policy"])
    db.session.commit()
    return jsonify({"message": "ok"})


@api.route("/controls/<string:cid>", methods=["DELETE"])
@login_required
def delete_control(cid):
    result = Authorizer(current_user).can_user_manage_control(cid)
    result["extra"]["control"].visible = False
    db.session.commit()
    return jsonify({"message": "ok"})


@api.route("/controls/<string:cid>", methods=["GET"])
@login_required
def get_control(cid):
    result = Authorizer(current_user).can_user_read_control(cid)
    return jsonify(result["extra"]["control"].as_dict())


@api.route("/tenants/<string:tid>/projects", methods=["GET"])
@login_required
def get_projects_in_tenant(tid):
    data = []
    result = Authorizer(current_user).can_user_access_tenant(tid)
    exclude = request.args.get("exclude-timely", False)
    for record in current_user.get_projects(result["extra"]["tenant"].id):
        data.append(record.as_dict(with_summary=True, exclude_timely=exclude))
    return jsonify(data)


@api.route("/tenants/<string:tid>/projects", methods=["POST"])
@login_required
def create_project(tid):
    result = Authorizer(current_user).can_user_manage_tenant(tid)
    payload = request.get_json()
    result = project_creation(result["extra"]["tenant"], payload, current_user)
    if not result:
        return jsonify({"message": "Failed to create project"}), 400
    return jsonify({"message": "ok"})


@api.route("/projects/<string:pid>/settings", methods=["PUT"])
@login_required
def update_settings_in_project(pid):
    result = Authorizer(current_user).can_user_manage_project(pid)
    data = request.get_json()
    if data.get("name"):
        result["extra"]["project"].name = data["name"]
    if data.get("description"):
        result["extra"]["project"].description = data["description"]
    if type(data.get("auditor_enabled")) is bool:
        result["extra"]["project"].auditor_enabled = data["auditor_enabled"]
    if type(data.get("can_auditor_read_scratchpad")) is bool:
        result["extra"]["project"].can_auditor_read_scratchpad = data[
            "can_auditor_read_scratchpad"
        ]
    if type(data.get("can_auditor_write_scratchpad")) is bool:
        result["extra"]["project"].can_auditor_write_scratchpad = data[
            "can_auditor_write_scratchpad"
        ]
    if type(data.get("can_auditor_read_comments")) is bool:
        result["extra"]["project"].can_auditor_read_comments = data[
            "can_auditor_read_comments"
        ]
    if type(data.get("can_auditor_write_comments")) is bool:
        result["extra"]["project"].can_auditor_write_comments = data[
            "can_auditor_write_comments"
        ]
    if type(data.get("policies_require_cc")) is bool:
        result["extra"]["project"].policies_require_cc = data["policies_require_cc"]
    db.session.commit()
    return jsonify({"message": "ok"})


@api.route("/projects/<string:pid>/history", methods=["GET"])
@login_required
def get_project_completion_history(pid):
    result = Authorizer(current_user).can_user_access_project(pid)
    return jsonify(result["extra"]["project"].generate_last_30_days())


@api.route("/projects/<string:pid>/controls", methods=["GET"])
@login_required
def get_controls_for_project(pid):
    result = Authorizer(current_user).can_user_access_project(pid)
    data = []
    view = request.args.get("view")
    if view == "all":
        view = None
    stats = request.args.get("stats", False)
    if stats:
        stats = True

    # controls = result["extra"]["project"].get_controls()
    for control in result["extra"]["project"].controls.all():
        record = control.as_dict()
        if view:
            if view == "with-evidence" and record["progress_evidence"] > 0:
                data.append(record)
            elif view == "missing-evidence" and record["progress_evidence"] == 0:
                data.append(record)
            elif view == "not-implemented" and record["progress_implemented"] == 0:
                data.append(record)
            elif view == "implemented" and record["progress_implemented"] == 100:
                data.append(record)
            elif view == "applicable" and record["is_applicable"]:
                data.append(record)
            elif view == "not-applicable" and not record["is_applicable"]:
                data.append(record)
            elif view == "complete" and record["is_complete"]:
                data.append(record)
            elif view == "not-complete" and not record["is_complete"]:
                data.append(record)
        else:
            data.append(record)
    return jsonify(data)


@api.route("/projects/<string:pid>/risks", methods=["POST"])
@login_required
def create_risk_for_project(pid):
    result = Authorizer(current_user).can_user_access_project(pid)
    data = request.get_json()
    risk = result["extra"]["project"].create_risk(
        title=data.get("title"),
        description=data.get("description"),
        status=data.get("status"),
        risk=data.get("risk"),
        priority=data.get("priority"),
    )
    return jsonify(risk.as_dict())


@api.route("/projects/<string:pid>/risks", methods=["GET"])
@login_required
def get_risks_for_project(pid):
    result = Authorizer(current_user).can_user_access_project(pid)
    data = []
    for risk in models.RiskRegister.query.filter(
        models.RiskRegister.project_id == pid
    ).all():
        data.append(risk.as_dict())
    return jsonify(data)


@api.route("/projects/<string:pid>/risks/<string:rid>", methods=["PUT"])
@login_required
def update_risk_for_project(pid, rid):
    Authorizer(current_user).can_user_access_project(pid)
    data = request.get_json()
    risk = (
        models.RiskRegister.query.filter(models.RiskRegister.project_id == pid)
        .filter(models.RiskRegister.id == rid)
        .first_or_404()
    )
    risk.title = data.get("title")
    risk.description = data.get("description")
    risk.status = data.get("status")
    risk.risk = data.get("risk")
    risk.priority = data.get("priority")
    db.session.commit()
    return jsonify(risk.as_dict())


@api.route("/controls/<string:cid>/feedback/<string:fid>/risk", methods=["POST"])
@login_required
def create_risk_from_feedback(cid, fid):
    result = Authorizer(current_user).can_user_manage_project_control_auditor_feedback(
        cid, fid
    )
    result["extra"]["feedback"].create_risk_record()
    return jsonify(result["extra"]["feedback"].as_dict())


@api.route("/projects/<string:pid>/policies", methods=["GET"])
@login_required
def get_policies_for_project(pid):
    result = Authorizer(current_user).can_user_access_project(pid)
    data = []
    for policy in result["extra"]["project"].policies.all():
        data.append(policy.as_dict())
    return jsonify(data)


@api.route("/projects/<string:pid>/policies/<string:ppid>", methods=["GET"])
@login_required
def get_policy_for_project(pid, ppid):
    result = Authorizer(current_user).can_user_read_project_policy(ppid)
    version_id = request.args.get("version-id")
    return jsonify(result["extra"]["policy"].as_dict())


@api.route(
    "/projects/<string:pid>/policies/<string:ppid>/versions/<string:version>",
    methods=["GET"],
)
@login_required
def get_version_for_policy_in_project(pid, ppid, version):
    result = Authorizer(current_user).can_user_read_project_policy(ppid)
    return jsonify(result["extra"]["policy"].get_version(version, as_dict=True))


@api.route("/projects/<string:pid>/policies/<string:ppid>/versions", methods=["POST"])
@login_required
def create_version_for_policy_in_project(pid, ppid):
    result = Authorizer(current_user).can_user_read_project_policy(ppid)
    data = request.get_json()
    version = result["extra"]["policy"].add_version(data.get("content", ""))
    return jsonify(version.as_dict())


@api.route(
    "/projects/<string:pid>/policies/<string:ppid>/versions/<string:version>",
    methods=["DELETE"],
)
@login_required
def delete_version_for_policy_in_project(pid, ppid, version):
    result = Authorizer(current_user).can_user_read_project_policy(ppid)
    result["extra"]["policy"].delete_version(version)
    return jsonify({"message": "ok"})


@api.route(
    "/projects/<string:pid>/policies/<string:ppid>/versions/<string:version>",
    methods=["PUT"],
)
@login_required
def update_policy_version_for_project(pid, ppid, version):
    result = Authorizer(current_user).can_user_manage_project_policy(ppid)
    data = request.get_json()
    version = result["extra"]["policy"].update_version(
        version=version,
        content=data.get("content"),
        status=data.get("status"),
        publish=data.get("publish"),
    )
    return jsonify(version.as_dict())


@api.route("/projects/<string:pid>/policies/<string:ppid>", methods=["PUT"])
@login_required
def update_policy_for_project(pid, ppid):
    result = Authorizer(current_user).can_user_manage_project_policy(ppid)
    data = request.get_json()
    policy = result["extra"]["policy"].update(
        name=data.get("name"),
        description=data.get("description"),
        reviewer=data.get("reviewer"),
    )
    return jsonify(policy.as_dict())


@api.route("/projects/<string:pid>/policies/<string:ppid>", methods=["DELETE"])
@login_required
def delete_policy_for_project(pid, ppid):
    result = Authorizer(current_user).can_user_delete_policy_from_project(pid, ppid)
    result["extra"]["policy"].project.remove_policy(ppid)
    return jsonify({"message": "ok"})


@api.route(
    "/projects/<string:pid>/policies/<string:ppid>/controls/<string:cid>",
    methods=["PUT"],
)
@login_required
def add_control_to_policy(pid, ppid, cid):
    result = Authorizer(current_user).can_user_manage_project_policy(ppid)
    result["extra"]["policy"].add_control(cid)
    return jsonify({"message": "ok"})


@api.route(
    "/projects/<string:pid>/policies/<string:ppid>/controls/<string:cid>",
    methods=["DELETE"],
)
@login_required
def remove_control_from_policy(pid, ppid, cid):
    result = Authorizer(current_user).can_user_manage_project_policy(ppid)
    result["extra"]["policy"].remove_control(cid)
    return jsonify({"message": "ok"})


@api.route("/projects/<string:pid>/controls/<string:cid>", methods=["GET"])
@login_required
def get_control_for_project(pid, cid):
    result = Authorizer(current_user).can_user_read_project_control(cid)
    return jsonify(result["extra"]["control"].as_dict())


@api.route("/projects/<string:pid>/subcontrols/<string:sid>", methods=["GET"])
@login_required
def get_subcontrol_for_project(pid, sid):
    result = Authorizer(current_user).can_user_read_project_subcontrol(sid)
    return jsonify(result["extra"]["subcontrol"].as_dict(include_evidence=True))


@api.route("/projects/<string:pid>/controls/<string:cid>/subcontrols", methods=["GET"])
@login_required
def get_subcontrols_for_control_in_project(pid, cid):
    result = Authorizer(current_user).can_user_read_project_control(cid)
    data = []
    for subcontrol in (
        result["extra"]["control"]
        .subcontrols.order_by(models.ProjectSubControl.date_added.asc())
        .all()
    ):
        data.append(subcontrol.as_dict(include_evidence=True))
    return jsonify(data)


@api.route("/projects/<string:pid>/controls/<string:cid>", methods=["DELETE"])
@login_required
def remove_control_from_project(pid, cid):
    result = Authorizer(current_user).can_user_delete_control_from_project(cid, pid)
    result["extra"]["project"].remove_control(cid)
    return jsonify({"message": "ok"})


@api.route("/projects/<string:id>/policies", methods=["POST"])
@login_required
def create_policy_for_project(id):
    result = Authorizer(current_user).can_user_edit_project(id)
    data = request.get_json()
    policy = result["extra"]["project"].create_policy(
        name=data.get("name"),
        description=data.get("description"),
        template=data.get("template"),
    )
    return jsonify(policy.as_dict())


@api.route("/controls/<string:cid>/projects/<string:pid>", methods=["PUT"])
@login_required
def add_control_to_project(cid, pid):
    result = Authorizer(current_user).can_user_add_control_to_project(cid, pid)
    result["extra"]["project"].add_control(result["extra"]["control"])
    return jsonify(result["extra"]["control"].as_dict())


@api.route("/controls/<string:id>/status", methods=["PUT"])
@login_required
def update_review_status_for_control(id):
    payload = request.get_json()
    result = Authorizer(current_user).can_user_manage_project_control_status(
        id, payload.get("review-status")
    )
    result["extra"]["control"].review_status = payload["review-status"].lower()
    db.session.commit()
    return jsonify(result["extra"]["control"].as_dict())


@api.route("/project-controls/<string:cid>/subcontrols/<string:sid>", methods=["PUT"])
@login_required
def update_subcontrols_in_control_for_project(cid, sid):
    # TODO - update
    result = Authorizer(current_user).can_user_manage_project_subcontrol(sid)
    payload = request.get_json()
    subcontrol = result["extra"]["subcontrol"].update(
        applicable=payload.get("applicable"),
        implemented=payload.get("implemented"),
        notes=payload.get("notes"),
        context=payload.get("context"),
        evidence=payload.get("evidence"),
        owner_id=payload.get("owner-id"),
    )
    return jsonify(subcontrol.as_dict())


@api.route("/project-controls/<string:cid>/applicability", methods=["PUT"])
@login_required
def set_applicability_of_control_for_project(cid):
    result = Authorizer(current_user).can_user_manage_project_control(cid)
    payload = request.get_json()
    result["extra"]["control"].set_applicability(payload["applicable"])
    return jsonify(result["extra"]["control"].as_dict())


@api.route("/projects/<string:pid>/evidence/controls", methods=["GET"])
@login_required
def project_evidence_by_control(pid):
    result = Authorizer(current_user).can_user_access_project(pid)
    data = []
    if evidence := result["extra"]["project"].evidence_groupings():
        for rid, record in evidence.items():
            data.append(record)
    return jsonify(data)


@api.route("/projects/<string:pid>/controls/<string:cid>/notes", methods=["PUT"])
@login_required
def update_notes_for_control(pid, cid):
    result = Authorizer(current_user).can_user_manage_project_control_notes(cid)
    data = request.get_json()
    result["extra"]["control"].notes = data["data"]
    db.session.commit()
    return jsonify({"message": "ok"})


@api.route(
    "/projects/<string:pid>/controls/<string:cid>/auditor-notes", methods=["PUT"]
)
@login_required
def update_auditor_notes_for_control(pid, cid):
    result = Authorizer(current_user).can_user_manage_project_control_auditor_notes(cid)
    data = request.get_json()
    result["extra"]["control"].auditor_notes = data["data"]
    db.session.commit()
    return jsonify({"message": "ok"})


@api.route("/projects/<string:pid>/subcontrols/<string:sid>/notes", methods=["PUT"])
@login_required
def update_notes_for_subcontrol(pid, sid):
    result = Authorizer(current_user).can_user_manage_project_subcontrol_notes(sid)
    data = request.get_json()
    result["extra"]["subcontrol"].notes = data["data"]
    db.session.commit()
    return jsonify({"message": "ok"})


@api.route(
    "/projects/<string:pid>/subcontrols/<string:sid>/auditor-notes", methods=["PUT"]
)
@login_required
def update_auditor_notes_for_subcontrol(pid, sid):
    result = Authorizer(current_user).can_user_manage_project_subcontrol_auditor_notes(
        sid
    )
    data = request.get_json()
    result["extra"]["subcontrol"].auditor_notes = data["data"]
    db.session.commit()
    return jsonify({"message": "ok"})


@api.route("/projects/<string:pid>/subcontrols/<string:sid>/context", methods=["PUT"])
@login_required
def update_context_for_subcontrol(pid, sid):
    result = Authorizer(current_user).can_user_manage_project_subcontrol(sid)
    data = request.get_json()
    result["extra"]["subcontrol"].context = data["data"]
    db.session.commit()
    return jsonify({"message": "ok"})


@api.route("/projects/<string:pid>/controls/<string:cid>/comments", methods=["POST"])
@login_required
def add_comment_for_control(pid, cid):
    result = Authorizer(current_user).can_user_read_project_control(cid)
    data = request.get_json()
    if not data.get("data"):
        return jsonify({"message": "empty comment"}), 400
    comment = models.ControlComment(message=data["data"], owner_id=current_user.id)
    result["extra"]["control"].comments.append(comment)
    db.session.commit()
    tenant = result["extra"]["control"].project.tenant
    tagged_users = get_users_from_text(
        data["data"],
        resolve_users=True,
        tenant=tenant,
    )
    if tagged_users:
        link = f"{current_app.config['HOST_NAME']}projects/{pid}/controls/{cid}?tab=comments"
        title = f"{current_app.config['APP_NAME']}: Mentioned by {current_user.get_username()}"
        content = f"{current_user.get_username()} mentioned you in a comment for a control. Please click the button to begin."
        send_email(
            title,
            recipients=[user.email for user in tagged_users],
            text_body=render_template(
                "email/basic_template.txt",
                title=title,
                content=content,
                button_link=link,
            ),
            html_body=render_template(
                "email/basic_template.html",
                title=title,
                content=content,
                button_link=link,
            ),
        )
    tenant.add_log(
        message=f"Added comment for control:{cid}",
        namespace="comments",
        action="create",
        user_id=current_user.id,
        meta={"project_id": pid},
    )
    return jsonify(comment.as_dict())


@api.route(
    "/projects/<string:pid>/controls/<string:cid>/comments/<string:ccid>",
    methods=["DELETE"],
)
@login_required
def delete_comment_for_control(pid, cid, ccid):
    result = Authorizer(current_user).can_user_manage_project_control_comment(ccid)
    db.session.delete(result["extra"]["comment"])
    db.session.commit()
    return jsonify({"message": "ok"})


@api.route("/projects/<string:pid>/controls/<string:cid>/comments", methods=["GET"])
@login_required
def get_comments_for_control(pid, cid):
    result = Authorizer(current_user).can_user_read_project_control(cid)
    data = [
        comment.as_dict()
        for comment in result["extra"]["control"]
        .comments.order_by(models.ControlComment.date_added.asc())
        .all()
    ]
    return jsonify(data)


@api.route("/projects/<string:pid>/subcontrols/<string:sid>/comments", methods=["POST"])
@login_required
def add_comment_for_subcontrol(pid, sid):
    result = Authorizer(current_user).can_user_read_project_subcontrol(sid)
    data = request.get_json()
    if not data.get("data"):
        return jsonify({"message": "empty comment"}), 400
    comment = models.SubControlComment(message=data["data"], owner_id=current_user.id)
    result["extra"]["subcontrol"].comments.append(comment)
    db.session.commit()
    tenant = result["extra"]["subcontrol"].p_control.project.tenant
    tagged_users = get_users_from_text(
        data["data"],
        resolve_users=True,
        tenant=tenant,
    )
    if tagged_users:
        link = f"{current_app.config['HOST_NAME']}projects/{pid}/controls/{result['extra']['subcontrol'].project_control_id}/subcontrols/{sid}?tab=comments"
        title = f"{current_app.config['APP_NAME']}: Mentioned by {current_user.get_username()}"
        content = f"{current_user.get_username()} mentioned you in a comment for a subcontrol. Please click the button to begin."
        send_email(
            title,
            recipients=[user.email for user in tagged_users],
            text_body=render_template(
                "email/basic_template.txt",
                title=title,
                content=content,
                button_link=link,
            ),
            html_body=render_template(
                "email/basic_template.html",
                title=title,
                content=content,
                button_link=link,
            ),
        )
    tenant.add_log(
        message="Added comment for subcontrol:{sid}",
        namespace="comments",
        action="create",
        user_id=current_user.id,
        meta={"project_id": pid},
    )
    return jsonify(comment.as_dict())


@api.route(
    "/projects/<string:pid>/subcontrols/<string:sid>/comments/<string:cid>",
    methods=["DELETE"],
)
@login_required
def delete_comment_for_subcontrol(pid, sid, cid):
    result = Authorizer(current_user).can_user_manage_project_subcontrol_comment(cid)
    db.session.delete(result["extra"]["comment"])
    db.session.commit()
    return jsonify({"message": "ok"})


@api.route("/projects/<string:pid>/subcontrols/<string:sid>/comments", methods=["GET"])
@login_required
def get_comments_for_subcontrol(pid, sid):
    result = Authorizer(current_user).can_user_read_project_subcontrol(sid)
    data = [
        comment.as_dict()
        for comment in result["extra"]["subcontrol"]
        .comments.order_by(models.SubControlComment.date_added.asc())
        .all()
    ]
    return jsonify(data)


@api.route("/projects/<string:pid>/controls/<string:cid>/feedback", methods=["GET"])
@login_required
def get_feedback_for_control(pid, cid):
    result = Authorizer(current_user).can_user_read_project_control(cid)
    data = [
        item.as_dict()
        for item in result["extra"]["control"]
        .feedback.order_by(models.AuditorFeedback.date_added.asc())
        .all()
    ]
    return jsonify(data)


@api.route("/projects/<string:pid>/controls/<string:cid>/feedback", methods=["POST"])
@login_required
def add_feedback_for_control(pid, cid):
    result = Authorizer(current_user).can_user_add_project_control_feedback(cid)
    data = request.get_json()
    feedback = result["extra"]["control"].create_feedback(
        title=data.get("title"),
        owner_id=current_user.id,
        description=data.get("description"),
        is_complete=data.get("is_complete"),
        response=data.get("response"),
        relates_to=data.get("relates_to"),
    )
    return jsonify(feedback.as_dict())


@api.route(
    "/projects/<string:pid>/controls/<string:cid>/feedback/<string:fid>",
    methods=["PUT"],
)
@login_required
def update_feedback_for_control(pid, cid, fid):
    result = Authorizer(current_user).can_user_manage_project_control(cid)
    data = request.get_json()
    feedback = result["extra"]["control"].update_feedback(
        feedback_id=fid,
        title=data.get("title"),
        description=data.get("description"),
        is_complete=data.get("is_complete"),
        response=data.get("response"),
    )
    return jsonify(feedback.as_dict())


@api.route(
    "/projects/<string:pid>/controls/<string:cid>/feedback/<string:fid>",
    methods=["DELETE"],
)
@login_required
def delete_feedback_for_control(pid, cid, fid):
    result = Authorizer(current_user).can_user_add_project_control_feedback(cid)
    db.session.delete(result["extra"]["feedback"])
    db.session.commit()
    return jsonify({"message": "ok"})


@api.route("/projects/<string:pid>/evidence", methods=["GET"])
@login_required
def get_evidence_for_project(pid):
    result = Authorizer(current_user).can_user_read_project(pid)
    data = [
        evidence.as_dict() for evidence in result["extra"]["project"].evidence.all()
    ]
    return jsonify(data)


@api.route("/projects/<string:id>/evidence", methods=["POST"])
@login_required
def create_evidence_for_project(id):
    result = Authorizer(current_user).can_user_edit_project(id)

    evidence = result["extra"]["project"].create_evidence(
        name=request.form.get("name"),
        content=request.form.get("content"),
        description=request.form.get("description"),
        owner_id=current_user.id,
        file=request.files.get("file"),
    )
    return jsonify(evidence.as_dict())


@api.route(
    "/projects/<string:pid>/subcontrols/<string:sid>/evidence/<string:eid>/file",
    methods=["DELETE"],
)
@login_required
def remove_file_from_evidence(pid, sid, eid):
    result = Authorizer(current_user).can_user_manage_project_subcontrol(sid)
    next_check = Authorizer(current_user).can_user_manage_evidence(eid)
    next_check["extra"]["evidence"].remove_file()
    return jsonify({"message": "ok"})


@api.route("/projects/<string:pid>/subcontrols/<string:sid>/evidence", methods=["GET"])
@login_required
def get_evidence_for_subcontrol(pid, sid):
    result = Authorizer(current_user).can_user_read_project_subcontrol(sid)
    data = [
        evidence.as_dict() for evidence in result["extra"]["subcontrol"].evidence.all()
    ]
    return jsonify(data)


@api.route("/projects/<string:pid>/subcontrols/<string:sid>/evidence", methods=["POST"])
@login_required
def add_evidence_for_subcontrol(pid, sid):
    result = Authorizer(current_user).can_user_manage_project_subcontrol(sid)

    evidence = result["extra"]["subcontrol"].project.create_evidence(
        name=request.form.get("name"),
        content=request.form.get("content"),
        description=request.form.get("description"),
        owner_id=current_user.id,
        file=request.files.get("file"),
        associate_with=[sid],
    )
    return jsonify(evidence.as_dict())


@api.route("/subcontrols/<string:sid>/associate-evidence", methods=["PUT"])
@login_required
def associate_evidence_with_subcontrol(sid):
    result = Authorizer(current_user).can_user_manage_project_subcontrol(sid)
    data = request.get_json()
    result["extra"]["subcontrol"].associate_with_evidence(data["evidence"])
    return jsonify(result["extra"]["subcontrol"].as_dict())


@api.route("/subcontrols/<string:sid>/disassociate-evidence", methods=["DELETE"])
@login_required
def disassociate_evidence_with_subcontrol(sid):
    result = Authorizer(current_user).can_user_manage_project_subcontrol(sid)
    data = request.get_json()
    result["extra"]["subcontrol"].disassociate_with_evidence(data["evidence"])
    return jsonify(result["extra"]["subcontrol"].as_dict())


@api.route(
    "/projects/<string:pid>/subcontrols/<string:sid>/evidence/<string:eid>",
    methods=["DELETE"],
)
@login_required
def delete_evidence_for_subcontrol(pid, sid, eid):
    result = Authorizer(current_user).can_user_manage_project_subcontrol_evidence(
        sid, eid
    )
    result["extra"]["subcontrol"].evidence.remove(result["extra"]["evidence"])
    db.session.commit()
    return jsonify({"message": "ok"})


# TODO - complete
@api.route("/tenants/<string:tid>/vendor-files", methods=["GET"])
@login_required
def get_files_for_assessments(tid):
    result = Authorizer(current_user).can_user_access_tenant(tid)
    data = []

    # Get all assessments the user has access to
    # Get all files uploaded to those assessments
    # Return the files

    for form in result["extra"]["tenant"].get_form_templates():
        data.append(form.as_dict())
    return jsonify(data)


@api.route("/assessments/<string:id>/nudge", methods=["PUT"])
@login_required
def send_assessment_reminder_to_vendor(id):
    result = Authorizer(current_user).can_user_manage_assessment(id)
    result["extra"]["assessment"].send_reminder_email_to_vendor()
    return jsonify({"message": "ok"})


@api.route("/controls/<string:cid>/tags", methods=["PUT"])
@login_required
def add_tag_to_control(cid):
    result = Authorizer(current_user).can_user_manage_project_control(cid)
    data = request.get_json()
    for tag in data.get("tags"):
        result["extra"]["control"].add_tag(tag)
    return jsonify({"message": "ok"})


@api.route("/controls/<string:cid>/tags", methods=["DELETE"])
@login_required
def remove_tag_from_control(cid):
    result = Authorizer(current_user).can_user_manage_project_control(cid)
    data = request.get_json()
    for tag in data.get("tags"):
        result["extra"]["control"].remove_tag(tag)
    return jsonify({"message": "ok"})


@api.route("/risks/<string:id>/comments", methods=["POST"])
@login_required
def add_comment_for_risk(id):
    result = Authorizer(current_user).can_user_manage_risk(id)
    data = request.get_json()
    if not data.get("message"):
        return jsonify({"message": "empty comment"}), 400
    tenant = result["extra"]["risk"].tenant
    comment = models.RiskComment(
        message=data["message"], owner_id=current_user.id, tenant_id=tenant.id
    )
    result["extra"]["risk"].comments.append(comment)
    db.session.commit()
    tenant.add_log(
        message=f"Added comment for risk:{id}",
        namespace="comments",
        action="create",
        user_id=current_user.id,
    )
    return jsonify(comment.as_dict())


@api.route("/project-controls/<string:cid>/assignee", methods=["PUT"])
@login_required
def update_control_assignee(cid):
    result = Authorizer(current_user).can_user_manage_project_control(cid)
    data = request.get_json()
    result["extra"]["control"].set_assignee(data.get("assignee-id"))
    return jsonify(result["extra"]["control"].as_dict())


@api.route("/project-controls/<string:cid>/applicability", methods=["PUT"])
@login_required
def update_control_applicability(cid):
    result = Authorizer(current_user).can_user_manage_project_control(cid)
    data = request.get_json()
    if not data.get("applicable"):
        return jsonify({"message": "applicability must be true or false"}), 400

    if data.get("applicable"):
        result["extra"]["control"].set_as_applicable()
    else:
        result["extra"]["control"].set_as_not_applicable()
    return jsonify(result["extra"]["control"].as_dict())


@api.route("/project-controls/<string:cid>/tags", methods=["PUT"])
@login_required
def update_control_tags(cid):
    result = Authorizer(current_user).can_user_manage_project_control(cid)
    data = request.get_json()
    result["extra"]["control"].set_tags(data.get("tags"))
    return jsonify(result["extra"]["control"].as_dict())


@api.route("/projects/<string:pid>/tags", methods=["GET"])
@login_required
def get_project_tags(pid):
    result = Authorizer(current_user).can_user_access_project(pid)
    tags = result["extra"]["project"].tags.all()
    return jsonify([tag.as_dict() for tag in tags])


@api.route("/projects/<string:pid>/tags", methods=["POST"])
@login_required
def create_project_tag(pid):
    result = Authorizer(current_user).can_user_manage_project(pid)
    data = request.get_json()
    tag = result["extra"]["project"].create_tag(data["name"])
    return jsonify(tag.as_dict())


@api.route("/projects/<string:pid>/controls", methods=["POST"])
@login_required
def create_project_control(pid):
    result = Authorizer(current_user).can_user_manage_project(pid)
    data = request.get_json()
    control = result["extra"]["project"].add_custom_control(data)
    return jsonify(control.as_dict())
