from typing import cast

from app.models import Policy, ProjectPolicy
from app.repository import ProjectPolicyRepository
from app.utils.misc import obj_to_dict
from app.utils.types import SerializedObjectType

class ProjectPolicyService:

    @staticmethod
    def get_project_policies_summary(project_id: int) -> SerializedObjectType:
        policies_with_summary = ProjectPolicyRepository.get_project_policies_summary(project_id)

        data = []
        for row in policies_with_summary:
            project_policy = cast(ProjectPolicy, row.ProjectPolicy)
            parent_policy = cast(Policy, row.Policy)
            
            policy_as_dict = obj_to_dict(project_policy)
            policy_as_dict['description'] = parent_policy.description
            policy_as_dict['name'] = parent_policy.name
            policy_as_dict['ref_code'] = parent_policy.ref_code
            policy_as_dict['public_viewable'] = parent_policy.public_viewable if parent_policy.public_viewable is not None else False
            data.append(policy_as_dict)

        return data