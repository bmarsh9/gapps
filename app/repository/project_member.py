from typing import Dict, List, Optional, Tuple, Union
import traceback

from flask import current_app
from sqlalchemy import asc

from app import db
from app.models import ProjectMember, User
from app.utils.custom_errors import PostgresError
from app.utils.enums import ProjectRoles

class ProjectMemberRepository:

    @staticmethod
    def get_project_member(user_id: int, project_id: int) -> Optional[ProjectMember]:
        return ProjectMember.query.filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id
        ).first()

    @staticmethod
    def get_project_members_with_associated_user_data(project_id: int) -> List[Tuple[str, Union[str, int, ProjectMember]]]:
        return (
            db.session.query(
                ProjectMember,
                User.id.label('user_id'),
                User.email.label('user_email'),
            )
            .join(User, User.id == ProjectMember.user_id)
            .filter(ProjectMember.project_id == project_id)
            .order_by(asc(User.id))
        ).all()

    @staticmethod
    def add_project_members(project_id: int, members_to_add: List[Dict[str, Union[int, str]]]) -> None:
        try:
            with db.session.begin(subtransactions=True):
                 for member_data in members_to_add:
                    project_member = ProjectMember(
                        user_id = member_data['id'],
                        project_id = project_id,
                        access_level = ProjectRoles.VIEWER.value
                    )
                    db.session.add(project_member)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(traceback.format_exc())
            raise PostgresError('An error occurred while attempting to add new members')

    @staticmethod
    def delete_project_member(project_id: int, user_id: int) -> None:
        try:
            ProjectMember.query.filter_by(project_id=project_id, user_id=user_id).delete()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(traceback.format_exc())
            raise PostgresError('An error occurred while attempting to remove user from the project')
        
    @staticmethod
    def update_project_member_access_level(project_id: int, user_id: int, access_level: str) -> None:
        try:
            ProjectMember.query.filter_by(
                project_id=project_id,
                user_id=user_id
            ).update({'access_level': access_level})
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(traceback.format_exc())
            raise PostgresError('Failed to update member access level')
