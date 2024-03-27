from typing import Dict, List, Union

from app.repository import (
    ProjectMemberRepository,
    ProjectSubControlRepository,
    UserRepository
)
from app.utils.notification_service import NotificationService
from app.service.project import ProjectService
from app.service.user import UserService
from app.utils.types import SerializedObjectType

class ProjectMemberService:

    @staticmethod
    def get_project_responsibility_matrix(project_id: int) -> SerializedObjectType:
        responsibility_matrix = UserRepository.get_project_user_responsibility_matrix(project_id)
        project_total_subcontrol_count = ProjectSubControlRepository.get_project_subcontrols_count(project_id)

        data = {
            'responsibility_matrix': [],
            'total_project_subcontrols': project_total_subcontrol_count,
        }

        for user_id, user_email, owned_subcontrols, operated_subcontrols in responsibility_matrix:
            data['responsibility_matrix'].append({
                'user': {
                    'id': user_id,
                    'email': user_email,
                },
                'owned_subcontrols': owned_subcontrols,
                'operated_subcontrols': operated_subcontrols,
            })

        return data

    @staticmethod
    def add_project_members(project_id: int, members_to_add: List[Dict[str, Union[int, str]]]) -> None:
        ProjectMemberRepository.add_project_members(project_id, members_to_add)
        project = ProjectService.get_project_or_404(project_id)
        new_member_emails = [member.get('email') for member in members_to_add if member.get('email')]
        NotificationService.send_added_to_project_notification(project, new_member_emails)

    @staticmethod
    def update_project_member_access_level(project_id: int, user_id: int, access_level: str) -> None:
        ProjectMemberRepository.update_project_member_access_level(project_id, user_id, access_level)
        project = ProjectService.get_project_or_404(project_id)
        user_email = UserService.get_user_email_or_raise_404(user_id)
        NotificationService.send_member_project_access_level_change_notification(project, user_email, access_level)

    @staticmethod
    def remove_project_member(project_id: int, user_id: int) -> None:
        ProjectMemberRepository.delete_project_member(project_id, user_id)
