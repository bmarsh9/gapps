from typing import List, Optional, Tuple

from app import db
from app.models import Role, Tenant, UserRole

class TenantRepository:

    @staticmethod
    def get_tenant_by_id(tenant_id: int) -> Optional[Tenant]:
        return Tenant.query.get(tenant_id)
    
    @staticmethod
    def get_tenant_with_user_roles(user_id: int, tenant_id: int) -> Tuple[Tenant, List[str]]:
        query_result = (
            db.session.query(Tenant, Role.name)
            .filter(Tenant.id == tenant_id)
            .join(UserRole, UserRole.tenant_id == Tenant.id)
            .join(Role, Role.id == UserRole.role_id)
            .filter(UserRole.user_id == user_id)
            .all()
        )

        tenant: Optional[Tenant] = None
        user_roles: List[str] = []

        if query_result:
            tenant, user_roles = query_result[0]
            user_roles = [role_name for _, role_name in query_result]

        return tenant, user_roles
