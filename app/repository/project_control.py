from typing import List

from flask import current_app
from flask_login import current_user
from sqlalchemy import and_, case, distinct, func
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models import (
    Control,
    EvidenceAssociation,
    Framework,
    Project,
    ProjectControl,
    ProjectSubControl
)
from app.utils.custom_errors import PostgresError
from app.utils.enums import ProjectControlsFilter

class ProjectControlRepository:
    
    @staticmethod
    def get_project_controls(project_id: int) -> List[ProjectControl]:
        return ProjectControl.query.filter(ProjectControl.project_id == project_id).all()

    @staticmethod
    def get_project_controls_with_summaries(project_id: int, extra_filter: str = None) -> dict:

        distinct_evidence_count_subquery = (
            db.session.query(
                ProjectControl.id,
                func.count(distinct(EvidenceAssociation.evidence_id)).label('distinct_evidence_count')
            )
            .join(ProjectSubControl, ProjectControl.id == ProjectSubControl.project_control_id)
            .join(EvidenceAssociation, ProjectSubControl.id == EvidenceAssociation.control_id)
            .group_by(ProjectControl.id)
            .subquery()
        )

        subcontrol_alias = db.aliased(ProjectSubControl)
        evidence_association_alias = db.aliased(EvidenceAssociation)

        filters = [
            ProjectControl.project_id == project_id,
        ]
        
        if extra_filter == ProjectControlsFilter.IS_APPLICABLE.value:
            filters.append(subcontrol_alias.is_applicable.is_(True))

        elif extra_filter == ProjectControlsFilter.NOT_APPLICABLE.value:
            filters.append(subcontrol_alias.is_applicable.isnot(True))

        elif extra_filter == ProjectControlsFilter.IMPLEMENTED.value:
            filters.append(subcontrol_alias.implemented == 100)

        elif extra_filter == ProjectControlsFilter.NOT_IMPLEMENTED.value:
            filters.append(subcontrol_alias.implemented < 100)

        query = (
            db.session.query(
                ProjectControl,
                Control,
                case(
                    [
                        (
                            func.count().filter(subcontrol_alias.is_applicable == True) == func.count(),
                            True
                        ),
                    ],
                    else_=False
                ).label('all_subcontrols_are_applicable'),
                case(
                    [
                        (
                            and_(
                                Framework.feature_evidence == True,
                                func.count().filter(subcontrol_alias.id == evidence_association_alias.control_id) == func.count(),
                                func.count().filter(subcontrol_alias.implemented == 100) == func.count()
                            ),
                            True
                        ),
                        (
                            and_(
                                Framework.feature_evidence.in_([False, None]),
                                func.count().filter(subcontrol_alias.implemented == 100) == func.count()
                            ),
                            True
                        ),
                    ],
                    else_=False
                ).label('all_subcontrols_are_complete'),
                distinct_evidence_count_subquery.c.distinct_evidence_count,
            )
            .outerjoin(subcontrol_alias, ProjectControl.id == subcontrol_alias.project_control_id)
            .outerjoin(evidence_association_alias, subcontrol_alias.id == evidence_association_alias.control_id)
            .outerjoin(distinct_evidence_count_subquery, ProjectControl.id == distinct_evidence_count_subquery.c.id)
            .join(Project, Project.id == ProjectControl.project_id)
            .join(Framework, Framework.id == Project.framework_id)
            .join(Control, ProjectControl.control_id == Control.id)
            .filter(*filters)
            .group_by(
                ProjectControl.id,
                Project.id,
                Framework.id,
                Control.id,
                distinct_evidence_count_subquery.c.distinct_evidence_count
            )
            .order_by(ProjectControl.id)
        )

        try:
            return query.all()
        except SQLAlchemyError as e:
            current_app.logger.error(f"Postgres READ operation failed failed for user({current_user.id})")
            raise PostgresError("An error occurred while attempting to fetch project controls with summaries.")