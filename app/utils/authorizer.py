from flask import abort
from app.utils.misc import get_class_by_tablename
import logging

AUTHORIZED_MSG = "authorized"
UNAUTHORIZED_MSG = "unauthorized"

logger = logging.getLogger(__name__)


class Authorizer:
    def __init__(self, user, bubble_errors=False, ds=False):
        self.user = user
        self.bubble_errors = bubble_errors
        # deserialize - dont return objects in the json response
        # Not implemented
        self.ds = ds

    def return_response(self, ok, msg, code=200, **kwargs):
        data = {**{"ok": ok, "message":msg, "code": code}, "extra": {**kwargs}}
        if self.bubble_errors or ok:
            return data
        abort(code, data)

    def id_to_obj(self, model_str, object):
        """
        convert id to object
        """
        model = get_class_by_tablename(model_str)
        if not model:
            logging.error(f"table object: {model_str} not found for Authorizer!")
        try:
            if isinstance(object, (int, str)):
                if not (object := model.query.get(object)):
                    return False
            return object
        except Exception as e:
            logging.error(e)
            return False

    # platform
    def can_user_manage_platform(self):
        if self.user.super:
            return self.return_response(True, AUTHORIZED_MSG, 200)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    # tenant
    def _does_tenant_exist(self, tenant):
        return self.id_to_obj("Tenant", tenant)

    def _can_user_admin_tenant(self, tenant):
        if self.user.super or self.user.id == tenant.owner_id or self.user.has_any_role_for_tenant(tenant, "admin"):
            return True
        return False

    def _can_user_manage_tenant(self, tenant):
        if self.user.super or self.user.id == tenant.owner_id or self.user.has_any_role_for_tenant(tenant, ["admin", "editor"]):
            return True
        return False

    def _can_user_read_tenant(self, tenant):
        if self.user.super or self.user.id == tenant.owner_id or self.user.has_any_role_for_tenant(tenant, ["admin", "editor","viewer"]):
            return True
        return False

    def _can_user_access_tenant(self, tenant):
        if self.user.super or self.user.id == tenant.owner_id or self.user.has_tenant(tenant):
            return True
        return False

    def can_user_create_tenants(self):
        if self.user.super or self.user.can_user_create_tenant and len(self.user.tenants(own=True)) < self.user.tenant_limit:
            return self.return_response(True, AUTHORIZED_MSG, 200)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_admin_tenant(self, tenant):
        if not (tenant := self._does_tenant_exist(tenant)):
            return self.return_response(False, "tenant not found", 404)
        if self._can_user_admin_tenant(tenant):
            return self.return_response(True, AUTHORIZED_MSG, 200, tenant=tenant)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_tenant(self, tenant):
        if not (tenant := self._does_tenant_exist(tenant)):
            return self.return_response(False, "tenant not found", 404)
        if self._can_user_manage_tenant(tenant):
            return self.return_response(True, AUTHORIZED_MSG, 200, tenant=tenant)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_read_tenant(self, tenant):
        if not (tenant := self._does_tenant_exist(tenant)):
            return self.return_response(False, "tenant not found", 404)
        if self._can_user_read_tenant(tenant):
            return self.return_response(True, AUTHORIZED_MSG, 200, tenant=tenant)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_access_tenant(self, tenant):
        if not (tenant := self._does_tenant_exist(tenant)):
            return self.return_response(False, "tenant not found", 404)
        if self._can_user_access_tenant(tenant):
            return self.return_response(True, AUTHORIZED_MSG, 200, tenant=tenant)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    # tenant questionnaire
    def can_user_manage_questionnaire(self, questionnaire):
        if not (questionnaire := self.id_to_obj("Questionnaire", questionnaire)):
            return self.return_response(False, "questionnaire not found", 404)
        if self.user.id == questionnaire.owner_id or self._can_user_manage_tenant(questionnaire.tenant):
            return self.return_response(True, AUTHORIZED_MSG, 200, questionnaire=questionnaire)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_read_questionnaire(self, questionnaire):
        if not (questionnaire := self.id_to_obj("Questionnaire", questionnaire)):
            return self.return_response(False, "questionnaire not found", 404)
        if self._can_user_access_tenant(questionnaire.tenant) or questionnaire.has_guest(self.user.email):
            return self.return_response(True, AUTHORIZED_MSG, 200, questionnaire=questionnaire)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_submit_questionnaire(self, questionnaire):
        if not (questionnaire := self.id_to_obj("Questionnaire", questionnaire)):
            return self.return_response(False, "questionnaire not found", 404)
        if questionnaire.has_guest(self.user.email):
            return self.return_response(True, AUTHORIZED_MSG, 200, questionnaire=questionnaire)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_render_questionnaire(self, questionnaire):
        if not (questionnaire := self.id_to_obj("Questionnaire", questionnaire)):
            return self.return_response(False, "questionnaire not found", 404)
        if self._can_user_admin_tenant(questionnaire.tenant) or questionnaire.has_guest(self.user.email):
            return self.return_response(True, AUTHORIZED_MSG, 200, questionnaire=questionnaire)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    # tenant tag
    def can_user_manage_tag(self, tag):
        if not (tag := self.id_to_obj("Tag", tag)):
            return self.return_response(False, "tag not found", 404)
        if self.user == tag.owner_id or self._can_user_manage_tenant(tag.tenant):
            return self.return_response(True, AUTHORIZED_MSG, 200, tag=tag)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    # tenant policy labels
    def can_user_manage_policy_label(self, label):
        if not (label := self.id_to_obj("PolicyLabels", label)):
            return self.return_response(False, "policy label not found", 404)
        if self.user == label.owner_id or self._can_user_manage_tenant(label.tenant):
            return self.return_response(True, AUTHORIZED_MSG, 200, tag=tag)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    # tenant controls
    def can_user_manage_control(self, control):
        if not (control := self.id_to_obj("Control", control)):
            return self.return_response(False, "control not found", 404)
        if self._can_user_manage_tenant(control.tenant):
            return self.return_response(True, AUTHORIZED_MSG, 200, control=control)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_read_control(self, control):
        if not (control := self.id_to_obj("Control", control)):
            return self.return_response(False, "control not found", 404)
        if self._can_user_read_tenant(control.tenant):
            return self.return_response(True, AUTHORIZED_MSG, 200, control=control)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    # tenant policies
    def can_user_manage_policy(self, policy):
        if not (policy := self.id_to_obj("Policy", policy)):
            return self.return_response(False, "policy not found", 404)
        if self._can_user_manage_tenant(policy.tenant):
            return self.return_response(True, AUTHORIZED_MSG, 200, policy=policy)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_read_policy(self, policy):
        if not (policy := self.id_to_obj("Policy", policy)):
            return self.return_response(False, "policy not found", 404)
        if self._can_user_read_tenant(policy.tenant):
            return self.return_response(True, AUTHORIZED_MSG, 200, policy=policy)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    # tenant framework
    def can_user_read_framework(self, framework):
        if not (framework := self.id_to_obj("Framework", framework)):
            return self.return_response(False, "framework not found", 404)
        if self._can_user_read_tenant(framework.tenant):
            return self.return_response(True, AUTHORIZED_MSG, 200, framework=framework)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    # tenant evidence
    def can_user_manage_evidence(self, evidence):
        if not (evidence := self.id_to_obj("Evidence", evidence)):
            return self.return_response(False, "evidence not found", 404)
        if self.user.id == evidence.owner_id or self._can_user_manage_tenant(evidence.tenant):
            return self.return_response(True, AUTHORIZED_MSG, 200, evidence=evidence)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_read_evidence(self, evidence):
        if not (evidence := self.id_to_obj("Evidence", evidence)):
            return self.return_response(False, "evidence not found", 404)
        if self.user.id == evidence.owner_id or self._can_user_read_tenant(evidence.tenant):
            return self.return_response(True, AUTHORIZED_MSG, 200, evidence=evidence)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    # project
    def _does_project_exist(self, project):
        if project := self.id_to_obj("Project", project):
            return project
        return False

    def _can_user_manage_project(self, project):
        if self._can_user_admin_tenant(project.tenant) or project.has_member_with_access(self.user, ["manager"]):
            return True
        return False

    def _can_user_edit_project(self, project):
        if self._can_user_admin_tenant(project.tenant) or project.has_member_with_access(self.user, ["manager", "contributor"]):
            return True
        return False

    def _can_user_read_project(self, project):
        if self._can_user_admin_tenant(project.tenant) or project.has_member_with_access(self.user, ["manager", "contributor", "viewer"]):
            return True
        return False

    def _can_user_audit_project(self, project):
        if self._can_user_admin_tenant(project.tenant) or project.has_member_with_access(self.user, ["auditor"]):
            return True
        return False

    def _can_user_access_project(self, project):
        if self._can_user_admin_tenant(project.tenant) or project.has_member(self.user):
            return True
        return False

    def can_user_manage_project(self, project):
        if not (project := self._does_project_exist(project)):
            return self.return_response(False, "project not found", 404)
        if self._can_user_manage_project(project):
            return self.return_response(True, AUTHORIZED_MSG, 200, project=project)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_edit_project(self, project):
        if not (project := self._does_project_exist(project)):
            return self.return_response(False, "project not found", 404)
        if self._can_user_edit_project(project):
            return self.return_response(True, AUTHORIZED_MSG, 200, project=project)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_read_project(self, project):
        """
        has any role except for auditor
        """
        if not (project := self._does_project_exist(project)):
            return self.return_response(False, "project not found", 404)
        if self._can_user_read_project(project):
            return self.return_response(True, AUTHORIZED_MSG, 200, project=project)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_audit_project(self, project):
        if not (project := self._does_project_exist(project)):
            return self.return_response(False, "project not found", 404)
        if self._can_user_audit_project(project):
            return self.return_response(True, AUTHORIZED_MSG, 200, project=project)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_access_project(self, project):
        """
        has any access level to project
        """
        if not (project := self._does_project_exist(project)):
            return self.return_response(False, "project not found", 404)
        if self._can_user_access_project(project):
            return self.return_response(True, AUTHORIZED_MSG, 200, project=project)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    # project comments
    def can_user_read_project_comments(self, project):
        if not (project := self._does_project_exist(project)):
            return self.return_response(False, "project not found", 404)
        if self._can_user_read_project(project) or (self._can_user_audit_project(project) and project.can_auditor_read_comments):
            return self.return_response(True, AUTHORIZED_MSG, 200, project=project)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_write_project_comments(self, project):
        if not (project := self._does_project_exist(project)):
            return self.return_response(False, "project not found", 404)
        if self._can_user_edit_project(project) or (self._can_user_audit_project(project) and project.can_auditor_write_comments):
            return self.return_response(True, AUTHORIZED_MSG, 200, project=project)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_delete_project_comment(self, comment):
        if not (comment := self.id_to_obj("ProjectComment", comment)):
            return self.return_response(False, "comment not found", 404)
        if self.user.id == comment.owner_id or self._can_user_manage_project(comment.project):
            return self.return_response(True, AUTHORIZED_MSG, 200, comment=comment)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    # project scratchpad
    def can_user_read_project_scratchpad(self, project):
        if not (project := self._does_project_exist(project)):
            return self.return_response(False, "project not found", 404)
        if self._can_user_read_project(project) or (self._can_user_audit_project(project) and project.can_auditor_read_scratchpad):
            return self.return_response(True, AUTHORIZED_MSG, 200, project=project)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_write_project_scratchpad(self, project):
        if not (project := self._does_project_exist(project)):
            return self.return_response(False, "project not found", 404)
        if self._can_user_edit_project(project) or (self._can_user_audit_project(project) and project.can_auditor_write_scratchpad):
            return self.return_response(True, AUTHORIZED_MSG, 200, project=project)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    # project control
    def can_user_read_project_control(self, control):
        if not (control := self.id_to_obj("ProjectControl", control)):
            return self.return_response(False, "control not found", 404)
        if self._can_user_access_project(control.project):
            return self.return_response(True, AUTHORIZED_MSG, 200, control=control)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_project_control(self, control):
        if not (control := self.id_to_obj("ProjectControl", control)):
            return self.return_response(False, "control not found", 404)
        if self._can_user_edit_project(control.project):
            return self.return_response(True, AUTHORIZED_MSG, 200, control=control)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_project_control_notes(self, control):
        if not (control := self.id_to_obj("ProjectControl", control)):
            return self.return_response(False, "control not found", 404)
        if self._can_user_edit_project(control.project):
            return self.return_response(True, AUTHORIZED_MSG, 200, control=control)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_project_control_auditor_notes(self, control):
        if not (control := self.id_to_obj("ProjectControl", control)):
            return self.return_response(False, "control not found", 404)
        if self._can_user_audit_project(control.project):
            return self.return_response(True, AUTHORIZED_MSG, 200, control=control)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_project_control_comment(self, comment):
        if not (comment := self.id_to_obj("ControlComment", comment)):
            return self.return_response(False, "comment not found", 404)
        if self.user.id == comment.owner_id or self._can_user_manage_project(comment.project):
            return self.return_response(True, AUTHORIZED_MSG, 200, comment=comment)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    # project subcontrol
    def can_user_read_project_subcontrol(self, subcontrol):
        if not (subcontrol := self.id_to_obj("ProjectSubControl", subcontrol)):
            return self.return_response(False, "subcontrol not found", 404)
        if self._can_user_access_project(subcontrol.p_control.project):
            return self.return_response(True, AUTHORIZED_MSG, 200, subcontrol=subcontrol)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_project_subcontrol(self, subcontrol):
        if not (subcontrol := self.id_to_obj("ProjectSubControl", subcontrol)):
            return self.return_response(False, "subcontrol not found", 404)
        if self.user.id == subcontrol.owner_id or self.user.id == subcontrol.operator_id or self._can_user_edit_project(subcontrol.p_control.project):
            return self.return_response(True, AUTHORIZED_MSG, 200, subcontrol=subcontrol)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_project_subcontrol_status(self, subcontrol, status):
        if not status:
            return self.return_response(False, UNAUTHORIZED_MSG, 403)
        if not (subcontrol := self.id_to_obj("ProjectSubControl", subcontrol)):
            return self.return_response(False, "subcontrol not found", 404)
        if self._can_user_admin_tenant(subcontrol.p_control.project.tenant) and status.lower() in ["not started","infosec action","ready for auditor","action required","complete"]:
            return self.return_response(True, AUTHORIZED_MSG, 200, subcontrol=subcontrol)
        if self._can_user_audit_project(subcontrol.p_control.project) and status.lower() in ["action required","complete"]:
            return self.return_response(True, AUTHORIZED_MSG, 200, subcontrol=subcontrol)
        elif self._can_user_edit_project(subcontrol.p_control.project) and status.lower() in ["not started","infosec action","ready for auditor"]:
            return self.return_response(True, AUTHORIZED_MSG, 200, subcontrol=subcontrol)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_project_subcontrol_notes(self, subcontrol):
        if not (subcontrol := self.id_to_obj("ProjectSubControl", subcontrol)):
            return self.return_response(False, "subcontrol not found", 404)
        if self.user.id == subcontrol.owner_id or self.user.id == subcontrol.operator_id or self._can_user_edit_project(subcontrol.p_control.project):
            return self.return_response(True, AUTHORIZED_MSG, 200, subcontrol=subcontrol)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_project_subcontrol_auditor_notes(self, subcontrol):
        if not (subcontrol := self.id_to_obj("ProjectSubControl", subcontrol)):
            return self.return_response(False, "subcontrol not found", 404)
        if self._can_user_audit_project(subcontrol.p_control.project):
            return self.return_response(True, AUTHORIZED_MSG, 200, subcontrol=subcontrol)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_project_subcontrol_comment(self, comment):
        if not (comment := self.id_to_obj("SubControlComment", comment)):
            return self.return_response(False, "comment not found", 404)
        if self.user.id == comment.owner_id or self._can_user_manage_project(comment.subcontrol.p_control.project):
            return self.return_response(True, AUTHORIZED_MSG, 200, comment=comment)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_add_project_subcontrol_feedback(self, subcontrol):
        if not (subcontrol := self.id_to_obj("ProjectSubControl", subcontrol)):
            return self.return_response(False, "subcontrol not found", 404)
        if self._can_user_audit_project(subcontrol.p_control.project):
            return self.return_response(True, AUTHORIZED_MSG, 200, subcontrol=subcontrol)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_project_subcontrol_feedback(self, feedback):
        if not (feedback := self.id_to_obj("AuditorFeedback", feedback)):
            return self.return_response(False, "feedback not found", 404)
        if self._can_user_edit_project(feedback.subcontrol.p_control.project):
            return self.return_response(True, AUTHORIZED_MSG, 200, feedback=feedback)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_project_subcontrol_auditor_feedback(self, feedback):
        if not (feedback := self.id_to_obj("AuditorFeedback", feedback)):
            return self.return_response(False, "feedback not found", 404)
        if self._can_user_audit_project(subcontrol.p_control.project):
            return self.return_response(True, AUTHORIZED_MSG, 200, feedback=feedback)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_project_subcontrol_evidence(self, subcontrol, evidence):
        if not (subcontrol := self.id_to_obj("ProjectSubControl", subcontrol)):
            return self.return_response(False, "subcontrol not found", 404)
        if not (evidence := self.id_to_obj("Evidence", evidence)):
            return self.return_response(False, "evidence not found", 404)
        if self._can_user_edit_project(subcontrol.p_control.project):
            return self.return_response(True, AUTHORIZED_MSG, 200, subcontrol=subcontrol, evidence=evidence)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    # project policy
    def can_user_read_project_policy(self, policy):
        if not (policy := self.id_to_obj("ProjectPolicy", policy)):
            return self.return_response(False, "policy not found", 404)
        if self._can_user_read_project(policy.project):
            return self.return_response(True, AUTHORIZED_MSG, 200, policy=policy)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_project_policy(self, policy):
        if not (policy := self.id_to_obj("ProjectPolicy", policy)):
            return self.return_response(False, "policy not found", 404)
        if self.user.id == policy.owner_id or self._can_user_manage_project(policy.project):
            return self.return_response(True, AUTHORIZED_MSG, 200, policy=policy)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_add_policy_to_project(self, policy, project):
        if not (policy := self.id_to_obj("Policy", policy)):
            return self.return_response(False, "policy not found", 404)
        if not (project := self.id_to_obj("Project", project)):
            return self.return_response(False, "project not found", 404)
        if self._can_user_edit_project(project) and policy.tenant == project.tenant:
            return self.return_response(True, AUTHORIZED_MSG, 200, policy=policy, project=project)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_delete_policy_from_project(self, policy, project):
        return self.can_user_add_policy_to_project(policy, project)

    def can_user_add_control_to_project(self, control, project):
        if not (control := self.id_to_obj("Control", control)):
            return self.return_response(False, "control not found", 404)
        if not (project := self.id_to_obj("Project", project)):
            return self.return_response(False, "project not found", 404)
        if self._can_user_edit_project(project) and control.tenant == project.tenant:
            return self.return_response(True, AUTHORIZED_MSG, 200, control=control, project=project)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_delete_control_from_project(self, control, project):
        return self.can_user_add_control_to_project(control, project)

    # users
    def can_user_manage_user(self, user):
        if not (user := self.id_to_obj("User", user)):
            return self.return_response(False, "user not found", 404)
        if self.user.id == user.id or self.can_user_manage_platform():
            return self.return_response(True, AUTHORIZED_MSG, 200, user=user)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_read_tenants_of_user(self, user):
        if not (user := self.id_to_obj("User", user)):
            return self.return_response(False, "user not found", 404)
        if self.user.id == user.id or self.can_user_manage_platform():
            return self.return_response(True, AUTHORIZED_MSG, 200, user=user)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_user_roles_in_tenant(self, user, tenant):
        if not (user := self.id_to_obj("User", user)):
            return self.return_response(False, "user not found", 404)
        if not (tenant := self.id_to_obj("Tenant", tenant)):
            return self.return_response(False, "tenant not found", 404)
        if self._can_user_admin_tenant(tenant):
            return self.return_response(True, AUTHORIZED_MSG, 200, user=user, tenant=tenant)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)
