from typing import List

from app.repository import ProjectSubControlRepository
from app.utils.misc import obj_to_dict
from app.utils.types import SerializedObjectType

class ProjectSubControlService:

    @staticmethod
    def get_project_subcontrol_summary(project_id: int, extra_filters: dict = {}) -> SerializedObjectType:
        subcontrols_with_summaries = ProjectSubControlRepository.get_project_subcontrols_with_summaries(project_id, extra_filters)

        data = []
        for project_subcontrol, *subcontrol_data in subcontrols_with_summaries:
            subcontrol_dict = obj_to_dict(project_subcontrol)
            subcontrol_dict = ProjectSubControlService.create_subcontrol_dict(project_subcontrol, *subcontrol_data)
            data.append(subcontrol_dict)

        return data

    @staticmethod
    def create_subcontrol_dict(*subcontrol_data: tuple) -> SerializedObjectType:
        project_subcontrol, parent_subcontrol, parent_control_name, project_name, framework_name, owner_email, \
        operator_email, subcontrol_comment_count, auditor_feedback_total_count, auditor_feedback_complete_count, \
        evidence_count = subcontrol_data

        subcontrol_dict = obj_to_dict(project_subcontrol)
        subcontrol_dict['comments'] = subcontrol_comment_count if subcontrol_comment_count is not None else 0
        subcontrol_dict['feedback'] = auditor_feedback_total_count if auditor_feedback_total_count is not None else 0
        subcontrol_dict['complete_feedback'] = auditor_feedback_complete_count if auditor_feedback_complete_count is not None else 0
        subcontrol_dict['is_complete'] = (project_subcontrol.implemented == 100) if project_subcontrol.implemented is not None else False
        subcontrol_dict['owner'] = owner_email if owner_email is not None else "Missing Owner"
        subcontrol_dict['operator'] = operator_email if operator_email is not None else "Missing Operator"
        subcontrol_dict['parent_control'] = parent_control_name
        subcontrol_dict['name'] = parent_subcontrol.name
        subcontrol_dict['description'] = parent_subcontrol.description
        subcontrol_dict['ref_code'] = parent_subcontrol.ref_code
        subcontrol_dict['mitigation'] = parent_subcontrol.mitigation
        subcontrol_dict['project'] = project_name
        subcontrol_dict['framework'] = framework_name
        subcontrol_dict['implementation_status'] = project_subcontrol.implementation_status()
        subcontrol_dict['evidence'] = evidence_count if evidence_count is not None else 0
        subcontrol_dict['has_evidence'] = evidence_count > 0 if evidence_count is not None else False

        return subcontrol_dict