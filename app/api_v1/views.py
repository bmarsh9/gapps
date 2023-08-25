from flask import jsonify, request, current_app,abort,render_template, make_response,session
from . import api
from app import models, db
from flask_login import current_user
from app.utils.decorators import login_required
from app.utils.misc import project_creation, get_users_from_text
from app.utils.notification_service import NotificationService
from sqlalchemy import func
from app.utils.reports import Report
from app.utils.authorizer import Authorizer
from app.integrations.aws.src.s3_client import S3


@api.route('/health', methods=['GET'])
def get_health():
    return jsonify({"message":"ok"})

@api.route('/session', methods=['GET'])
@login_required
def get_session():
    return jsonify(session)

@api.route('/session/<int:id>', methods=['PUT'])
@login_required
def set_session(id):
    result = Authorizer(current_user).can_user_access_tenant(id)
    session["tenant-id"] = result["extra"]["tenant"].id
    session["tenant-uuid"] = result["extra"]["tenant"].uuid
    return jsonify({"message":"ok"})

@api.route('/tenants/<int:id>', methods=['DELETE'])
@login_required
def delete_tenant(id):
    result = Authorizer(current_user).can_user_admin_tenant(id)
    db.session.delete(result["extra"]["tenant"])
    db.session.commit()
    return jsonify({"message":"ok"})

@api.route('/questionnaires/<int:qid>', methods=['GET'])
@login_required
def get_questionnaire(qid):
    result = Authorizer(current_user).can_user_read_questionnaire(qid)
    data = result["extra"]["questionnaire"].as_dict()
    available_guests = request.args.get("available-guests")
    if available_guests:
        data["guests"] = result["extra"]["questionnaire"].get_available_guests()
    return jsonify(data)

@api.route('/questionnaires/<int:qid>/guests')
@login_required
def get_guests_for_questionnaire(qid):
    result = Authorizer(current_user).can_user_read_questionnaire(qid)
    return jsonify(result["extra"]["questionnaire"].get_available_guests())

@api.route('/questionnaires/<int:qid>/publish', methods=['PUT'])
@login_required
def publish_questionnaire(qid):
    result = Authorizer(current_user).can_user_manage_questionnaire(qid)
    data = request.get_json()
    result["extra"]["questionnaire"].published = data.get("enabled")
    return jsonify({"message": "ok"})

@api.route('/questionnaires/<int:qid>/guests', methods=['PUT'])
@login_required
def update_questionnaire_guests(qid):
    result = Authorizer(current_user).can_user_manage_questionnaire(qid)
    data = request.get_json()
    result["extra"]["questionnaire"].set_guests(data.get("guests"), send_notification=True)
    return jsonify(result["extra"]["questionnaire"].as_dict())

@api.route('/questionnaires/<int:qid>/form', methods=['PUT'])
@login_required
def update_questionnaire_form(qid):
    result = Authorizer(current_user).can_user_manage_questionnaire(qid)
    data = request.get_json()
    result["extra"]["questionnaire"].form = data.get("form",{})
    db.session.commit()
    return jsonify(result["extra"]["questionnaire"].as_dict())

@api.route('/questionnaires/<int:qid>/submission', methods=['PUT'])
@login_required
def update_questionnaire_submission(qid):
    result = Authorizer(current_user).can_user_submit_questionnaire(qid)
    questionnaire = result["extra"]["questionnaire"]
    data = request.get_json()
    if submit := request.args.get("submit",False):
        questionnaire.submitted = True
    questionnaire.submission = data.get("form", {})
    db.session.commit()
    return jsonify(questionnaire.as_dict())

@api.route('/questionnaires/<int:qid>', methods=['PUT'])
@login_required
def update_questionnaire(qid):
    result = Authorizer(current_user).can_user_manage_questionnaire(qid)
    questionnaire = result["extra"]["questionnaire"]
    data = request.get_json()
    questionnaire.name = data.get("name")
    questionnaire.vendor = data.get("vendor")
    questionnaire.description = data.get("description")
    questionnaire.enabled = data.get("enabled")
    db.session.commit()
    return jsonify(questionnaire.as_dict())

@api.route('/tenants/<int:tid>/questionnaires', methods=["POST"])
@login_required
def create_questionnaire(tid):
    result = Authorizer(current_user).can_user_manage_tenant(tid)
    data = request.get_json()
    questionnaire = models.Questionnaire(name=data.get("name"),
         description=data.get("description"), vendor=data.get("vendor"),
         owner_id=current_user.id)
    if data.get("template") != "empty":
        template = models.Questionnaire.query.get(data.get("template"))
        questionnaire.form = template.form
    result["extra"]["tenant"].questionnaires.append(questionnaire)
    db.session.commit()
    return jsonify(questionnaire.as_dict())

@api.route('/tenants/<int:tid>/questionnaires', methods=['GET'])
@login_required
def get_questionnaires(tid):
    result = Authorizer(current_user).can_user_access_tenant(tid)
    data = []
    for questionnaire in result["extra"]["tenant"].get_questionnaires_for_user(current_user):
        data.append(questionnaire.as_dict())
    return jsonify(data)

@api.route('/tenants/<int:id>/frameworks', methods=['GET'])
@login_required
def get_frameworks(id):
    data = []
    print("Executed")
    result = Authorizer(current_user).can_user_access_tenant(id)
    print("Authorised")
    for framework in result["extra"]["tenant"].frameworks.all():
        data.append(framework.as_dict())
    return jsonify(data)

@api.route('/projects/<int:id>/reports', methods=['POST'])
@login_required
def generate_report_for_project(id):
    result = Authorizer(current_user).can_user_read_project(id)
    report = Report().generate(result["extra"]["project"])
    return jsonify({"name": report})

@api.route('/projects/<int:id>/scratchpad', methods=['GET'])
@login_required
def get_scratchpad_for_project(id):
    result = Authorizer(current_user).can_user_read_project_scratchpad(id)
    return jsonify({"notes": result["extra"]["project"].notes})

