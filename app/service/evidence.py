from typing import Dict, List, Optional, Union

from app.repository import EvidenceRepository
from app.utils.misc import  calculate_percentage, obj_to_dict
from app.utils.types import SerializedObjectType

class EvidenceService:

    @staticmethod
    def get_project_evidence_summary(project_id: int) -> SerializedObjectType:
        evidence_with_subcontrol_count = EvidenceRepository.get_project_evidence_with_subcontrol_count(project_id)
        complete_evidence = EvidenceRepository.get_project_complete_evidence_count(project_id)

        data = {
            "evidence": [],
            "evidence_progress": 0.0
        }

        for evidence, subcontrol_count in evidence_with_subcontrol_count:
            control_dict = obj_to_dict(evidence)
            control_dict["associated_subcontrol_count"] = subcontrol_count
            data["evidence"].append(control_dict)

        if complete_evidence:
            subcontrols_with_evidence_count, total_subcontrol_count = complete_evidence
            data["evidence_progress"] = calculate_percentage(total_subcontrol_count, subcontrols_with_evidence_count)

        return data