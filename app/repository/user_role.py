from typing import List

from sqlalchemy import and_

from app.models import Role, UserRole
from app.utils.enums import TenantRole

class UserRoleRepository:

    @staticmethod
    def get_all_user_roles_for_tenant(tenant_id: int) -> List[UserRole]:
        return UserRole.query.filter(UserRole.tenant_id == tenant_id).all()
    
    @staticmethod
    def get_users_roles_for_tenant(user_id: int, tenant_id: int) -> List[UserRole]:
        return UserRole.query.filter(
            UserRole.user_id == user_id,
            UserRole.tenant_id == tenant_id
        ).all()

    @staticmethod
    def get_users_roles_for_tenant_filter_by_role(user_id: int, tenant_id: int, roles: List[TenantRole]) -> List[UserRole]:
        return (
            UserRole.query
                .join(Role)
                .filter(
                    and_(
                        UserRole.user_id == user_id,
                        UserRole.tenant_id == tenant_id,
                        Role.name.in_(roles)
                    )
                )
                .with_entities(UserRole)
                .all()
        )
