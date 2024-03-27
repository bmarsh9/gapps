from typing import Dict, List, Optional, Tuple, Union
import traceback

from flask import current_app
from flask_login import current_user
from sqlalchemy import and_, asc, func

from app import db
from app.models import (
    EvidenceAssociation,
    Framework,
    Project,
    ProjectControl,
    ProjectMember,
    ProjectPolicy,
    ProjectSubControl,
    Role,
    Tenant,
    User,
    UserRole
)
from app.repository.tenant import TenantRepository
from app.utils.custom_errors import PostgresError, TenantNotFound

class ProjectRepository:

    @staticmethod
    def get_project(project_id) -> Optional[Project]:
        return Project.query.get(project_id)

    @staticmethod
    def get_project_summary(project_id: int) -> List[Tuple[str, Union[Project, str, int, Optional[Dict[str, Union[str, int]]]]]]:
        return ProjectRepository._get_project_summary_query().filter(Project.id == project_id).all()
    
    @staticmethod
    def get_tenant_project_summaries(tenant_id: int) -> List[Tuple[str, Union[Project, str, int, Optional[Dict[str, Union[str, int]]]]]]:
        query = ProjectRepository._get_project_summary_query(tenant_id).filter(Project.tenant_id == tenant_id)

        tenant = TenantRepository.get_tenant_by_id(tenant_id)
        if tenant is None:
            raise TenantNotFound()

        if not current_user.super and current_user.id != tenant.owner_id:
            user_member_alias = db.aliased(User, name='user_member')
            query = (
                query
                .join(ProjectMember, ProjectMember.project_id == Project.id)
                .join(user_member_alias, user_member_alias.id == ProjectMember.user_id)
                .filter(user_member_alias.id == current_user.id)
            )

        return query.all()
    
    @staticmethod
    def get_project_notes(project_id: int) -> Optional[str]:
        return Project.query.with_entities(Project.notes).filter_by(id=project_id).scalar()
    
    @staticmethod
    def update_project_notes(project_id: int, notes: str):
        try:
            Project.query.filter_by(id=project_id).update({'notes': notes})
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(traceback.format_exc())
            raise PostgresError('Failed to update project notes')
        
    @staticmethod
    def get_project_settings(project_id: int) -> List[Tuple[str, bool]]:
        return Project.query.with_entities(
            Project.name,
            Project.description,
            Project.can_auditor_read_comments,
            Project.can_auditor_write_comments,
            Project.can_auditor_read_scratchpad,
            Project.can_auditor_write_scratchpad
        ).filter_by(id=project_id).first()
    
    @staticmethod
    def update_project_settings(project_id: int, properties: Dict[str, Union[str, bool]]) -> None:
        try:
            Project.query.filter_by(id=project_id).update(properties)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(traceback.format_exc())
            raise PostgresError('Failed to update project settings')


    @staticmethod
    def _get_project_summary_query(tenant_id=None) -> List[Tuple[str, Union[Project, str, int, Optional[Dict[str, Union[str, int]]]]]]:
        control_subquery = (
            db.session.query(
                Project.id.label('project_id'),
                func.count(ProjectControl.id).label('total_controls')
            )
            .join(Framework)
            .join(ProjectControl)
            .group_by(Project.id)
            .subquery()
        )

        policy_subquery = (
            db.session.query(
                Project.id.label('project_id'),
                func.count(ProjectPolicy.id).label('total_policies')
            )
            .join(Framework)
            .join(ProjectPolicy)
            .group_by(Project.id)
            .subquery()
        )

        subcontrol_subquery = (
            db.session.query(
                Project.id.label('project_id'),
                ProjectSubControl.review_status,
                func.count(ProjectSubControl.id).label('status_count')
            )
            .join(Framework)
            .join(ProjectSubControl)
            .group_by(Project.id, ProjectSubControl.review_status)
            .subquery()
        )

        summary_subquery = (
            db.session.query(
                subcontrol_subquery.c.project_id,
                func.json_object_agg(subcontrol_subquery.c.review_status, subcontrol_subquery.c.status_count).label('review_summary')
            )
            .group_by(subcontrol_subquery.c.project_id)
            .subquery()
        )

        auditor_subquery = (
            db.session.query(
                Project.id.label('project_id'),
                func.json_agg(func.json_build_object('id', User.id, 'email', User.email)).label('auditors')
            )
            .select_from(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .join(User, User.id == ProjectMember.user_id)
            .filter(ProjectMember.access_level == 'auditor')
            .group_by(Project.id)
            .subquery()
        )

        subcontrols_total_subquery = (
            db.session.query(
                Project.id.label('project_id'),
                func.count(ProjectSubControl.id).label('subcontrols_total')
            )
            .join(Framework)
            .join(ProjectSubControl)
            .group_by(Project.id)
            .subquery()
        )

        subcontrols_implemented_subquery = (
            db.session.query(
                Project.id.label('project_id'),
                func.coalesce(func.count(ProjectSubControl.id), 0).label('subcontrols_implemented')
            )
            .join(Framework)
            .join(ProjectSubControl)
            .filter(ProjectSubControl.implemented == 100)
            .filter(ProjectSubControl.is_applicable.is_(True))
            .group_by(Project.id)
            .subquery()
        )

        subcontrols_complete_subquery = (
            db.session.query(
                Project.id.label('project_id'),
                func.coalesce(func.count(ProjectSubControl.id), 0).label('subcontrols_complete')
            )
            .join(Framework)
            .join(ProjectSubControl)
            .filter(ProjectSubControl.is_applicable.is_(True))
            .filter(ProjectSubControl.review_status == 'complete')
            .group_by(Project.id)
            .subquery()
        )

        evidence_association_subquery = (
            db.session.query(
                ProjectSubControl.project_id.label('project_id'),
                func.count(func.distinct(EvidenceAssociation.control_id)).label('evidence_count')
            )
            .select_from(Project)
            .join(Framework)
            .join(ProjectSubControl)
            .join(EvidenceAssociation, EvidenceAssociation.control_id == ProjectSubControl.id)
            .filter(Framework.id == Project.framework_id)
            .group_by(ProjectSubControl.project_id)
            .having(func.bool_and(Framework.feature_evidence))
            .subquery()
        )

        query = (
            db.session.query(
                Project,
                Tenant.name.label('tenant_name'),
                Framework.name.label('framework_name'),
                Framework.feature_evidence.label('requires_evidence'),
                User.email.label('owner_email'),
                auditor_subquery.c.auditors,
                control_subquery.c.total_controls,
                policy_subquery.c.total_policies,
                summary_subquery.c.review_summary,
                subcontrols_total_subquery.c.subcontrols_total,
                subcontrols_implemented_subquery.c.subcontrols_implemented,
                subcontrols_complete_subquery.c.subcontrols_complete,
                evidence_association_subquery.c.evidence_count
            )
            .outerjoin(control_subquery, Project.id == control_subquery.c.project_id)
            .outerjoin(policy_subquery, Project.id == policy_subquery.c.project_id)
            .outerjoin(summary_subquery, Project.id == summary_subquery.c.project_id)
            .outerjoin(auditor_subquery, Project.id == auditor_subquery.c.project_id)
            .outerjoin(subcontrols_total_subquery, Project.id == subcontrols_total_subquery.c.project_id)
            .outerjoin(subcontrols_implemented_subquery, Project.id == subcontrols_implemented_subquery.c.project_id)
            .outerjoin(subcontrols_complete_subquery, Project.id == subcontrols_complete_subquery.c.project_id)
            .outerjoin(evidence_association_subquery, Project.id == evidence_association_subquery.c.project_id)
            .join(Tenant, Tenant.id == Project.tenant_id)
            .join(Framework, Framework.id == Project.framework_id)
            .join(User, User.id == Project.owner_id)
            .order_by(asc(Project.name))
        )

        if tenant_id is not None:
            query = query.filter(Project.tenant_id == tenant_id)

        return query
    
    @staticmethod
    def get_project_with_tenant_and_user_roles(user_id: int, project_id: int) -> Tuple[str, Union[Optional[Tenant], Optional[Project], List[str]]]:
        query_result = (
            db.session.query(Project, Tenant, Role.name)
            .join(Tenant, Tenant.id == Project.tenant_id)
            .join(UserRole, and_(UserRole.tenant_id == Project.tenant_id, UserRole.user_id == user_id))
            .join(Role, Role.id == UserRole.role_id)
            .filter(Project.id == project_id)
            .all()
        )
        
        project: Optional[Project] = None
        tenant: Optional[Tenant] = None
        user_roles: List[str] = []

        if query_result:
            project, tenant, user_roles = query_result[0]
            user_roles = [role_name for _, _, role_name in query_result]

        return project, tenant, user_roles
