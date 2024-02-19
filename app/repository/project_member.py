from typing import Optional

from app.models import ProjectMember

class ProjectMemberRepository:

    @staticmethod
    def get_project_member(user_id: int, project_id: int) -> Optional[ProjectMember]:
        return ProjectMember.query.filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id
        ).first()