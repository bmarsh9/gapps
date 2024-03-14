from typing import List, Optional

from flask import current_app

from app.models import Project, ProjectMember, User, UserRole, Tenant
from app.repository.project import ProjectRepository
from app.repository.project_member import ProjectMemberRepository
from app.repository.tenant import TenantRepository
from app.repository.user_role import UserRoleRepository
from app.utils.custom_errors import AuthorizationError, TenantNotFound, ProjectNotFound

class AuthorizationService:

    def __init__(self, user: User):
        self.user = user

    def _is_super_user(self) -> bool:
        return self.user.super
    
    # TODO: Move these helper methods into appropraite models after refactoring models    
    def has_any_role_for_tenant(self, tenant_id: int) -> bool:
        user_roles: Optional[List[UserRole]] = UserRoleRepository.get_user_roles_for_tenant(self.user.id, tenant_id)
        if not user_roles:
            return False
        return True
    
    def is_project_member(self, project_id: int) -> bool:
        project_member: Optional[ProjectMember] = ProjectMemberRepository.get_project_member(self.user.id, project_id)
        if not project_member:
            return False
        return True

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
        
        if self.has_any_role_for_tenant(tenant_id):
            return True
        
        current_app.logger.error(f"User({self.user.id}) does not have access to tenant({tenant_id})")
        raise AuthorizationError("User is not authorized to view the tenant")
    
    # Project access
    def can_user_access_project(self, project_id: int) -> bool:
        if self._is_super_user():
            return True
        
        project: Project = ProjectRepository.get_project_by_id(project_id)
        if project is None:
            raise ProjectNotFound()
        
        if project.tenant.owner_id == self.user.id:
            return True
                
        if self.has_any_role_for_tenant(project.tenant_id) and self.is_project_member(project.id):
            return True

        current_app.logger.error(f"User({self.user.id}) does not have permission to access project({project.id}) in tenant({project.tenant_id})")
        raise AuthorizationError("User is not authorized to access the project")

    # Expand access as needed

    def can_user_view_projects(self, project_id: int) -> bool:
        return self.can_user_access_project(project_id)
    
    def can_user_view_project_summary(self, project_id: int) -> bool:
        return self.can_user_access_project(project_id)
    
    def can_user_view_project_controls(self, project_id: int) -> bool:
        return self.can_user_access_project(project_id)
    
    def can_user_view_project_subcontrols(self, project_id: int) -> bool:
        return self.can_user_access_project(project_id)
    
    def can_user_view_project_policies(self, project_id: int) -> bool:
        return self.can_user_access_project(project_id)
    
    def can_user_view_project_evidence(self, project_id: int) -> bool:
        return self.can_user_access_project(project_id)
