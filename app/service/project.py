from typing import List

from app.models import User
from app.repository.project import ProjectRepository
from app.utils.custom_errors import ProjectNotFound
from app.utils.misc import calculate_percentage
from app.utils.types import SerializedObjectType

class ProjectService:

    @staticmethod
    def get_project_summary(project_id) -> SerializedObjectType:
        project_summary =  ProjectRepository.get_project_summary(project_id)

        if project_summary is not None and len(project_summary) == 1:
            return ProjectService._get_summary_as_dict(project_summary[0])

        raise ProjectNotFound()

    @staticmethod
    def get_tenant_project_summaries(tenant_id: int) -> List[SerializedObjectType]:
        project_summeries =  ProjectRepository.get_tenant_project_summaries(tenant_id)

        projects = []
        if project_summeries:
            for project_summary in project_summeries:
                projects.append(ProjectService._get_summary_as_dict(project_summary))

        return projects
    
    @staticmethod
    def _get_summary_as_dict(project_summary) -> SerializedObjectType:
        (
            project,
            tenant_name,
            framework_name,
            requires_evidence,
            owner_email,
            auditor_emails,
            total_controls,
            total_policies,
            review_summary,
            subcontrols_total,
            subcontrols_implemented,
            subcontrols_complete,
            evidence_count,
        ) = project_summary

        data = {c.name: getattr(project, c.name) for c in project.__table__.columns}
        data['auditors'] = auditor_emails if auditor_emails is not None else []
        data['tenant'] = tenant_name
        data['framework'] = framework_name
        data['owner'] = owner_email
        data['total_controls'] = total_controls
        data['total_policies'] = total_policies
        data['review_summary'] = review_summary
        data['review_summary']['total'] = subcontrols_total

        evidence_compleation_percentage = 0.0
        total_completion_percentage = 0.0

        subcontrols_implementation_percentage = calculate_percentage(subcontrols_total, subcontrols_implemented)
        subcontrols_completion_percentage = calculate_percentage(subcontrols_total, subcontrols_complete)

        if requires_evidence:
            evidence_compleation_percentage = calculate_percentage(subcontrols_total, evidence_count)
            total_completion_percentage = (subcontrols_implementation_percentage + subcontrols_completion_percentage + evidence_compleation_percentage) / 3
        else:
            total_completion_percentage = (subcontrols_implementation_percentage + subcontrols_completion_percentage) / 2

        data['completion_progress'] = round(total_completion_percentage, 2)
        data['implemented_progress'] = subcontrols_implementation_percentage
        data['evidence_progress'] = evidence_compleation_percentage

        return data