@api.route('/projects/<int:id>/scratchpad', methods=["PUT"])
@login_required
def update_scratchpad_for_project(id):
    result = Authorizer(current_user).can_user_write_project_scratchpad(id)
    data = request.get_json()
    result["extra"]["project"].notes = data["data"]
    db.session.commit()
    return jsonify({"message": "ok"})

@api.route('/projects/<int:id>/comments', methods=["POST"])
@login_required
def add_comment_for_project(id):
    result = Authorizer(current_user).can_user_write_project_comments(id)
    data = request.get_json()
    if not data.get("data"):
        return jsonify({"message": "empty comment"}), 400
    comment = models.ProjectComment(message=data["data"], owner_id=current_user.id)
    result["extra"]["project"].comments.append(comment)
    db.session.commit()
    NotificationService.send_email_to_users_tagged_in_project_comment(data["data"], result["extra"]["project"])
    return jsonify(comment.as_dict())

@api.route('/projects/<int:pid>/comments/<int:cid>', methods=["DELETE"])
@login_required
def delete_comment_for_project(pid, cid):
    result = Authorizer(current_user).can_user_delete_project_comment(pid, cid)
    db.session.delete(result["extra"]["comment"])
    db.session.commit()
    return jsonify({"message":"ok"})

@api.route('/projects/<int:pid>/comments', methods=['GET'])
@login_required
def get_comments_for_project(pid):
    result = Authorizer(current_user).can_user_read_project_comments(pid)
    data = [comment.as_dict() for comment in result["extra"]["project"].comments.order_by(models.ProjectComment.id.asc()).all()]
    return jsonify(data)

@api.route('/projects/<int:pid>/matrix/summary', methods=['GET'])
@login_required
def get_resp_matrix_summary_for_project(pid):
    result = Authorizer(current_user).can_user_access_project(pid)
    data = {"total": 0, "owners": [], "operators": []}
    _query = result["extra"]["project"].subcontrols(as_query=True)
    data["total"] = _query.count()
    for record in _query.with_entities(models.ProjectSubControl.operator_id, func.count(models.ProjectSubControl.operator_id)).group_by(models.ProjectSubControl.operator_id).all():
        if record[0]:
            if user := models.User.query.get(record[0]):
                data["operators"].append({"email":user.email,"user_id":user.id,"subcontrols":record[1]})
    for record in _query.with_entities(models.ProjectSubControl.owner_id, func.count(models.ProjectSubControl.owner_id)).group_by(models.ProjectSubControl.owner_id).all():
        if record[0]:
            if user := models.User.query.get(record[0]):
                data["owners"].append({"email":user.email,"user_id":user.id,"subcontrols":record[1]})
    return jsonify(data)

@api.route('/projects/<int:pid>/matrix/users/<int:uid>', methods=['GET'])
@login_required
def get_resp_matrix_for_user(pid, uid):
    result = Authorizer(current_user).can_user_access_project(pid)
    if uid == 0:
        uid = None
    data = {"owner": [], "operator": []}
    _query = result["extra"]["project"].subcontrols(as_query=True)
    data["owner"] = [x.as_dict() for x in _query.filter(models.ProjectSubControl.owner_id == uid).all()]
    data["operator"] = [x.as_dict() for x in _query.filter(models.ProjectSubControl.operator_id == uid).all()]
    return jsonify(data)

@api.route('/projects/<int:pid>/members')
@login_required
def get_members_for_project(pid):
    result = Authorizer(current_user).can_user_access_project(pid)
    project = result["extra"]["project"]
    users = []
    for user in project.tenant.users():
        record = {"id":user.id,"email":user.email,"member":False}
        if member := project.has_member(user):
            record["member"] = True
            record["access_level"] = member.access_level
        users.append(record)
    return jsonify(users)

@api.route('/projects/<int:pid>/members', methods=['POST'])
@login_required
def add_members_for_project(pid):
    result = Authorizer(current_user).can_user_manage_project(pid)
    data = request.get_json()
    for user in data["members"]:
        if user := models.User.query.get(user["id"]):
            result["extra"]["project"].add_member(user)
    
    NotificationService.send_added_to_project_notification(
        result['extra']['project'],
        [member.get("text") for member in data["members"] if member.get("text")]
    )
    return jsonify({"message": "ok"})

@api.route('/projects/<int:pid>/members/<int:uid>/access', methods=['PUT'])
@login_required
def update_access_level_for_user_in_project(pid, uid):
    result = Authorizer(current_user).can_user_manage_project(pid)
    data = request.get_json()
    member = result["extra"]["project"].update_member_access(uid, data["access_level"])

    NotificationService.send_member_project_access_level_change_notification(
        result['extra']['project'],
        member.user.email,
        data['access_level']
    )
    return jsonify({"message": "ok"})

@api.route('/projects/<int:pid>/members/<int:uid>', methods=['DELETE'])
@login_required
def delete_user_from_project(pid, uid):
    result = Authorizer(current_user).can_user_manage_project(pid)
    result["extra"]["project"].remove_member(models.User.query.get(uid))
    return jsonify({"message": "ok"})

@api.route('/tenants', methods=['GET'])
@login_required
def get_tenants():
    data = []
    for tenant in current_user.tenants():
        data.append(tenant.as_dict())
    return jsonify(data)

@api.route('/admin/users', methods=['GET'])
@login_required
def get_users():
    result = Authorizer(current_user).can_user_manage_platform()
    data = []
    for user in models.User.query.all():
        data.append(user.as_dict())
    return jsonify(data)

@api.route('/admin/users', methods=['POST'])
@login_required
def create_user():
    result = Authorizer(current_user).can_user_manage_platform()
    data = request.get_json()
    email = data.get("email")
    if not models.User.validate_email(email):
        return jsonify({"message":"invalid email"}), 400
    tenant_id = data.get("tenant_id")
    token = models.User.generate_invite_token(email, tenant_id)
    NotificationService.send_app_invitation_email(
        email,
        token
    )
    return jsonify({"message":"invited user", "url": token})

