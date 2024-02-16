from sqlalchemy import func

from app import db
from app.models import (
    EvidenceAssociation,
    Framework,
    Project,
    ProjectControl,
    ProjectMember,
    ProjectPolicy,
    ProjectSubControl,
    Tenant,
    User,
)
from app.repository.tenant import TenantRepository
from app.utils.custom_errors import TenantNotFound

class ProjectRepository:

    @staticmethod
    def get_tenant_project_summaries(current_user: User, tenant_id: int):
        control_subquery = (
            db.session.query(
                Project.id.label('project_id'),
                func.count(ProjectControl.id).label('total_controls')
            )
            .join(Framework)
            .join(ProjectControl)
            .filter(Project.tenant_id == tenant_id)
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
            .filter(Project.tenant_id == tenant_id)
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
            .filter(Project.tenant_id == tenant_id)
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
            .filter(ProjectMember.access_level == "auditor")
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
            .filter(Project.tenant_id == tenant_id)
            .group_by(Project.id)
            .subquery()
        )

        evidence_required_subquery = (
            db.session.query(
                Framework.id
            )
            .select_from(Project)
            .join(Framework)
            .filter(Framework.id == Project.framework_id)
            .filter(Framework.feature_evidence.is_(True))
            .subquery()
        )

        subcontrols_complete_subquery = (
            db.session.query(
                Project.id.label('project_id'),
                func.coalesce(func.count(ProjectSubControl.id), 0).label('subcontrols_complete')
            )
            .join(Framework)
            .join(ProjectSubControl)
            .filter(Project.tenant_id == tenant_id)
            .filter(ProjectSubControl.implemented == 100)
            .filter(ProjectSubControl.is_applicable.is_(True))
            .filter(ProjectSubControl.review_status == "complete")
            .group_by(Project.id)
            .subquery()
        )

        evidence_association_subquery = (
            db.session.query(
                ProjectSubControl.project_id.label('project_id'),
                func.count(EvidenceAssociation.control_id).label('evidence_count')
            )
            .select_from(Project)
            .join(Framework)
            .join(ProjectSubControl)
            .join(EvidenceAssociation, EvidenceAssociation.control_id == ProjectSubControl.id)
            .filter(Project.tenant_id == tenant_id)
            .filter(Framework.id == evidence_required_subquery.c.id)
            .filter(Project.id == Project.id)
            .group_by(ProjectSubControl.project_id)
            .subquery()
        )

        query = (
            db.session.query(
                Project,
                Tenant.name.label('tenant_name'),
                Framework.name.label('framework_name'),
                User.email.label('owner_email'),
                auditor_subquery.c.auditors,
                control_subquery.c.total_controls,
                policy_subquery.c.total_policies,
                summary_subquery.c.review_summary,
                subcontrols_total_subquery.c.subcontrols_total,
                subcontrols_complete_subquery.c.subcontrols_complete
            )
            .outerjoin(control_subquery, Project.id == control_subquery.c.project_id)
            .outerjoin(policy_subquery, Project.id == policy_subquery.c.project_id)
            .outerjoin(summary_subquery, Project.id == summary_subquery.c.project_id)
            .outerjoin(auditor_subquery, Project.id == auditor_subquery.c.project_id)
            .outerjoin(subcontrols_total_subquery, Project.id == subcontrols_total_subquery.c.project_id)
            .outerjoin(subcontrols_complete_subquery, Project.id == subcontrols_complete_subquery.c.project_id)
            .outerjoin(evidence_association_subquery, Project.id == evidence_association_subquery.c.project_id)
            .join(Tenant, Tenant.id == tenant_id)
            .join(Framework, Framework.id == Project.framework_id)
            .join(User, User.id == Project.owner_id)
            .filter(Project.tenant_id == tenant_id)
        )

        tenant = TenantRepository.get_tenant_by_id(tenant_id)
        if tenant is None:
            raise TenantNotFound()

        if not current_user.super and current_user.id != (tenant is None or current_user.id != tenant.owner_id):
            user_member_alias = db.aliased(User, name="user_member")
            query = (
                query
                .join(ProjectMember, ProjectMember.project_id == Project.id)
                .join(user_member_alias, user_member_alias.id == ProjectMember.user_id)
                .filter(user_member_alias.id == current_user.id)
            )

        return query.all()
