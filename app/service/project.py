from typing import Dict, List, Union

from app.models import Project
from app.repository import ProjectMemberRepository, ProjectRepository
from app.utils.custom_errors import ProjectNotFound
from app.utils.misc import calculate_percentage, obj_to_dict
from app.utils.types import SerializedObjectType

class ProjectService:

    @staticmethod
    def get_project_or_404(project_id: int) -> Project:
        project = ProjectRepository.get_project(project_id)
        if project is None:
            raise ProjectNotFound()
        return project

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
    def get_project_notes(project_id: int) -> str:
        notes = ProjectRepository.get_project_notes(project_id)
        return notes if notes is not None else ""
    
    @staticmethod
    def update_project_notes(project_id: int, notes: str) -> None:
        ProjectRepository.update_project_notes(project_id, notes)

    @staticmethod
    def get_project_settings(project_id: int) -> SerializedObjectType:
        settings = ProjectRepository.get_project_settings(project_id)
        if not settings:
            raise ProjectNotFound()
        
        project_members = ProjectMemberRepository.get_project_members_with_associated_user_data(project_id)

        members = []
        for project_member, user_id, user_email in project_members:
            members.append({
                "access_level": project_member.access_level,
                "email": user_email,
                "id": user_id,
            })

        settings_dict = {
            "name": settings.name,
            "description": settings.description,
            "can_auditor_read_comments": settings.can_auditor_read_comments,
            "can_auditor_write_comments": settings.can_auditor_write_comments,
            "can_auditor_read_scratchpad": settings.can_auditor_read_scratchpad,
            "can_auditor_write_scratchpad": settings.can_auditor_write_scratchpad,
            "members": members
        }

        return settings_dict
    
    @staticmethod
    def update_project_settings(project_id: int, update_data: Dict[str, Union[str, bool]]) -> None:
        properties = {}
        for name, new_value in update_data.items():
            if new_value is not None:
                properties[name] = new_value
        ProjectRepository.update_project_settings(project_id, properties)

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

        data = obj_to_dict(project)
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
