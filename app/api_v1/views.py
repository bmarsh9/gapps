from typing import List, Optional

from flask import abort, current_app, jsonify, render_template, request, session
from flask_login import current_user

from . import api
from app import models, db
from app.integrations.aws.src.s3_client import S3
from app.service import (
    AuthorizationService,
    EvidenceService,
    ProjectService,
    ProjectCommentService,
    ProjectControlService,
    ProjectSubControlService,
    ProjectPolicyService,
    ProjectReportService,
    ProjectMemberService,
    UserService
)
from app.utils.authorizer import Authorizer
from app.utils.custom_errors import ValidationError
from app.utils.decorators import login_required
from app.utils.enums import (
    FileType,
    ProjectControlsFilter,
    ProjectRoles,
    ProjectSubControlsFilter
)
from app.utils.misc import (
    get_content_type_for_extension,
    get_file_type_by_extensions,
    get_users_from_text,
    project_creation
)
from app.utils.notification_service import NotificationService

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

@api.route('/languages', methods=['GET'])
@login_required
def get_available_languages():
    return jsonify({"languages": current_app.config['LANGUAGES']})

@api.route('/locale', methods=['PUT'])
@login_required
def set_user_locale():
    data = request.get_json()
    new_locale = data.get("locale")
    UserService.update_user_locale(new_locale)
    return jsonify({"message": "ok"})

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

@api.route('/tenants/<int:tenant_id>/projects', methods=['GET'])
@login_required
def get_projects_in_tenant(tenant_id: int):
    AuthorizationService(current_user).can_user_access_tenant(tenant_id)
    projects: List[dict] = ProjectService.get_tenant_project_summaries(tenant_id)
    return jsonify(projects)

@api.route('/projects/<int:project_id>', methods=['GET'])
@login_required
def get_project_summary(project_id: int):
    AuthorizationService(current_user).can_user_access_project(project_id)
    result = ProjectService.get_project_summary(project_id)
    return jsonify(result)

@api.route('/projects/<int:project_id>/controls', methods=['GET'])
@login_required
def get_controls_for_project(project_id: int):
    AuthorizationService(current_user).can_user_view_project_controls(project_id)
    filter = request.args.get("filter")
    extra_filter = filter if filter is not None and filter in ProjectControlsFilter.values() else None
    result = ProjectControlService.get_project_control_summary(project_id, extra_filter)
    return jsonify(result)

@api.route('/projects/<int:project_id>/subcontrols', methods=['GET'])
@login_required
def get_subcontrols_for_project(project_id: int):
    AuthorizationService(current_user).can_user_view_project_subcontrols(project_id)
    
    filter = request.args.get("filter")
    by_owner = request.args.get("owner")
    by_operator = request.args.get("operator")

    extra_filters = {}
    if filter and filter in ProjectSubControlsFilter.values():
        extra_filters['filter'] = filter
    if by_owner:
        extra_filters['owner'] = by_owner
    if by_operator:
        extra_filters['operator'] = by_operator
        
    result: List[dict] = ProjectSubControlService.get_project_subcontrol_summary(project_id, extra_filters)
    return jsonify(result)

@api.route('/projects/<int:project_id>/policies', methods=['GET'])
@login_required
def get_policies_for_project(project_id: int):
    AuthorizationService(current_user).can_user_view_project_policies(project_id)
    result = ProjectPolicyService.get_project_policies_summary(project_id)
    return jsonify(result)

@api.route('/projects/<int:project_id>/evidence', methods=['GET'])
@login_required
def get_project_evidence_summary(project_id: int):
    AuthorizationService(current_user).can_user_view_project_evidence(project_id)
    result = EvidenceService.get_project_evidence_summary(project_id)
    return jsonify(result)

@api.route('/projects/<int:project_id>/matrix', methods=['GET'])
@login_required
def get_resp_matrix_summary_for_project(project_id: int):
    AuthorizationService(current_user).can_user_view_project_responsibility_matrix(project_id)
    result = ProjectMemberService.get_project_responsibility_matrix(project_id)
    return jsonify(result)

@api.route('/projects/<int:project_id>/scratchpad', methods=['GET'])
@login_required
def get_scratchpad_for_project(project_id: int):
    AuthorizationService(current_user).can_user_view_project_notes(project_id)
    result = ProjectService.get_project_notes(project_id)
    return jsonify({'notes': result})

@api.route('/projects/<int:project_id>/scratchpad', methods=['PUT'])
@login_required
def update_scratchpad_for_project(project_id: int):
    AuthorizationService(current_user).can_user_update_project_notes(project_id)
    payload = request.get_json()
    ProjectService.update_project_notes(project_id, payload['notes'])
    return jsonify({'message': 'ok'})

@api.route('/projects/<int:project_id>/comments', methods=['GET'])
@login_required
def get_comments_for_project(project_id: int):
    AuthorizationService(current_user).can_user_view_project_comments(project_id)
    result = ProjectCommentService.get_project_comments(project_id)
    return jsonify(result)

@api.route('/projects/<int:project_id>/comments', methods=['POST'])
@login_required
def add_comment_for_project(project_id: int):
    AuthorizationService(current_user).can_user_create_project_comment(project_id)

    data = request.get_json()
    message =  data.get('data')
    if not message:
        raise ValidationError('Comment is empty')
    
    result = ProjectCommentService.add_comment(project_id, message)
    return jsonify(result)

