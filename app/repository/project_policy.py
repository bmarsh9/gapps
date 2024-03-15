from typing import List, Tuple, Union

from app import db
from app.models import (
    Policy,
    ProjectPolicy
)

class ProjectPolicyRepository:

    @staticmethod
    def get_project_policies_summary(project_id: int) -> List[Tuple[str, Union[ProjectPolicy, Policy]]]:
        return (
            db.session.query(
                ProjectPolicy,
                Policy,
            )
            .join(Policy, ProjectPolicy.policy_id == Policy.id)
            .filter(ProjectPolicy.project_id == project_id)
            .order_by(Policy.name)
        ).all()
