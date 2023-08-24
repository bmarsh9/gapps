from flask import request, current_app, render_template
from flask_login import current_user
from typing import List

from app.integrations.azure.graph_client import GraphClient
from app.utils.misc import get_users_from_text
from app.models import Policy, Project, ProjectControl, ProjectSubControl, ProjectMember


class TenantNotSpecified(Exception):
    pass

class NotificationService:

    @staticmethod
    def send_email_to_users_tagged_in_project_comment(comment:str, project: Project):
        tagged_users = get_users_from_text(comment, resolve_users=True, tenant=project.tenant)
        if tagged_users:
            title = f"{current_app.config['APP_NAME']}: Mentioned by {current_user.get_username()}"
            content = f"{current_user.get_username()} mentioned you in a comment for the {project.name} project. Please click the button to begin."
            GraphClient().send_email(
                title,
                recipients=[user.email for user in tagged_users],
                text_body=render_template(
                    'email/basic_template.txt',
                    title=title,
                    content=content,
                    button_link=f"{request.host_url}projects/{project.id}?tab=comments"
                ),
                html_body=render_template(
                    'email/basic_template.html',
                    title=title,
                    content=content,
                    button_link=f"{request.host_url}projects/{project.id}?tab=comments"
                )
            )

    @staticmethod
    def send_added_to_project_notification(project: Project, new_member_emails: List[str]):
        GraphClient().send_email(
            f"{current_app.config['APP_NAME']}: You have been added to a project.",
            new_member_emails,
            text_body=None,
            html_body=render_template(
                'email/basic_template.html',
                title=f"{current_app.config['APP_NAME']}: You have been added to a project.",
                content=f"You have been added to project {project.name} as viewer. Click on the button bellow to open the project.",
                button_link=f"{request.host_url}projects/{project.id}"
            )
        )

    @staticmethod
    def send_member_project_access_level_change_notification(project: Project, member_email: str, access_level: str):
        GraphClient().send_email(
            f"{current_app.config['APP_NAME']}: Project role changed.",
            [member_email],
            text_body=None,
            html_body=render_template(
                'email/basic_template.html',
                title=f"{current_app.config['APP_NAME']}: Project role changed.",
                content=f"Your role on project {project.name} has been changed to {access_level}. Click on the button bellow to open the project.",
                button_link=f"{request.host_url}projects/{project.id}"
            )
        )

    @staticmethod
    def send_app_invitation_email(invited_user_email: str, invitation_token: str):
        GraphClient().send_email(
            f"{current_app.config['APP_NAME']}: Welcome",
            recipients=[invited_user_email],
            text_body=render_template(
                'email/basic_template.txt',
                title=f"{current_app.config['APP_NAME']}: Welcome",
                content=f"You have been invited to {current_app.config['APP_NAME']}. Please click the button below to begin.",
                button_link="{}{}?token={}".format(request.host_url,"register",invitation_token)
            ),
            html_body=render_template(
                'email/basic_template.html',
                title=f"{current_app.config['APP_NAME']}: Welcome",
                content=f"You have been invited to {current_app.config['APP_NAME']}. Please click the button below to begin.",
                button_link="{}{}?token={}".format(request.host_url,"register",invitation_token)
            )
        )

    @staticmethod
    def send_invited_to_tenant_email(user_email:str):
        GraphClient().send_email(
            f"{current_app.config['APP_NAME']}: Tenant invite",
            recipients=[user_email],
            text_body=render_template(
                'email/basic_template.txt',
                title=f"{current_app.config['APP_NAME']}: Tenant invite",
                content=f"You have been added to a new tenant in {current_app.config['APP_NAME']}",
                button_link=request.host_url
            ),
            html_body=render_template(
                'email/basic_template.html',
                title=f"{current_app.config['APP_NAME']}: Tenant invite",
                content=f"You have been added to a new tenant in {current_app.config['APP_NAME']}",
                button_link=request.host_url
            )
        )

    @staticmethod
    def send_policy_owner_changed_notification(policy: Policy):
        GraphClient().send_email(
            f"{current_app.config['APP_NAME']}: Policy assigned to you.",
            [policy.owner.email],
            text_body=None,
            html_body=render_template(
                'email/basic_template.html',
                title=f"{current_app.config['APP_NAME']}: Policy assigned to you.",
                content="You have been added as policy owner. Click bellow to visit the policy page.",
                button_link=f"{request.host_url}policies/{policy.id}"
            )
        )

    @staticmethod
    def send_policy_reviewer_changed_notification(policy: Policy):
        GraphClient().send_email(
            f"{current_app.config['APP_NAME']}: Policy assigned to you.",
            [policy.reviewer.email],
            text_body=None,
            html_body=render_template(
                'email/basic_template.html',
                title=f"{current_app.config['APP_NAME']}: Policy assigned to you.",
                content="You have been added as policy reviewer. Click bellow to visit the policy page.",
                button_link=f"{request.host_url}policies/{policy.id}"
            )
        )

    @staticmethod
    def send_subcontrol_owner_changed_notification(subcontrol: ProjectSubControl):
        GraphClient().send_email(
            f"{current_app.config['APP_NAME']}: Control assigned to you.",
            [subcontrol.owner.email],
            text_body=None,
            html_body=render_template(
                'email/basic_template.html',
                title=f"{current_app.config['APP_NAME']}: Control assigned to you.",
                content="You have been added as control owner. Click bellow to visit the control page.",
                button_link=f"{request.host_url}projects/{subcontrol.project_id}/controls/{subcontrol.project_control_id}/subcontrols/{subcontrol.id}"
            )
        )

    @staticmethod
    def send_subcontrol_operator_changed_notification(subcontrol: ProjectSubControl):
        GraphClient().send_email(
            f"{current_app.config['APP_NAME']}: Control assigned to you.",
            [subcontrol.operator.email],
            text_body=None,
            html_body=render_template(
                'email/basic_template.html',
                title=f"{current_app.config['APP_NAME']}: Control assigned to you.",
                content="You have been added as control operator. Click bellow to visit the control page.",
                button_link=f"{request.host_url}projects/{subcontrol.project_id}/controls/{subcontrol.project_control_id}/subcontrols/{subcontrol.id}"
            )
        )

    @staticmethod
    def send_tagged_in_control_comment_notification(control: ProjectControl, recipient_emails: List[str]):
        title = f"{current_app.config['APP_NAME']}: Mentioned by {current_user.get_username()}"
        content = f"{current_user.get_username()} mentioned you in a comment for a control. Please click the button to begin."
        GraphClient().send_email(
            title,
            recipient_emails,
            text_body=render_template(
                'email/basic_template.txt',
                title=title,
                content=content,
                button_link=f"{request.host_url}projects/{control.project_id}/controls/{control.id}?tab=comments"
            ),
            html_body=render_template(
                'email/basic_template.html',
                title=title,
                content=content,
                button_link=f"{request.host_url}projects/{control.project_id}/controls/{control.id}?tab=comments"
            )
        )

    @staticmethod
    def send_tagged_in_subcontrol_comment_notification(subcontrol: ProjectSubControl, recipient_emails: List[str]):
        link = f"{request.host_url}projects/{subcontrol.project.id}/controls/{subcontrol.project_control_id}/subcontrols/{subcontrol.id}?tab=comments"
        title = f"{current_app.config['APP_NAME']}: Mentioned by {current_user.get_username()}"
        content = f"{current_user.get_username()} mentioned you in a comment for a subcontrol. Please click the button to begin."
        GraphClient().send_email(
            title,
            recipients=recipient_emails,
            text_body=render_template(
                'email/basic_template.txt',
                title=title,
                content=content,
                button_link=link
            ),
            html_body=render_template(
                'email/basic_template.html',
                title=title,
                content=content,
                button_link=link
            )
        )
    
    @staticmethod
    def send_subcontrol_status_change_notification(project_subcontrol: ProjectSubControl):
        roles_to_receive_notification = ["manager", "auditor"] if project_subcontrol.review_status == "ready for auditor" else ["manager"]
        recipient_emails = [
            member.user.email for member in 
            ProjectMember.query.filter(
                ProjectMember.project_id == project_subcontrol.project_id,
                ProjectMember.access_level.in_(roles_to_receive_notification)
            )
        ]
        if project_subcontrol.owner:
            recipient_emails.append(project_subcontrol.owner.email)
        if project_subcontrol.operator:
            recipient_emails.append(project_subcontrol.operator.email)
        recipient_emails = list(dict.fromkeys(recipient_emails))
        GraphClient().send_email(
            f"{current_app.config['APP_NAME']}: Subcontrol status changed.",
            recipients=recipient_emails,
            text_body=None,
            html_body=render_template(
                'email/basic_template.html',
                title=f"{current_app.config['APP_NAME']}: Subcontrol status changed.",
                content=f"Status for subcontrol {project_subcontrol.subcontrol.ref_code} in project {project_subcontrol.project.name} is now changed to {project_subcontrol.review_status}. Click the button bellow to visit the subcontrol page.",
                button_link=f"{request.host_url}projects/{project_subcontrol.project.id}/controls/{project_subcontrol.project_control_id}/subcontrols/{project_subcontrol.id}"
            )
        )
    