@api.route('/admin/users/<int:id>', methods=['GET'])
@login_required
def get_user(id):
    result = Authorizer(current_user).can_user_manage_platform()
    data = []
    user = models.User.query.get(id)
    return jsonify(user.as_dict())

@api.route('/tenants/<int:tid>/frameworks', methods=['GET'])
@login_required
def get_frameworks_for_tenant(tid):
    result = Authorizer(current_user).can_user_read_tenant(tid)
    data = []
    for framework in result["extra"]["tenant"].frameworks.all():
        data.append(framework.as_dict())
    return jsonify(data)

@api.route('/tenants/<int:tid>/controls', methods=['GET'])
@login_required
def get_controls_for_tenant(tid):
    result = Authorizer(current_user).can_user_read_tenant(tid)
    data = []
    for control in result["extra"]["tenant"].controls.filter(models.Control.visible == True).all():
        data.append(control.as_dict())
    return jsonify(data)

@api.route('/tenants/<int:tid>/controls', methods=['POST'])
@login_required
def create_control_for_tenant(tid):
    Authorizer(current_user).can_user_manage_tenant(tid)
    payload = request.get_json()
    models.Control.create(payload, tid)
    return jsonify({"message": "ok"})

@api.route('/tenants/<int:tid>/evidence', methods=['GET'])
@login_required
def get_evidence_for_tenant(tid):
    result = Authorizer(current_user).can_user_read_tenant(tid)
    data = []
    for evidence in result["extra"]["tenant"].evidence.all():
        data.append(evidence.as_dict())
    return jsonify(data)

@api.route('/tenants/<int:tid>/tags', methods=['GET'])
@login_required
def get_tags_for_tenant(tid):
    result = Authorizer(current_user).can_user_read_tenant(tid)
    data = []
    for tag in result["extra"]["tenant"].tags.all():
        data.append(tag.as_dict())
    return jsonify(data)

@api.route('/tenants/<int:tid>/labels', methods=['GET'])
@login_required
def get_labels_for_tenant(tid):
    result = Authorizer(current_user).can_user_read_tenant(tid)
    data = []
    for label in result["extra"]["tenant"].labels.all():
        data.append(label.as_dict())
    return jsonify(data)

@api.route('/tenants/<int:tid>/policies', methods=['GET'])
@login_required
def get_policies_for_tenant(tid):
    result = Authorizer(current_user).can_user_read_tenant(tid)
    data = []
    for policy in result["extra"]["tenant"].policies.filter(models.Policy.visible == True).all():
        data.append(policy.as_dict())
    return jsonify(data)

@api.route('/tenants/<int:tid>/policies', methods=['POST'])
@login_required
def create_policy_for_tenant(tid):
    result = Authorizer(current_user).can_user_manage_tenant(tid)
    payload = request.get_json()
    policy = models.Policy(name=payload["name"],
        description=payload.get("description"),
        ref_code=payload.get("code"))
    result["extra"]["tenant"].policies.append(policy)
    db.session.commit()
    return jsonify(policy.as_dict())

@api.route('/tenants/<int:tid>/invite-user', methods=['POST'])
@login_required
def invite_user_to_tenant(tid):
    result = Authorizer(current_user).can_user_admin_tenant(tid)
    data = request.get_json()
    email = data.get("email")
    roles = data.get("roles",[])
    if not models.User.validate_email(email):
        return jsonify({"message":"invalid email"}), 400
    if not result["extra"]["tenant"].can_we_invite_user(email):
        return jsonify({"message":"user is not in approved domains"}),403
    if user := models.User.find_by_email(email):
        result["extra"]["tenant"].add_user(user, roles=roles)
        NotificationService.send_invited_to_tenant_email(email)
    else:
        token = models.User.generate_invite_token(email, tid, attributes={"roles":roles})
        NotificationService.send_app_invitation_email(
            email,
            token
        )
    return jsonify({"url":"{}{}?token={}".format(request.host_url,"register",token) ,"email_sent":True})

@api.route('/tenants/<int:tid>', methods=['GET'])
@login_required
def get_tenant(tid):
    result = Authorizer(current_user).can_user_access_tenant(tid)
    return jsonify(result["extra"]["tenant"].as_dict())

@api.route('/tenants/<int:tid>', methods=['PUT'])
@login_required
def update_tenant(tid):
    result = Authorizer(current_user).can_user_admin_tenant(tid)
    data = request.get_json()
    result["extra"]["tenant"].contact_email = data.get("contact_email")
    result["extra"]["tenant"].name = data.get("name")
    result["extra"]["tenant"].approved_domains = data.get("approved_domains")
    result["extra"]["tenant"].magic_link_login = data.get("magic_link")
    db.session.commit()
    return jsonify(result["extra"]["tenant"].as_dict())

@api.route('/tenants', methods=['POST'])
@login_required
def add_tenant():
    result = Authorizer(current_user).can_user_create_tenants()
    data = request.get_json()
    try:
        tenant = models.Tenant.create(current_user, data.get("name"),
            data.get("contact_email"), approved_domains=data.get("approved_domains"))
        # TODO - clean up, we only need to add policies once
        for language in tenant.get_valid_framework_languages():
            tenant.create_base_policies(language)

        for framework in tenant.get_valid_frameworks():
            tenant.create_framework(framework,add_controls=True)
        return jsonify(tenant.as_dict())
    except:
        abort(500)

@api.route('/users/<int:uid>/tenants', methods=['GET'])
@login_required
def get_tenants_for_user(uid):
    result = Authorizer(current_user).can_user_read_tenants_of_user(uid)
    data = []
    for tenant in result["extra"]["user"].tenants():
        data.append({"id":tenant.id,"name":tenant.name})
    return jsonify(data)

@api.route('/tenants/<int:tid>/users', methods=['GET'])
@login_required
def get_users_for_tenant(tid):
    result = Authorizer(current_user).can_user_access_tenant(tid)
    data = []
    for user in result["extra"]["tenant"].users():
        data.append(user.as_dict(tenant=result["extra"]["tenant"]))
    return jsonify(data)

