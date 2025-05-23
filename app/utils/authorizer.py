from flask import abort
from app.utils.misc import get_class_by_tablename
import logging

AUTHORIZED_MSG = "authorized"
UNAUTHORIZED_MSG = "unauthorized"


class Authorizer:
    def __init__(self, user, bubble_errors=False, ds=False):
        self.user = user
        self.bubble_errors = bubble_errors
        # deserialize - don't return objects in the json response
        # Not implemented
        self.ds = ds

    def return_response(self, ok, msg, code=200, **kwargs):
        data = {**{"ok": ok, "message": msg, "code": code}, "extra": {**kwargs}}
        if self.bubble_errors or ok:
            return data
        abort(code, data)

    def id_to_obj(self, model_str, object):
        """
        convert id to object
        """
        model = get_class_by_tablename(model_str)
        if not model:
            logging.error(f"Model: {model_str} not found for Authorizer!")
            return self.return_response(False, "Invalid authorization query", 404)
        try:
            if isinstance(object, int):
                object = str(object)
            if isinstance(object, str):
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
        if (
            self.user.super
            or self.user.id == tenant.owner_id
            or self.user.has_role_for_tenant(tenant, "admin")
        ):
            return True
        return False

    def _can_user_manage_tenant(self, tenant):
        if (
            self.user.super
            or self.user.id == tenant.owner_id
            or self.user.has_role_for_tenant(tenant, "admin")
        ):
            return True
        return False

    def _can_user_read_tenant(self, tenant):
        if (
            self.user.super
            or self.user.id == tenant.owner_id
            or self.user.has_tenant(tenant)
        ):
            return True
        return False

    def _can_user_access_tenant(self, tenant):
        if (
            self.user.super
            or self.user.id == tenant.owner_id
            or self.user.has_tenant(tenant)
        ):
            return True
        return False

    def _can_user_access_risk_module(self, tenant):
        if (
            self.user.super
            or self.user.id == tenant.owner_id
            or self.user.has_any_role_for_tenant(
                tenant,
                ["admin", "viewer", "vendor", "riskmanager", "riskviewer"],
            )
        ):
            return True
        return False

    def _can_user_manage_risk(self, tenant):
        if (
            self.user.super
            or self.user.id == tenant.owner_id
            or self.user.has_any_role_for_tenant(
                tenant, ["admin", "viewer", "riskmanager"]
            )
        ):
            return True
        return False

    def can_user_create_tenants(self):
        if (
            self.user.super
            or self.user.can_user_create_tenant
            and len(self.user.get_tenants(own=True)) < self.user.tenant_limit
        ):
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

    def can_user_chat_in_tenant(self, tenant):
        """
        can user chat with the AI bot
        """
        if not (tenant := self._does_tenant_exist(tenant)):
            return self.return_response(False, "tenant not found", 404)
        if self._can_user_access_tenant(tenant) and tenant.ai_enabled:
            return self.return_response(True, AUTHORIZED_MSG, 200, tenant=tenant)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    # tenant assessment
    def can_user_manage_assessment(self, assessment):
        if not (assessment := self.id_to_obj("Assessment", assessment)):
            return self.return_response(False, "assessment not found", 404)
        if self.user.id == assessment.owner_id or self._can_user_manage_tenant(
            assessment.tenant
        ):
            return self.return_response(
                True, AUTHORIZED_MSG, 200, assessment=assessment
            )
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_read_assessment(self, assessment):
        if not (assessment := self.id_to_obj("Assessment", assessment)):
            return self.return_response(False, "assessment not found", 404)
        if self._can_user_access_tenant(assessment.tenant) or assessment.has_guest(
            self.user.email
        ):
            return self.return_response(
                True, AUTHORIZED_MSG, 200, assessment=assessment
            )
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_respond_to_assessment(self, assessment):
        if not (assessment := self.id_to_obj("Assessment", assessment)):
            return self.return_response(False, "assessment not found", 404)

        if assessment.has_guest(self.user.email) or self._can_user_admin_tenant(
            assessment.tenant
        ):
            return self.return_response(
                True, AUTHORIZED_MSG, 200, assessment=assessment
            )
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_question(self, question):
        if not (question := self.id_to_obj("FormItem", question)):
            return self.return_response(False, "question not found", 404)
        # TODO - check if user can manage question
        return self.return_response(True, AUTHORIZED_MSG, 200, question=question)
        # return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_form(self, form):
        if not (form := self.id_to_obj("Form", form)):
            return self.return_response(False, "form not found", 404)
        if self._can_user_manage_risk(form.tenant):
            return self.return_response(True, AUTHORIZED_MSG, 200, form=form)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_read_form(self, form):
        if not (form := self.id_to_obj("Form", form)):
            return self.return_response(False, "form not found", 404)
        if self._can_user_access_risk_module(form.tenant):
            return self.return_response(True, AUTHORIZED_MSG, 200, form=form)
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

    # Project evidence
    def can_user_manage_evidence(self, evidence):
        if not (evidence := self.id_to_obj("ProjectEvidence", evidence)):
            return self.return_response(False, "evidence not found", 404)
        if self.user.id == evidence.owner_id or self._can_user_manage_project(
            evidence.project
        ):
            return self.return_response(True, AUTHORIZED_MSG, 200, evidence=evidence)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_read_evidence(self, evidence):
        if not (evidence := self.id_to_obj("ProjectEvidence", evidence)):
            return self.return_response(False, "evidence not found", 404)
        if self.user.id == evidence.owner_id or self._can_user_read_project(
            evidence.project
        ):
            return self.return_response(True, AUTHORIZED_MSG, 200, evidence=evidence)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    # project
    def _does_project_exist(self, project):
        if project := self.id_to_obj("Project", project):
            return project
        return False

    def _can_user_manage_project(self, project):
        if self._can_user_admin_tenant(
            project.tenant
        ) or project.has_member_with_access(self.user, ["manager"]):
            return True
        return False

    def _can_user_edit_project(self, project):
        if self._can_user_admin_tenant(
            project.tenant
        ) or project.has_member_with_access(self.user, ["manager", "contributor"]):
            return True
        return False

    def _can_user_read_project(self, project):
        if self._can_user_admin_tenant(
            project.tenant
        ) or project.has_member_with_access(
            self.user, ["manager", "contributor", "viewer", "auditor"]
        ):
            return True
        return False

    def _can_user_audit_project(self, project):
        if project.has_member_with_access(self.user, ["auditor"]):
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
    def can_user_delete_project_comment(self, comment):
        if not (comment := self.id_to_obj("ProjectComment", comment)):
            return self.return_response(False, "comment not found", 404)
        if self.user.id == comment.owner_id or self._can_user_manage_project(
            comment.project
        ):
            return self.return_response(True, AUTHORIZED_MSG, 200, comment=comment)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    # project scratchpad
    def can_user_read_project_scratchpad(self, project):
        if not (project := self._does_project_exist(project)):
            return self.return_response(False, "project not found", 404)
        if self._can_user_read_project(project) or (
            self._can_user_audit_project(project)
            and project.can_auditor_read_scratchpad
        ):
            return self.return_response(True, AUTHORIZED_MSG, 200, project=project)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_write_project_scratchpad(self, project):
        if not (project := self._does_project_exist(project)):
            return self.return_response(False, "project not found", 404)
        if self._can_user_edit_project(project) or (
            self._can_user_audit_project(project)
            and project.can_auditor_write_scratchpad
        ):
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
        if self.user.id == comment.owner_id or self._can_user_manage_project(
            comment.project
        ):
            return self.return_response(True, AUTHORIZED_MSG, 200, comment=comment)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    # project subcontrol
    def can_user_read_project_subcontrol(self, subcontrol):
        if not (subcontrol := self.id_to_obj("ProjectSubControl", subcontrol)):
            return self.return_response(False, "subcontrol not found", 404)
        if self._can_user_access_project(subcontrol.p_control.project):
            return self.return_response(
                True, AUTHORIZED_MSG, 200, subcontrol=subcontrol
            )
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_project_subcontrol(self, subcontrol):
        if not (subcontrol := self.id_to_obj("ProjectSubControl", subcontrol)):
            return self.return_response(False, "subcontrol not found", 404)
        if (
            self.user.id == subcontrol.owner_id
            or self.user.id == subcontrol.operator_id
            or self._can_user_edit_project(subcontrol.p_control.project)
        ):
            return self.return_response(
                True, AUTHORIZED_MSG, 200, subcontrol=subcontrol
            )
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_project_control_status(self, control, status):
        if not status:
            return self.return_response(False, UNAUTHORIZED_MSG, 403)
        if not (control := self.id_to_obj("ProjectControl", control)):
            return self.return_response(False, "control not found", 404)
        if self._can_user_audit_project(control.project) and status.lower() in [
            "infosec action",
            "complete",
        ]:
            return self.return_response(True, AUTHORIZED_MSG, 200, control=control)
        if self.can_user_manage_project_control(control) and status.lower() in [
            "ready for auditor"
        ]:
            return self.return_response(True, AUTHORIZED_MSG, 200, control=control)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_project_subcontrol_notes(self, subcontrol):
        if not (subcontrol := self.id_to_obj("ProjectSubControl", subcontrol)):
            return self.return_response(False, "subcontrol not found", 404)
        if (
            self.user.id == subcontrol.owner_id
            or self.user.id == subcontrol.operator_id
            or self._can_user_edit_project(subcontrol.p_control.project)
        ):
            return self.return_response(
                True, AUTHORIZED_MSG, 200, subcontrol=subcontrol
            )
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_project_subcontrol_auditor_notes(self, subcontrol):
        if not (subcontrol := self.id_to_obj("ProjectSubControl", subcontrol)):
            return self.return_response(False, "subcontrol not found", 404)
        if self._can_user_audit_project(subcontrol.p_control.project):
            return self.return_response(
                True, AUTHORIZED_MSG, 200, subcontrol=subcontrol
            )
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_project_subcontrol_comment(self, comment):
        if not (comment := self.id_to_obj("SubControlComment", comment)):
            return self.return_response(False, "comment not found", 404)
        if self.user.id == comment.owner_id or self._can_user_manage_project(
            comment.subcontrol.p_control.project
        ):
            return self.return_response(True, AUTHORIZED_MSG, 200, comment=comment)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_add_project_control_feedback(self, control):
        if not (control := self.id_to_obj("ProjectControl", control)):
            return self.return_response(False, "control not found", 404)
        if self._can_user_audit_project(control.project):
            return self.return_response(True, AUTHORIZED_MSG, 200, control=control)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_project_control_feedback(self, feedback):
        if not (feedback := self.id_to_obj("AuditorFeedback", feedback)):
            return self.return_response(False, "feedback not found", 404)
        if self._can_user_edit_project(feedback.control.project):
            return self.return_response(True, AUTHORIZED_MSG, 200, feedback=feedback)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_project_control_auditor_feedback(self, control, feedback):
        if not (feedback := self.id_to_obj("AuditorFeedback", feedback)):
            return self.return_response(False, "feedback not found", 404)
        if self._can_user_audit_project(feedback.control.project):
            return self.return_response(True, AUTHORIZED_MSG, 200, feedback=feedback)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_project_subcontrol_evidence(self, subcontrol, evidence):
        if not (subcontrol := self.id_to_obj("ProjectSubControl", subcontrol)):
            return self.return_response(False, "subcontrol not found", 404)
        if not (evidence := self.id_to_obj("ProjectEvidence", evidence)):
            return self.return_response(False, "evidence not found", 404)
        if self._can_user_edit_project(subcontrol.p_control.project):
            return self.return_response(
                True, AUTHORIZED_MSG, 200, subcontrol=subcontrol, evidence=evidence
            )
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
        if self.user.id == policy.owner_id or self._can_user_manage_project(
            policy.project
        ):
            return self.return_response(True, AUTHORIZED_MSG, 200, policy=policy)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_add_policy_to_project(self, policy, project):
        if not (policy := self.id_to_obj("Policy", policy)):
            return self.return_response(False, "policy not found", 404)
        if not (project := self.id_to_obj("Project", project)):
            return self.return_response(False, "project not found", 404)
        if self._can_user_edit_project(project) and policy.tenant == project.tenant:
            return self.return_response(
                True, AUTHORIZED_MSG, 200, policy=policy, project=project
            )
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_delete_policy_from_project(self, policy, project):
        return self.can_user_add_policy_to_project(policy, project)

    def can_user_add_control_to_project(self, control, project):
        if not (control := self.id_to_obj("Control", control)):
            return self.return_response(False, "control not found", 404)
        if not (project := self.id_to_obj("Project", project)):
            return self.return_response(False, "project not found", 404)
        if self._can_user_edit_project(project) and control.tenant == project.tenant:
            return self.return_response(
                True, AUTHORIZED_MSG, 200, control=control, project=project
            )
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
            return self.return_response(
                True, AUTHORIZED_MSG, 200, user=user, tenant=tenant
            )
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_access_vendor(self, vendor):
        if not (vendor := self.id_to_obj("Vendor", vendor)):
            return self.return_response(False, "vendor not found", 404)
        if self._can_user_manage_tenant(vendor.tenant):
            return self.return_response(True, AUTHORIZED_MSG, 200, vendor=vendor)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_access_application(self, application):
        if not (application := self.id_to_obj("VendorApp", application)):
            return self.return_response(False, "application not found", 404)
        if self.can_user_access_vendor(application.vendor):
            return self.return_response(
                True, AUTHORIZED_MSG, 200, application=application
            )
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_access_risk_module(self, tenant):
        if not (tenant := self.id_to_obj("Tenant", tenant)):
            return self.return_response(False, "tenant not found", 404)

        if self._can_user_access_risk_module(tenant):
            return self.return_response(True, AUTHORIZED_MSG, 200, tenant=tenant)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_manage_risk(self, risk):
        if not (risk := self.id_to_obj("RiskRegister", risk)):
            return self.return_response(False, "risk not found", 404)

        if risk.project_id:
            if self.can_user_manage_project(risk.project):
                return self.return_response(True, AUTHORIZED_MSG, 200, risk=risk)
            return self.return_response(False, UNAUTHORIZED_MSG, 403)

        if self._can_user_manage_risk(risk.tenant):
            return self.return_response(True, AUTHORIZED_MSG, 200, risk=risk)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    # user email confirmation
    def can_user_send_email_confirmation(self, user):
        if not (user := self.id_to_obj("User", user)):
            return self.return_response(False, "user not found", 404)
        if self.user.id == user.id or self.can_user_manage_platform():
            return self.return_response(True, AUTHORIZED_MSG, 200, user=user)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)

    def can_user_verify_email_confirmation(self, user):
        if not (user := self.id_to_obj("User", user)):
            return self.return_response(False, "user not found", 404)
        if self.user.id == user.id or self.can_user_manage_platform():
            return self.return_response(True, AUTHORIZED_MSG, 200, user=user)
        return self.return_response(False, UNAUTHORIZED_MSG, 403)
