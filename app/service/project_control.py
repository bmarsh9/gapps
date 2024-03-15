from typing import Optional

from app.repository import ProjectControlRepository, ProjectSubControlRepository
from app.service.project_subcontrol import ProjectSubControlService
from app.utils.enums import ProjectControlStatus, ProjectSubControlStatus
from app.utils.misc import obj_to_dict, calculate_percentage
from app.utils.types import SerializedObjectType

class ProjectControlService:

    @staticmethod
    def get_project_control_summary(project_id: int, extra_filter: Optional[str] = None) -> SerializedObjectType:
        controls_with_summaries = ProjectControlRepository.get_project_controls_with_summaries(project_id, extra_filter)
        subcontrols_with_summaries = ProjectSubControlRepository.get_project_subcontrols_with_summaries(project_id)

        data = []

        for (
            project_control,
            parent_control,
            all_subcontrols_are_applicable,
            all_subcontrols_are_complete,
            distinct_evidence_count
        ) in controls_with_summaries:
            control_dict = obj_to_dict(project_control)
            control_dict.update(**parent_control.get_parent_data_as_dict())

            subcontrols_implementation_progress_sum = 0
            subcontrols_with_evidence_count = 0
            subcontrols_completed_count = 0
            subcontrols_review_complete_count = 0
            inapplicable_subcontrol_count = 0
            subcontrol_comment_count = 0
            subcontrol_feedback_count = 0
            subcontrol_feedback_complete_count = 0

            subcontrols_for_control = []
            for project_subcontrol, *subcontrol_data in subcontrols_with_summaries:
                if project_subcontrol.project_control_id == project_control.id:
                    subcontrol_dict = obj_to_dict(project_subcontrol)
                    subcontrol_dict = ProjectSubControlService.create_subcontrol_dict(project_subcontrol, *subcontrol_data)
                    subcontrols_for_control.append(subcontrol_dict)
                    subcontrols_implementation_progress_sum += subcontrol_dict['implemented']
                    subcontrols_with_evidence_count += int(subcontrol_dict['has_evidence'])
                    subcontrols_completed_count += int(subcontrol_dict['is_complete'])
                    subcontrols_review_complete_count += int(subcontrol_dict['review_status'] == ProjectSubControlStatus.COMPLETE.value)
                    inapplicable_subcontrol_count += int(not subcontrol_dict['is_applicable'])
                    subcontrol_feedback_count += subcontrol_dict['feedback']
                    subcontrol_feedback_complete_count += subcontrol_dict['complete_feedback']
                    subcontrol_comment_count += subcontrol_dict['comments']
                    
            control_dict['subcontrols'] = subcontrols_for_control
            control_dict['subcontrol_count'] = len(subcontrols_for_control)
            control_dict['is_applicable'] = all_subcontrols_are_applicable
            control_dict['is_complete'] = all_subcontrols_are_applicable and all_subcontrols_are_complete
            progress_implemented = int(subcontrols_implementation_progress_sum / len(subcontrols_for_control)) if subcontrols_for_control else 0            
            progress_evidence = calculate_percentage(len(subcontrols_for_control), subcontrols_with_evidence_count)
            progress_completed = calculate_percentage(len(subcontrols_for_control), subcontrols_completed_count)
            control_dict['progress_implemented'] = progress_implemented if all_subcontrols_are_applicable else 0
            control_dict['progress_evidence'] = progress_evidence if all_subcontrols_are_applicable else 0
            control_dict['progress_completed'] = progress_completed if all_subcontrols_are_applicable else 0
            control_status = ProjectControlService.get_project_control_status(
                all_subcontrols_are_applicable,
                all_subcontrols_are_complete,
                subcontrols_implementation_progress_sum
            )
            control_dict['status'] = control_status.value
            control_dict['stats'] = {
                'comments': subcontrol_comment_count,
                'evidence': distinct_evidence_count if distinct_evidence_count is not None else 0,
                'feedback': subcontrol_feedback_count,
                'complete_feedback': subcontrol_feedback_complete_count,
                'complete_reviews': subcontrols_review_complete_count,
                'subcontrols': len(subcontrols_for_control),
                'inapplicable_subcontrols': inapplicable_subcontrol_count,
                'subcontrols_complete': subcontrols_completed_count,
            }

            data.append(control_dict)

        return data

    @staticmethod
    def get_project_control_status(
        all_subcontrols_are_applicable: bool,
        all_subcontrols_are_complete: bool,
        subcontrols_implementation_progress_sum: int,
    ) -> ProjectControlStatus:
        if not all_subcontrols_are_applicable:
            return ProjectControlStatus.NOT_APPLICABLE
        if all_subcontrols_are_complete:
            return ProjectControlStatus.COMPLETE
        if subcontrols_implementation_progress_sum > 0:
            return ProjectControlStatus.IN_PROGRESS
        return ProjectControlStatus.NOT_STARTED