@api.route('/users/<int:uid>/tenants/<int:tid>/roles', methods=['GET'])
@login_required
def get_roles_for_user_in_tenant(uid, tid):
    result = Authorizer(current_user).can_user_access_tenant(tid)
    if not (user := models.User.query.get(uid)):
        abort(404)
    return jsonify(user.all_roles_by_tenant(result["extra"]["tenant"]))

@api.route('/users/<int:uid>', methods=['PUT'])
@login_required
def update_user(uid):
    result = Authorizer(current_user).can_user_manage_user(uid)
    data = request.get_json()
    result["extra"]["user"].username = data.get("username")
    if current_user.super and "is_active" in data:
        result["extra"]["user"].is_active = data.get("is_active")
    if current_user.super and "is_super" in data:
        result["extra"]["user"].super = data.get("is_super")
    if current_user.super and "can_user_create_tenants" in data:
        result["extra"]["user"].can_user_create_tenant = data.get("can_user_create_tenants")
    return jsonify({"message": "ok"})

@api.route('/users/<int:uid>/tenants/<int:tid>', methods=['PUT'])
@login_required
def update_user_in_tenant(uid, tid):
    result = Authorizer(current_user).can_user_manage_user_roles_in_tenant(uid, tid)
    data = request.get_json()
    if roles := data.get("roles"):
        result["extra"]["tenant"].set_roles_by_id_for_user(result["extra"]["user"], roles)
    return jsonify({"message": "ok"})

@api.route('/users/<int:uid>/tenants/<int:tid>', methods=['DELETE'])
@login_required
def delete_user_in_tenant(uid, tid):
    result = Authorizer(current_user).can_user_manage_user_roles_in_tenant(uid, tid)
    result["extra"]["tenant"].remove_user(result["extra"]["user"])
    return jsonify({"message": "ok"})

@api.route('/projects/<int:pid>', methods=['GET'])
@login_required
def project(pid):
    result = Authorizer(current_user).can_user_access_project(pid)
    review_summary = request.args.get("review-summary", False)
    if review_summary:
        review_summary = True
    return jsonify(result["extra"]["project"].as_dict(with_review_summary=review_summary))

@api.route('/projects/<int:pid>', methods=['DELETE'])
@login_required
def delete_project(pid):
    result = Authorizer(current_user).can_user_manage_project(pid)
    db.session.delete(result["extra"]["project"])
    db.session.commit()
    return jsonify({"message": "ok"})

@api.route('/policies/<int:pid>', methods=['GET'])
@login_required
def policy(pid):
    result = Authorizer(current_user).can_user_read_policy(pid)
    return jsonify(result["extra"]["policy"].as_dict())

@api.route('/policies/<int:pid>', methods=['PUT'])
@login_required
def update_policy(pid):
    result = Authorizer(current_user).can_user_manage_policy(pid)
    data = request.get_json()
    result["extra"]["policy"].name = data["name"]
    result["extra"]["policy"].ref_code = data["ref_code"]
    result["extra"]["policy"].description = data["description"]
    result["extra"]["policy"].public_viewable = data["public"]
    db.session.commit()
    return jsonify(result["extra"]["policy"].as_dict())

@api.route('/policies/<int:pid>/content', methods=['PATCH'])
@login_required
def update_policy_content(pid):
    result = Authorizer(current_user).can_user_manage_policy(pid)
    data = request.get_json()
    p_version = models.PolicyVersion(
        content=data["content"],
        version = len(result["extra"]["policy"].policy_versions) + 1,
        policy=result["extra"]["policy"]
    )
    # result["extra"]["policy"].content = data["content"]
    db.session.add(p_version)
    db.session.commit()
    return jsonify(result["extra"]["policy"].as_dict())

@api.route('/policies/<int:pid>/owner', methods=['PATCH'])
@login_required
def update_policy_owner(pid):
    result = Authorizer(current_user).can_user_set_policy_owner_or_reviewer(pid)
    data = request.get_json()
    owner_changed = result["extra"]["policy"].owner_id != data.get("owner_id")
    result["extra"]["policy"].owner_id = data.get("owner_id")
    db.session.commit()
    if owner_changed and result["extra"]["policy"].owner is not None:
        NotificationService.send_policy_owner_changed_notification(result["extra"]["policy"])
        
    return jsonify(result["extra"]["policy"].as_dict())

@api.route('/policies/<int:pid>/reviewer', methods=['PATCH'])
@login_required
def update_policy_reviewer(pid):
    result = Authorizer(current_user).can_user_set_policy_owner_or_reviewer(pid)
    data = request.get_json()
    reviewer_changed = result["extra"]["policy"].reviewer_id != data.get("reviewer_id")
    result["extra"]["policy"].reviewer_id = data.get("reviewer_id")
    db.session.commit()
    if reviewer_changed and result["extra"]["policy"].reviewer is not None:
        NotificationService.send_policy_reviewer_changed_notification(result["extra"]["policy"])
    return jsonify(result["extra"]["policy"].as_dict())

@api.route('/frameworks/<int:fid>', methods=['GET'])
@login_required
def get_framework(fid):
    result = Authorizer(current_user).can_user_read_framework(fid)
    return jsonify(result["extra"]["framework"].as_dict())

@api.route('/evidence/<int:eid>', methods=['GET'])
@login_required
def get_evidence(eid):
    result = Authorizer(current_user).can_user_read_evidence(eid)
    return jsonify(result["extra"]["evidence"].as_dict())

