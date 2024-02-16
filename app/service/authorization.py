from typing import List, Optional
import logging

from flask import current_app

from app.models import User, UserRole, Tenant
from app.repository.tenant import TenantRepository
from app.repository.user_role import UserRoleRepository
from app.utils.custom_errors import AuthorizationError, TenantNotFound

logger = logging.getLogger(__name__)

class AuthorizationService:

    def __init__(self, user: User):
        self.user = user

    def _is_super_user(self) -> bool:
        return self.user.super

    # Tenant access
    def can_user_access_tenant(self, tenant_id: int) -> bool:
        if self._is_super_user():
            return True
        
        tenant: Optional[Tenant] = TenantRepository.get_tenant_by_id(tenant_id)
        if tenant is None:
            current_app.logger.error(f"User({self.user.id}) attempted to access non-existent tenant({tenant_id})")
            raise TenantNotFound()
        
        if tenant.owner_id == self.user.id:
            return True
        
        user_roles: Optional[List[UserRole]] = UserRoleRepository.get_user_roles_for_tenant(self.user.id, tenant_id)
        if not user_roles: 
            current_app.logger.error(f"User({self.user.id}) does not have permission to access tenant({tenant_id})")
            raise AuthorizationError("User is not authorized to view the tenant")
        
        return True
