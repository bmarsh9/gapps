from typing import List

from sqlalchemy import and_

from app.models import UserRole
from app.utils.enums import TenantRole

class UserRoleRepository:

    @staticmethod
    def get_user_roles_for_tenant(user_id: int, tenant_id: int) -> List[UserRole]:
        return UserRole.query.filter(
            and_(
                UserRole.user_id == user_id,
                UserRole.tenant_id == tenant_id,
                UserRole.role_id.in_(TenantRole.get_role_ids_with_access_to_tenant())
            )
        ).all()
    
    @staticmethod
    def has_any_role_for_tenant(user_id: int, tenant_id: int) -> bool:
        user_roles: List[UserRole] = UserRoleRepository.get_user_roles_for_tenant(user_id, tenant_id)
        if not user_roles:
            return False
        return True