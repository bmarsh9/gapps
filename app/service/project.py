from typing import List

from app.models import User
from app.repository.project import ProjectRepository

class ProjectService:

    @staticmethod
    def get_tenant_project_summaries(current_user: User, tenant_id: int) -> List[dict]:
        project_summeries =  ProjectRepository.get_tenant_project_summaries(current_user, tenant_id)
        projects = []

        if project_summeries:
            for (
                project,tenant_name,
                framework_name,
                owner_email,
                auditor_emails,
                total_controls,
                total_policies,
                review_summary,
                subcontrols_total,
                subcontrols_complete,
            ) in project_summeries:
                data = {c.name: getattr(project, c.name) for c in project.__table__.columns}
                data['auditors'] = auditor_emails if auditor_emails is not None else []
                data['tenant'] = tenant_name
                data['framework'] = framework_name
                data['owner'] = owner_email
                data['total_controls'] = total_controls
                data['total_policies'] = total_policies
                data['review_summary'] = review_summary
                completion_percentage = (subcontrols_complete or 0) / subcontrols_total * 100 if subcontrols_total else 0
                completion_percentage = round(completion_percentage, 2)
                data['completion_progress'] = completion_percentage
                projects.append(data)

        return projects