@api.route('/tenants/<int:tid>/evidence', methods=['POST'])
@login_required
def add_evidence_for_tenant(tid):
    result = Authorizer(current_user).can_user_manage_tenant(tid)
    evidence = models.Evidence(
        name=request.form.get("name"),
        description=request.form.get("description"),
        content=request.form.get("content"),
        owner_id=current_user.id,
        collected_on=request.form.get("collected") or None
    )
    result["extra"]["tenant"].evidence.append(evidence)
    db.session.add(evidence)
    db.session.flush()
    if files := request.files.getlist('file'):
        for file in files:
            evidence_upload = models.EvidenceUpload(
                filename = file.filename,
                evidence_id=evidence.id
            )
            db.session.add(evidence_upload)
            try:
                db.session.flush()
            except Exception:
                db.session.rollback()

            S3().upload_file_obj(file, str(evidence_upload.upload_link))
    db.session.commit()
    return jsonify(evidence.as_dict())

@api.route('/evidence/<int:eid>', methods=['PUT'])
@login_required
def update_evidence(eid):
    result = Authorizer(current_user).can_user_manage_evidence(eid)
    result["extra"]["evidence"].name = request.form.get("name"),
    result["extra"]["evidence"].description = request.form.get("description")
    result["extra"]["evidence"].content = request.form.get("content")
    result["extra"]["evidence"].collected_on = request.form.get("collected")
    db.session.flush()
    if files := request.files.getlist('file'):
        for file in files:
            evidence_upload = models.EvidenceUpload(
                filename = file.filename,
                evidence_id=eid
            )
            db.session.add(evidence_upload)
            try:
                db.session.flush()
            except Exception:
                db.session.rollback()
                
            S3().upload_file_obj(file, str(evidence_upload.upload_link))
    db.session.commit()
                
    return jsonify(result["extra"]["evidence"].as_dict())

@api.route('/evidence/<int:eid>', methods=['DELETE'])
@login_required
def delete_evidence(eid):
    result = Authorizer(current_user).can_user_manage_evidence(eid)
    db.session.delete(result["extra"]["evidence"])
    db.session.commit()
    return jsonify({"message": "ok"})

@api.route('/evidence/<int:eid>/controls', methods=['PUT'])
@login_required
def add_evidence_to_controls(eid):
    result = Authorizer(current_user).can_user_manage_evidence(eid)
    payload = request.get_json()
    result["extra"]["evidence"].associate_with_controls(payload)
    return jsonify({"message": "ok"})

@api.route('/policies/<int:pid>', methods=['DELETE'])
@login_required
def delete_policy(pid):
    result = Authorizer(current_user).can_user_manage_policy(pid)
    result["extra"]["policy"].visible = False
    db.session.commit()
    return jsonify({"message": "ok"})

@api.route('/controls/<int:cid>', methods=['DELETE'])
@login_required
def delete_control(cid):
    result = Authorizer(current_user).can_user_manage_control(cid)
    result["extra"]["control"].visible = False
    db.session.commit()
    return jsonify({"message": "ok"})

@api.route('/controls/<int:cid>', methods=['GET'])
@login_required
def control(cid):
    result = Authorizer(current_user).can_user_read_control(cid)
    return jsonify(result["extra"]["control"].as_dict())

@api.route('/tenants/<int:tid>/projects', methods=['GET'])
@login_required
def get_projects_in_tenant(tid):
    data = []
    result = Authorizer(current_user).can_user_access_tenant(tid)
    for record in current_user.get_projects_with_access_in_tenant(result["extra"]["tenant"]):
        data.append(record.as_dict(with_review_summary=True))
    return jsonify(data)

@api.route('/tenants/<int:tid>/projects', methods=['POST'])
@login_required
def create_project(tid):
    result = Authorizer(current_user).can_user_manage_tenant(tid)
    payload = request.get_json()
    result = project_creation(result["extra"]["tenant"], payload, current_user)
    if not result:
        return jsonify({"message": "failed to create project"}), 400
    return jsonify({"message": "ok"})

@api.route('/projects/<int:pid>/settings', methods=['POST'])
@login_required
def update_settings_in_project(pid):
    result = Authorizer(current_user).can_user_manage_project(pid)
    data = request.get_json()
    if data.get("name"):
        result["extra"]["project"].name = data["name"]
    if data.get("description"):
        result["extra"]["project"].description = data["description"]
    if type(data.get("can_auditor_read_scratchpad")) is bool:
        result["extra"]["project"].can_auditor_read_scratchpad = data["can_auditor_read_scratchpad"]
    if type(data.get("can_auditor_write_scratchpad")) is bool:
        result["extra"]["project"].can_auditor_write_scratchpad = data["can_auditor_write_scratchpad"]
    if type(data.get("can_auditor_read_comments")) is bool:
        result["extra"]["project"].can_auditor_read_comments = data["can_auditor_read_comments"]
    if type(data.get("can_auditor_write_comments")) is bool:
        result["extra"]["project"].can_auditor_write_comments = data["can_auditor_write_comments"]
    db.session.commit()
    return jsonify({"message": "ok"})

@api.route('/projects/<int:pid>/controls', methods=['GET'])
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
    for control in result["extra"]["project"].controls.all():
        record = control.as_dict(include_subcontrols=True, stats=stats)
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

@api.route('/projects/<int:pid>/policies', methods=['GET'])
@login_required
def get_policies_for_project(pid):
    result = Authorizer(current_user).can_user_access_project(pid)
    data = []
    for policy in result["extra"]["project"].policies.all():
        data.append(policy.as_dict())
    return jsonify(data)

@api.route('/projects/<int:pid>/policies/<int:ppid>', methods=['GET'])
@login_required
def get_policy_for_project(pid, ppid):
    result = Authorizer(current_user).can_user_read_project_policy(ppid)
    return jsonify(result["extra"]["policy"].as_dict())

@api.route('/projects/<int:pid>/policies/<int:ppid>', methods=['PUT'])
@login_required
def update_policy_for_project(pid, ppid):
    result = Authorizer(current_user).can_user_manage_project_policy(ppid)
    data = request.get_json()
    for key in ["content", "viewable", "owner_id", "reviewer_id"]:
        if key in data:
            setattr(result["extra"]["policy"], key, data[key])
    db.session.commit()
    return jsonify(result["extra"]["policy"].as_dict())

