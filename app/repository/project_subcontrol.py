from typing import List

from flask import current_app
from flask_login import current_user
from sqlalchemy import and_, func, case, or_
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models import (
    AuditorFeedback,
    Control,
    EvidenceAssociation,
    Framework,
    Project,
    ProjectControl,
    ProjectSubControl,
    SubControl,
    SubControlComment,
    User
)
from app.utils.custom_errors import PostgresError
from app.utils.enums import ProjectSubControlsFilter, ProjectSubControlStatus


class ProjectSubControlRepository:
    
    @staticmethod
    def get_project_subcontrols(project_id: int) -> List[ProjectSubControl]:
        return ProjectSubControl.query.filter_by(ProjectSubControl.project_id == project_id).all()
    
    @staticmethod
    def get_project_subcontrols_for_project_control(control_id: int) -> List[ProjectSubControl]:
        return ProjectSubControl.query.filter_by(ProjectSubControl.project_control_id == control_id).all()
    
    @staticmethod
    def get_project_subcontrols_with_summaries(project_id: int, extra_filters: dict = {}):
    
        filter = extra_filters.get('filter', None)
        owner = extra_filters.get('owner', None)
        operator = extra_filters.get('operator', None)

        comment_count_subquery = (
            db.session.query(
                SubControlComment.subcontrol_id,
                func.count().label("subcontrol_comment_count")
            )
            .group_by(SubControlComment.subcontrol_id)
            .subquery()
        )

        auditor_feedback_counts_subquery = (
            db.session.query(
                AuditorFeedback.subcontrol_id,
                func.count().label("auditor_feedback_total_count"),
                func.sum(case([(AuditorFeedback.auditor_complete == True, 1)], else_=0)).label("auditor_feedback_complete_count")
            )
            .group_by(AuditorFeedback.subcontrol_id)
            .subquery()
        )

        evidence_count_subquery = (
            db.session.query(
                EvidenceAssociation.control_id,
                func.count().label("evidence_count")
            )
            .group_by(EvidenceAssociation.control_id)
            .subquery()
        )


        owner_alias = db.aliased(User)
        operator_alias = db.aliased(User)

        filters = [
            ProjectSubControl.project_id == project_id,
        ]

        if filter == ProjectSubControlsFilter.AM_OWNER.value:
            filters.append(ProjectSubControl.owner_id == current_user.id)

        elif filter == ProjectSubControlsFilter.AM_OPERATOR.value:
            filters.append(ProjectSubControl.operator_id == current_user.id)

        elif filter == ProjectSubControlsFilter.IS_APPLICABLE.value:
            filters.append(ProjectSubControl.is_applicable.is_(True))

        elif filter == ProjectSubControlsFilter.NOT_APPLICABLE.value:
            filters.append(ProjectSubControl.is_applicable.is_(False))

        elif filter == ProjectSubControlsFilter.HAS_EVIDENCE.value:
            filters.append(EvidenceAssociation.control_id == ProjectSubControl.id)

        elif filter == ProjectSubControlsFilter.MISSING_EVIDENCE.value:
            missing_evidence_subquery = (
                ~db.session.query(EvidenceAssociation)
                .filter(EvidenceAssociation.control_id == ProjectSubControl.id)
                .exists()
            )
            filters.append(missing_evidence_subquery)

        elif filter == ProjectSubControlsFilter.REVIEW_NOT_STARTED.value:
            filters.append(ProjectSubControl.review_status == ProjectSubControlStatus.NOT_STARTED.value)

        elif filter == ProjectSubControlsFilter.REVIEW_INFOSEC_ACTION.value:
            filters.append(ProjectSubControl.review_status == ProjectSubControlStatus.INFOSEC_ACTION.value)

        elif filter == ProjectSubControlsFilter.REVIEW_ACTION_REQUIRED.value:
            filters.append(ProjectSubControl.review_status == ProjectSubControlStatus.ACTION_REQUIRED.value)

        elif filter == ProjectSubControlsFilter.REVIEW_READY_FOR_AUDITOR.value:
            filters.append(ProjectSubControl.review_status == ProjectSubControlStatus.READY_FOR_AUDITOR.value)

        elif filter == ProjectSubControlsFilter.REVIEW_COMPLETE.value:
            filters.append(ProjectSubControl.review_status == ProjectSubControlStatus.COMPLETE.value)

        elif filter == ProjectSubControlsFilter.IMPLEMENTED.value:
            filters.append(ProjectSubControl.implemented == 100)

        elif filter == ProjectSubControlsFilter.NOT_IMPLEMENTED.value:
            filters.append(ProjectSubControl.implemented < 100)

        elif filter == ProjectSubControlsFilter.NOT_COMPLETE.value:
            not_complete_condition = and_(
                ProjectSubControl.is_applicable.is_(True),
                or_(
                    ProjectSubControl.implemented != 100,
                    ProjectSubControl.review_status != ProjectSubControlStatus.COMPLETE.value,
                    and_(
                        db.session.query(Framework.feature_evidence)
                        .filter(Project.framework_id == Framework.id)
                        .correlate(Project)
                        .exists(),
                        ~db.session.query(EvidenceAssociation)
                        .filter(EvidenceAssociation.control_id == ProjectSubControl.id)
                        .exists()
                    )
                )
            )

            filters.append(not_complete_condition)

        elif filter == ProjectSubControlsFilter.COMPLETE.value:
            filters.append(ProjectSubControl.is_applicable.is_(True))
            filters.append(
                and_(
                    ProjectSubControl.implemented == 100,
                    ProjectSubControl.review_status == ProjectSubControlStatus.COMPLETE.value
                    )
                )
            feature_evidence_subquery = (
                db.session.query(Framework.feature_evidence)
                .filter(Project.framework_id == Framework.id)
                .correlate(Project)
            )
            if db.session.query(feature_evidence_subquery.exists()).scalar():
                filters.append(EvidenceAssociation.control_id == ProjectSubControl.id)

        if owner is not None:
            filters.append(func.lower(owner_alias.email).ilike(func.lower(f"%{owner}%")))

        if operator is not None:
            filters.append(func.lower(operator_alias.email).ilike(func.lower(f"%{operator}%")))

        query = (
            db.session.query(
                ProjectSubControl,
                SubControl,
                Control.name.label("parent_control_name"),
                Project.name.label("project_name"),
                Framework.name.label("framework_name"),
                owner_alias.email.label("owner_email"),
                operator_alias.email.label("operator_email"),
                comment_count_subquery.c.subcontrol_comment_count,
                auditor_feedback_counts_subquery.c.auditor_feedback_total_count,
                auditor_feedback_counts_subquery.c.auditor_feedback_complete_count,
                evidence_count_subquery.c.evidence_count
            )
            .outerjoin(comment_count_subquery, ProjectSubControl.id == comment_count_subquery.c.subcontrol_id)
            .outerjoin(auditor_feedback_counts_subquery, ProjectSubControl.id == auditor_feedback_counts_subquery.c.subcontrol_id)
            .join(SubControl, ProjectSubControl.subcontrol_id == SubControl.id)
            .join(ProjectControl, ProjectSubControl.project_control_id == ProjectControl.id)
            .join(Control, ProjectControl.control_id == Control.id)
            .join(Project, ProjectSubControl.project_id == Project.id)
            .join(Framework, Project.framework_id == Framework.id)
            .outerjoin(owner_alias, ProjectSubControl.owner_id == owner_alias.id)
            .outerjoin(operator_alias, ProjectSubControl.operator_id == operator_alias.id)
            .outerjoin(evidence_count_subquery, ProjectSubControl.id == evidence_count_subquery.c.control_id)
            .filter(*filters)
            .order_by(ProjectSubControl.id)
        )

        try:
            return query.all()
        except SQLAlchemyError as e:
            current_app.logger.error(f"Postgres READ operation failed failed for user({current_user.id})")
            raise PostgresError("An error occurred while attempting to fetch project subcontrols with summaries.")
