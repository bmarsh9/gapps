from flask import current_app
from sqlalchemy import and_, case, cast, Float, func, Integer, Numeric

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
import logging

logger = logging.getLogger(__name__)


def get_all_projects_by_tenant_id(tenant_id: int):
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

    query = (
        db.session.query(
            Project,
            Tenant.name.label('tenant_name'),
            Framework.name.label('framework_name'),
            User.email.label('owner_email'),
            auditor_subquery.c.auditors,
            control_subquery.c.total_controls,
            policy_subquery.c.total_policies,
            summary_subquery.c.review_summary
        )
        .outerjoin(control_subquery, Project.id == control_subquery.c.project_id)
        .outerjoin(policy_subquery, Project.id == policy_subquery.c.project_id)
        .outerjoin(summary_subquery, Project.id == summary_subquery.c.project_id)
        .outerjoin(auditor_subquery, Project.id == auditor_subquery.c.project_id)
        .join(Tenant, Tenant.id == tenant_id)
        .join(Framework, Framework.id == Project.framework_id)
        .join(User, User.id == Project.owner_id)
        .filter(Project.tenant_id == tenant_id)
    )

    result = query.all()

    current_app.logger.info(f"Columns: {[desc['name'] for desc in query.column_descriptions]}")
    current_app.logger.info(f"Query Result: {result}")

    projects_with_counts = []

    for (
        project,tenant_name,
        framework_name,
        owner_email,
        auditor_emails,
        total_controls,
        total_policies,
        review_summary,
        # subcontrols_complete,
        # subcontrols_total,
    ) in result:
        data = {c.name: getattr(project, c.name) for c in project.__table__.columns}
        data['auditors'] = auditor_emails if auditor_emails is not None else []
        data['tenant'] = tenant_name
        data['framework'] = framework_name
        data['owner'] = owner_email
        data['total_controls'] = total_controls
        data['total_policies'] = total_policies
        data['review_summary'] = review_summary
        # data['subcontrols_complete'] = subcontrols_complete
        # data['subcontrols_total'] = subcontrols_total
        projects_with_counts.append(data)


    # DEBUG STUFF DELETE
    current_app.logger.info(f"Result: {projects_with_counts}")

    return projects_with_counts