@api.route('/projects/<int:pid>/policies/<int:ppid>', methods=['DELETE'])
@login_required
def delete_policy_for_project(pid, ppid):
    result = Authorizer(current_user).can_user_delete_policy_from_project(pid, ppid)
    result["extra"]["policy"].project.remove_policy(ppid)
    return jsonify({"message": "ok"})

@api.route('/policies/<int:pid>/controls/<int:cid>', methods=['PUT'])
@login_required
def update_controls_for_policy(pid, cid):
    result = Authorizer(current_user).can_user_manage_project_policy(pid)
    result["extra"]["policy"].add_control(cid)
    return jsonify({"message": "ok"})

@api.route('/policies/<int:pid>/controls/<int:cid>', methods=['DELETE'])
@login_required
def delete_controls_for_policy(pid, cid):
    result = Authorizer(current_user).can_user_manage_project_policy(pid)
    if control := result["extra"]["policy"].has_control(cid):
        db.session.delete(control)
        db.session.commit()
    return jsonify({"message": "ok"})

@api.route('/projects/<int:pid>/policies/<int:ppid>/controls/<int:cid>', methods=['PUT'])
@login_required
def update_policy_controls_for_project(pid, ppid, cid):
    result = Authorizer(current_user).can_user_manage_project_policy(ppid)
    result["extra"]["policy"].add_control(cid)
    return jsonify({"message": "ok"})

@api.route('/projects/<int:pid>/policies/<int:ppid>/controls/<int:cid>', methods=['DELETE'])
@login_required
def delete_policy_controls_for_project(pid, ppid, cid):
    result = Authorizer(current_user).can_user_manage_project_policy(ppid)
    if control := result["extra"]["policy"].has_control(cid):
        db.session.delete(control)
        db.session.commit()
    return jsonify({"message": "ok"})

@api.route('/projects/<int:pid>/controls/<int:cid>', methods=['GET'])
@login_required
def get_control_for_project(pid, cid):
    result = Authorizer(current_user).can_user_read_project_control(cid)
    return jsonify(result["extra"]["control"].as_dict())

@api.route('/projects/<int:pid>/controls/<int:cid>/subcontrols', methods=['GET'])
@login_required
def get_subcontrols_for_control_in_project(pid, cid):
    result = Authorizer(current_user).can_user_read_project_control(cid)
    data = []
    for subcontrol in result["extra"]["control"].subcontrols.order_by(models.ProjectSubControl.id.asc()).all():
        data.append(subcontrol.as_dict(include_evidence=True))
    return jsonify(data)

@api.route('/projects/<int:pid>/controls/<int:cid>', methods=['DELETE'])
@login_required
def remove_control_from_project(pid, cid):
    result = Authorizer(current_user).can_user_delete_control_from_project(cid, pid)
    result["extra"]["project"].remove_control(cid)
    return jsonify({"message": "ok"})

@api.route('/policies/<int:pid>/projects/<int:ppid>', methods=['PUT'])
@login_required
def add_policy_to_project(pid, ppid):
    result = Authorizer(current_user).can_user_add_policy_to_project(pid, ppid)
    result["extra"]["project"].add_policy(result["extra"]["policy"])
    return jsonify(result["extra"]["policy"].as_dict())

@api.route('/controls/<int:cid>/projects/<int:pid>', methods=['PUT'])
@login_required
def add_control_to_project(cid, pid):
    result = Authorizer(current_user).can_user_add_control_to_project(cid, pid)
    result["extra"]["project"].add_control(result["extra"]["control"])
    return jsonify(result["extra"]["control"].as_dict())

@api.route('/subcontrols/<int:sid>/status', methods=['PUT'])
@login_required
def update_review_status_for_subcontrol(sid):
    payload = request.get_json()
    result = Authorizer(current_user).can_user_manage_project_subcontrol_status(sid, payload.get("review-status"))
    result["extra"]["subcontrol"].review_status = payload["review-status"].lower()
    db.session.commit()
    NotificationService.send_subcontrol_status_change_notification(result["extra"]["subcontrol"])
    return jsonify({"message": "ok"})

@api.route('/project-controls/<int:cid>/subcontrols/<int:sid>', methods=['PUT'])
@login_required
def update_subcontrols_in_control_for_project(cid, sid):
    result = Authorizer(current_user).can_user_manage_project_subcontrol(sid)
    payload = request.get_json()
    owner_changed = result["extra"]["subcontrol"].owner_id != payload.get("owner-id")
    operator_changed = result["extra"]["subcontrol"].operator_id != payload.get("operator-id")
    if payload.get("applicable") != None:
        result["extra"]["subcontrol"].is_applicable = payload.get("applicable")
    if payload.get("implemented") != None:
        result["extra"]["subcontrol"].implemented = payload.get("implemented")
    if notes := payload.get("notes"):
        result["extra"]["subcontrol"].notes = notes
    if feedback := payload.get("feedback"):
        result["extra"]["subcontrol"].auditor_feedback = feedback
    if evidence := payload.get("evidence"):
        result["extra"]["subcontrol"].set_evidence(evidence)
    if payload.get("owner-id") or payload.get("owner-id") == None:
        result["extra"]["subcontrol"].owner_id = payload.get("owner-id")
    if payload.get("operator-id") or payload.get("operator-id") == None:
        result["extra"]["subcontrol"].operator_id = payload.get("operator-id")
    db.session.commit()
    if owner_changed and result["extra"]["subcontrol"].owner is not None:
        NotificationService.send_subcontrol_owner_changed_notification(result["extra"]["subcontrol"])

    if operator_changed and result["extra"]["subcontrol"].operator is not None:
        NotificationService.send_subcontrol_operator_changed_notification(result["extra"]["subcontrol"])
    return jsonify({"message": "ok"})

@api.route('/project-controls/<int:cid>/applicability', methods=['PUT'])
@login_required
def set_applicability_of_control_for_project(cid):
    result = Authorizer(current_user).can_user_manage_project_control(cid)
    payload = request.get_json()
    result["extra"]["control"].set_applicability(payload["applicable"])
    return jsonify({"message": "ok"})