@api.route('/projects/<int:project_id>/comments/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment_for_project(project_id: int, comment_id: int):
    AuthorizationService(current_user).can_user_delete_project_comment(project_id, comment_id)
    ProjectCommentService.remove_comment(comment_id)
    return jsonify({'message':'ok'})

@api.route('/projects/<int:project_id>/reports', methods=['POST'])
@login_required
def generate_report_for_project(project_id: int):
    AuthorizationService(current_user).can_user_generate_project_reports(project_id)
    result = ProjectReportService.generate_project_report(project_id)
    return jsonify({'name': result})

@api.route('/projects/<int:project_id>/settings', methods=['GET'])
@login_required
def get_project_settings(project_id: int):
    AuthorizationService(current_user).can_user_access_project_settings(project_id)
    result = ProjectService.get_project_settings(project_id)
    return jsonify(result)

@api.route('/projects/<int:project_id>/settings', methods=['POST'])
@login_required
def update_project_settings(project_id: int):
    AuthorizationService(current_user).can_user_update_project_settings(project_id)
   
    payload = request.get_json()    
    name = payload.get('name')
    description = payload.get('description')
    can_read_scratchpad = payload.get('can_auditor_read_scratchpad')
    can_write_scratchpad = payload.get('can_auditor_write_scratchpad')
    can_read_comments = payload.get('can_auditor_read_comments')
    can_write_comments = payload.get('can_auditor_write_comments')
    project_update_data = {
        'name': name if isinstance(name, str) and len(name) > 3 else None,
        'description': description if isinstance(name, str) else "",
        'can_auditor_read_scratchpad': can_read_scratchpad if isinstance(can_read_scratchpad, bool) else None,
        'can_auditor_write_scratchpad': can_write_scratchpad if isinstance(can_write_scratchpad, bool) else None,
        'can_auditor_read_comments': can_read_comments if isinstance(can_read_comments, bool) else None,
        'can_auditor_write_comments': can_write_comments if isinstance(can_write_comments, bool) else None,
    }
    
    ProjectService.update_project_settings(project_id, project_update_data)
    return jsonify({'message': 'ok'})


@api.route('/projects/<int:project_id>/members', methods=['POST'])
@login_required
def add_members_for_project(project_id: int):
    AuthorizationService(current_user).can_user_manage_project_members(project_id)
    
    payload = request.get_json()
    if not payload['members']:
        raise ValidationError('No new members submitted')
    
    new_members = []
    for entry in payload['members']:
        try:
            entry_id = int(entry.get('id'))
            if not entry_id or entry_id <= 0:
                raise ValidationError("Invalid or missing user ID")
            if (
                not isinstance(entry.get('email'), str) or 
                len(entry['email']) < 5 or 
                '@' not in entry['email'] or 
                '.' not in entry['email']
            ):
                raise ValidationError("Invalid email format")
        except (ValueError, TypeError):
            raise ValidationError("Invalid ID format or missing ID")
        
        new_members.append({'id': entry_id, 'email': entry['email']})

    ProjectMemberService.add_project_members(project_id, new_members)
    return jsonify({'message': 'ok'})

@api.route('/projects/<int:project_id>/members/<int:user_id>/access', methods=['PUT'])
@login_required
def update_access_level_for_user_in_project(project_id: int, user_id: int):
    AuthorizationService(current_user).can_user_manage_project_members(project_id)
    data = request.get_json()

    new_access_level = data['access_level']
    if not new_access_level and new_access_level not in ProjectRoles.values():
        raise ValidationError('Invalid or missing access level')
    
    ProjectMemberService.update_project_member_access_level(project_id, user_id, new_access_level)
    return jsonify({'message': 'ok'})

@api.route('/projects/<int:project_id>/members/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user_from_project(project_id: int, user_id: int):
    AuthorizationService(current_user).can_user_manage_project_members(project_id)
    ProjectMemberService.remove_project_member(project_id, user_id)
    return jsonify({'message': 'ok'})

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

            extra_tags: dict = {}
            content_type: Optional[str] = get_content_type_for_extension(file.filename)
            if content_type:
                extra_tags["ContentType"] = content_type
                
            S3().upload_file_obj(file, str(evidence_upload.upload_link), extra_tags)
    db.session.commit()
    return jsonify(evidence.as_dict())

@api.route('/evidence/<int:eid>', methods=['PUT'])
@login_required
def update_evidence(eid):
    result = Authorizer(current_user).can_user_manage_evidence(eid)
    result["extra"]["evidence"].name = request.form.get("name")
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

            extra_tags: dict = {}
            content_type: Optional[str] = get_content_type_for_extension(file.filename)
            if content_type:
                extra_tags["ContentType"] = content_type
                
            S3().upload_file_obj(file, str(evidence_upload.upload_link), extra_tags)
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

@api.route('/tenants/<int:tid>/projects', methods=['POST'])
@login_required
def create_project(tid):
    result = Authorizer(current_user).can_user_manage_tenant(tid)
    payload = request.get_json()
    result = project_creation(result["extra"]["tenant"], payload, current_user)
    if not result:
        return jsonify({"message": "failed to create project"}), 400
    return jsonify({"message": "ok"})

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
    result = Authorizer(current_user).can_user_manage_tag(ttid)
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

    file_type: FileType = get_file_type_by_extensions(evidence_upload.filename)
    content_type: Optional[str] = get_content_type_for_extension(evidence_upload.filename)
    file_url: str = S3().generate_presigned_url(current_app.config['EVIDENCE_BUCKET'], str(upload_id))
    download_url: str = S3().generate_presigned_download_url(current_app.config['EVIDENCE_BUCKET'], str(upload_id), evidence_upload.filename)

    return render_template(
        "evidence_upload.html",
        file_url=file_url,
        download_url=download_url,
        evidence_name=evidence.name,
        file_name=evidence_upload.filename,
        file_type=file_type.value,
        content_type=content_type,
    )