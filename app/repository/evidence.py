from typing import List, Tuple, Union

from sqlalchemy import asc, func

from app import db
from app.models import (
    Evidence,
    EvidenceAssociation,
    ProjectSubControl
)

class EvidenceRepository:

    @staticmethod
    def get_project_evidence_with_subcontrol_count(project_id: int) -> List[Tuple[str, Union[Evidence, int]]]:
        return (
            db.session.query(
                Evidence,
                func.count(func.distinct(EvidenceAssociation.control_id)).label("subcontrol_count")
            )
            .join(EvidenceAssociation, EvidenceAssociation.evidence_id == Evidence.id)
            .join(ProjectSubControl, ProjectSubControl.id == EvidenceAssociation.control_id)
            .filter(ProjectSubControl.project_id == project_id)
            .group_by(Evidence.id, Evidence.name)
            .order_by(asc(Evidence.name))
        ).all()
    
    @staticmethod
    def get_project_complete_evidence_count(project_id: int) -> List[Tuple[str, int]]:
        return  (
            db.session.query(
                func.count(func.distinct(EvidenceAssociation.control_id)).label("subcontrols_with_evidence_count"),
                func.count(func.distinct(ProjectSubControl.id).label("total_subcontrol_count"))
            )
            .outerjoin(EvidenceAssociation, EvidenceAssociation.control_id == ProjectSubControl.id)
            .filter(ProjectSubControl.project_id == project_id)
            .group_by(ProjectSubControl.project_id)
            .first()
        )