@api.route('/tenants/<int:tid>/tags/<int:ttid>', methods=['DELETE'])
@login_required
def delete_tag_for_tenant(tid, ttid):
    result = Authorizer(current_user).can_user_manage_tag(tid)
    db.session.delete(result["extra"]["tag"])
    db.session.commit()
    return jsonify({"message": "ok"})

@api.route('/tenants/<int:tid>/tags', methods=['POST'])
@login_required
def create_tag_for_tenant(tid):
    result = Authorizer(current_user).can_user_manage_tenant(tid)
    data = request.get_json()
    models.Tag.add(current_user.id, data.get("name"), result["extra"]["tenant"])
    return jsonify({"message": "ok"})

@api.route('/tenants/<int:tid>/labels', methods=['POST'])
@login_required
def create_label_for_tenant(tid):
    result = Authorizer(current_user).can_user_manage_tenant(tid)
    data = request.get_json()
    result["extra"]["tenant"].labels.append(
        models.PolicyLabel(key=data.get("key"),
            value=data.get("value"),
            owner_id=current_user.id)
    )
    db.session.commit()
    return jsonify({"message": "ok"})

@api.route('/tenants/<int:tid>/labels/<int:lid>', methods=['DELETE'])
@login_required
def delete_label_for_tenant(tid, lid):
    result = Authorizer(current_user).can_user_manage_policy_label(lid)
    db.session.delete(result["extra"]["label"])
    db.session.commit()
    return jsonify({"message": "ok"})

@api.route('/projects/<int:pid>/evidence/controls', methods=['GET'])
@login_required
def project_evidence_by_control(pid):
    result = Authorizer(current_user).can_user_access_project(pid)
    data = []
    if evidence := result["extra"]["project"].evidence_groupings():
        for rid, record in evidence.items():
            data.append(record)
    return jsonify(data)

@api.route('/logs')
@login_required
def get_logs():
    result = Authorizer(current_user).can_user_manage_platform()
    data = [x.as_dict() for x in models.Logs.query.limit(500)]
    return jsonify(data)

@api.route('/projects/<int:pid>/controls/<int:cid>/notes', methods=["PUT"])
@login_required
def update_notes_for_control(pid, cid):
    result = Authorizer(current_user).can_user_manage_project_control_notes(cid)
    data = request.get_json()
    result["extra"]["control"].notes = data["data"]
    db.session.commit()
    return jsonify({"message": "ok"})

@api.route('/projects/<int:pid>/controls/<int:cid>/auditor-notes', methods=["PUT"])
@login_required
def update_auditor_notes_for_control(pid, cid):
    result = Authorizer(current_user).can_user_manage_project_control_auditor_notes(cid)
    data = request.get_json()
    result["extra"]["control"].auditor_notes = data["data"]
    db.session.commit()
    return jsonify({"message": "ok"})

@api.route('/projects/<int:pid>/subcontrols/<int:sid>/notes', methods=["PUT"])
@login_required
def update_notes_for_subcontrol(pid, sid):
    result = Authorizer(current_user).can_user_manage_project_subcontrol_notes(sid)
    data = request.get_json()
    result["extra"]["subcontrol"].notes = data["data"]
    db.session.commit()
    return jsonify({"message":"ok"})

@api.route('/projects/<int:pid>/subcontrols/<int:sid>/auditor-notes', methods=["PUT"])
@login_required
def update_auditor_notes_for_subcontrol(pid, sid):
    result = Authorizer(current_user).can_user_manage_project_subcontrol_auditor_notes(sid)
    data = request.get_json()
    result["extra"]["subcontrol"].auditor_notes = data["data"]
    db.session.commit()
    return jsonify({"message":"ok"})

@api.route('/projects/<int:pid>/subcontrols/<int:sid>/context', methods=["PUT"])
@login_required
def update_context_for_subcontrol(pid, sid):
    result = Authorizer(current_user).can_user_manage_project_subcontrol(sid)
    data = request.get_json()
    result["extra"]["subcontrol"].context = data["data"]
    db.session.commit()
    return jsonify({"message":"ok"})

@api.route('/projects/<int:pid>/controls/<int:cid>/comments', methods=["POST"])
@login_required
def add_comment_for_control(pid, cid):
    result = Authorizer(current_user).can_user_manage_project_control(cid)
    data = request.get_json()
    if not data.get("data"):
        return jsonify({"message": "empty comment"}), 400
    comment = models.ControlComment(message=data["data"], owner_id=current_user.id)
    result["extra"]["control"].comments.append(comment)
    db.session.commit()
    tagged_users = get_users_from_text(data["data"], resolve_users=True, tenant=result["extra"]["control"].project.tenant)
    if tagged_users:
        NotificationService.send_tagged_in_control_comment_notification(
            result["extra"]["control"],
            [user.email for user in tagged_users]
        )
    models.Logs.add("Added comment for control",
        namespace=f"projects:{id}.controls:{result['extra']['control'].id}.comments:{comment.id}",
        action="create",
        user_id=current_user.id
    )
    return jsonify(comment.as_dict())

@api.route('/projects/<int:pid>/controls/<int:cid>/comments/<int:ccid>', methods=["DELETE"])
@login_required
def delete_comment_for_control(pid, cid, ccid):
    result = Authorizer(current_user).can_user_manage_project_control_comment(cid)
    db.session.delete(result["extra"]["comment"])
    db.session.commit()
    return jsonify({"message":"ok"})

@api.route('/projects/<int:pid>/controls/<int:cid>/comments', methods=["GET"])
@login_required
def get_comments_for_control(pid, cid):
    result = Authorizer(current_user).can_user_read_project_control(cid)
    data = [comment.as_dict() for comment in result["extra"]["control"].comments.order_by(models.ControlComment.id.asc()).all()]
    return jsonify(data)

@api.route('/projects/<int:pid>/subcontrols/<int:sid>/comments', methods=["POST"])
@login_required
def add_comment_for_subcontrol(pid, sid):
    result = Authorizer(current_user).can_user_read_project_subcontrol(sid)
    data = request.get_json()
    if not data.get("data"):
        return jsonify({"message": "empty comment"}), 400
    comment = models.SubControlComment(message=data["data"], owner_id=current_user.id)
    result["extra"]["subcontrol"].comments.append(comment)
    db.session.commit()
    tagged_users = get_users_from_text(data["data"], resolve_users=True, tenant=result["extra"]["subcontrol"].p_control.project.tenant)
    if tagged_users:
        NotificationService.send_tagged_in_subcontrol_comment_notification(
            result["extra"]["subcontrol"],
            [user.email for user in tagged_users],
        )
    models.Logs.add("Added comment for subcontrol",
        namespace=f"projects:{id}.subcontrols:{result['extra']['subcontrol'].id}.comments:{comment.id}",
        action="create",
        user_id=current_user.id
    )
    return jsonify(comment.as_dict())

@api.route('/projects/<int:pid>/subcontrols/<int:sid>/comments/<int:cid>', methods=["DELETE"])
@login_required
def delete_comment_for_subcontrol(pid, sid, cid):
    result = Authorizer(current_user).can_user_manage_project_subcontrol_comment(cid)
    db.session.delete(result["extra"]["comment"])
    db.session.commit()
    return jsonify({"message": "ok"})

@api.route('/projects/<int:pid>/subcontrols/<int:sid>/comments', methods=["GET"])
@login_required
def get_comments_for_subcontrol(pid, sid):
    result = Authorizer(current_user).can_user_read_project_subcontrol(sid)
    data = [comment.as_dict() for comment in result["extra"]["subcontrol"].comments.order_by(models.SubControlComment.id.asc()).all()]
    return jsonify(data)

@api.route('/projects/<int:pid>/subcontrols/<int:sid>/feedback', methods=["GET"])
@login_required
def get_feedback_for_subcontrol(pid, sid):
    result = Authorizer(current_user).can_user_read_project_subcontrol(sid)
    data = [item.as_dict() for item in result["extra"]["subcontrol"].feedback.order_by(models.AuditorFeedback.id.asc()).all()]
    return jsonify(data)

@api.route('/projects/<int:pid>/subcontrols/<int:sid>/feedback', methods=["POST"])
@login_required
def add_feedback_for_subcontrol(pid, sid):
    result = Authorizer(current_user).can_user_add_project_subcontrol_feedback(sid)
    data = request.get_json()
    feedback = models.AuditorFeedback(owner_id=current_user.id,
        title=data["title"],description=data["description"],
        is_complete=data["is_complete"],auditor_complete=data["auditor_complete"])
    result["extra"]["subcontrol"].feedback.append(feedback)
    db.session.commit()
    return jsonify(feedback.as_dict())

@api.route('/projects/<int:pid>/subcontrols/<int:sid>/feedback/<int:fid>', methods=["PUT"])
@login_required
def update_feedback_for_subcontrol(pid, sid, fid):
    result = Authorizer(current_user).can_user_read_project_subcontrol(sid)

    data = request.get_json()
    control = models.ProjectSubControl.query.get(sid)
    feedback = models.AuditorFeedback.query.get(fid)
    feedback.title = data["title"]
    feedback.description = data["description"]
    feedback.is_complete = data["is_complete"]
    feedback.auditor_complete = data["auditor_complete"]
    db.session.commit()
    return jsonify(feedback.as_dict())

@api.route('/projects/<int:pid>/subcontrols/<int:sid>/feedback/<int:fid>', methods=["DELETE"])
@login_required
def delete_feedback_for_subcontrol(pid, sid, fid):
    result = Authorizer(current_user).can_user_manage_project_subcontrol_feedback(fid)
    db.session.delete(result["extra"]["feedback"])
    db.session.commit()
    return jsonify({"message":"ok"})

@api.route('/projects/<int:pid>/subcontrols/<int:sid>/evidence', methods=["GET"])
@login_required
def get_evidence_for_subcontrol(pid, sid):
    result = Authorizer(current_user).can_user_read_project_subcontrol(sid)
    data = [evidence.as_dict() for evidence in result["extra"]["subcontrol"].evidence.all()]
    return jsonify(data)

@api.route('/projects/<int:pid>/subcontrols/<int:sid>/evidence', methods=["POST"])
@login_required
def add_evidence_for_subcontrol(pid, sid):
    result = Authorizer(current_user).can_user_manage_project_subcontrol(sid)
    data = request.get_json()
    evidence = models.Evidence(name=data["name"],
        content=data["content"],description=data["description"],
        tenant_id=result["extra"]["subcontrol"].p_control.project.tenant_id,
        owner_id=current_user.id)
    result["extra"]["subcontrol"].evidence.append(evidence)
    db.session.commit()
    return jsonify(evidence.as_dict())

@api.route('/projects/<int:pid>/subcontrols/<int:sid>/evidence/<int:eid>', methods=["DELETE"])
@login_required
def delete_evidence_for_subcontrol(pid, sid, eid):
    result = Authorizer(current_user).can_user_manage_project_subcontrol_evidence(sid, eid)
    result["extra"]["subcontrol"].evidence.remove(result["extra"]["evidence"])
    db.session.commit()
    return jsonify({"message": "ok"})

@api.route("/evidence_upload/<uuid:upload_id>", methods=["GET"])
def get_evidence_upload(upload_id):
    evidence_upload = models.EvidenceUpload.query.filter(models.EvidenceUpload.upload_link == str(upload_id)).one_or_none()
    result = Authorizer(current_user).can_user_read_evidence(evidence_upload.evidence_id)
    evidence = result["extra"]["evidence"]
    image_url = S3().generate_presigned_url(current_app.config['EVIDENCE_BUCKET'], str(upload_id))

    return render_template("evidence_upload.html", image_url=image_url, evidence_name=evidence.name)