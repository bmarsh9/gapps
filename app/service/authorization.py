from typing import List, Optional, Tuple, Union

from flask import current_app

from app.models import (
    Project,
    ProjectMember,
    User,
    UserRole,
    Tenant
)
from app.repository import (
    ProjectCommentRepository,
    ProjectRepository,
    ProjectMemberRepository,
    TenantRepository,
    UserRoleRepository
)
from app.utils.custom_errors import (
    AuthorizationError,
    TenantNotFound,
    ProjectCommentNotFound,
    ProjectNotFound
)
from app.utils.enums import TenantRole, ProjectRoles

class AuthorizationService:

    def __init__(self, user: User):
        self.user = user
    
    # Tenant access
    def can_user_access_tenant(self, tenant_id: int) -> bool:
        if self._is_super_user():
            return True
        
        tenant, roles = self._get_tenant_and_user_roles(tenant_id)

        if self._is_tenant_owner(tenant) or self._can_access_tenant(roles):
            return True
        
        current_app.logger.error(f'User({self.user.id}) does not have access to Tenant({tenant.id})')
        raise AuthorizationError('User is not authorized to view the tenant')

    '''
    PROJECT ACCESS
    Collection of checks for project access and management
    '''
    
    def can_user_access_project(self, project_id: int) -> bool:
        if self._is_super_user():
            return True
        
        project, tenant, roles = self._get_project_with_tenant_and_user_roles(project_id)

        if (
            self._is_tenant_owner(tenant) or 
            self._can_manage_tenant(roles) or 
            (
                self._can_access_tenant(roles) and
                self._is_project_member(project.id)
            )
        ):
            return True

        current_app.logger.error(f'User({self.user.id}) does not have permission to access Project({project.id})')
        raise AuthorizationError('User is not authorized to access the project')

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

    def can_user_view_project_responsibility_matrix(self, project_id: int) -> bool:
        return self.can_user_access_project(project_id)
    
    def can_user_view_project_notes(self, project_id: int) -> bool:
        if self._is_super_user():
            return True
        
        project, tenant, roles = self._get_project_with_tenant_and_user_roles(project_id)

        if self._is_tenant_owner(tenant) or self._can_manage_tenant(roles):
            return True
        
        if self._can_access_tenant(roles):
            user_project_member = self._get_project_member(project_id)
            if user_project_member:
                if (
                    user_project_member.access_level == ProjectRoles.AUDITOR.value and
                    project.can_auditor_read_scratchpad
                ):
                    return True
                elif (
                    user_project_member.access_level != ProjectRoles.AUDITOR.value and 
                    user_project_member.access_level in ProjectRoles.values()
                ):
                    return True
                
        current_app.logger.error(f'User({self.user.id}) does not have permission to view Project({project.id}) notes in Tenant({project.tenant_id})')
        raise AuthorizationError('User is not authorized to view project notes')
    
    def can_user_update_project_notes(self, project_id: int) -> bool:
        if self._is_super_user():
            return True
        
        project, tenant, roles = self._get_project_with_tenant_and_user_roles(project_id)

        if self._is_tenant_owner(tenant) or self._can_manage_tenant(roles):
            return True
        
        if self._can_access_tenant(roles):
            user_project_member = self._get_project_member(project_id)
            if user_project_member:
                if (
                    user_project_member.access_level == ProjectRoles.AUDITOR.value and
                    project.can_auditor_write_scratchpad
                ):
                    return True
                elif (
                    user_project_member.access_level != ProjectRoles.AUDITOR.value and 
                    user_project_member.access_level in ProjectRoles.get_roles_that_can_update_project_notes()
                ):
                    return True
                
        current_app.logger.error(f'User({self.user.id}) does not have permission to view update Project({project.id}) notes in Tenant({project.tenant_id})')
        raise AuthorizationError('User is not authorized to update project notes')
    
    def can_user_view_project_reports(self, project_id: int) -> bool:
        return self.can_user_access_project(project_id)
    
    def can_user_generate_project_reports(self, project_id: int) -> bool:
        return self.can_user_access_project(project_id)
    
    def can_user_view_project_comments(self, project_id: int) -> bool:
        if self._is_super_user():
            return True
        
        project, tenant, roles = self._get_project_with_tenant_and_user_roles(project_id)

        if self._is_tenant_owner(tenant) or self._can_manage_tenant(roles):
            return True
        
        if self._can_access_tenant(roles):
            user_project_member = self._get_project_member(project_id)
            if user_project_member:
                if (
                    user_project_member.access_level == ProjectRoles.AUDITOR.value and
                    project.can_auditor_read_comments
                ):
                    return True
                elif (
                    user_project_member.access_level != ProjectRoles.AUDITOR.value and 
                    user_project_member.access_level in ProjectRoles.values()
                ):
                    return True
                
        current_app.logger.error(f'User({self.user.id}) does not have permission to view Project({project.id}) comments in Tenant({project.tenant_id})')
        raise AuthorizationError('User is not authorized to view project comments')
    
    def can_user_create_project_comment(self, project_id: int) -> bool:
        if self._is_super_user():
            return True
        
        project, tenant, roles = self._get_project_with_tenant_and_user_roles(project_id)

        if self._is_tenant_owner(tenant) or self._can_manage_tenant(roles):
            return True
        
        if self._can_access_tenant(roles):
            user_project_member = self._get_project_member(project_id)
            if user_project_member:
                if (
                    user_project_member.access_level == ProjectRoles.AUDITOR.value and
                    project.can_auditor_write_comments
                ):
                    return True
                elif (
                    user_project_member.access_level != ProjectRoles.AUDITOR.value and 
                    user_project_member.access_level in ProjectRoles.get_roles_that_can_update_project_comments()
                ):
                    return True

        current_app.logger.error(f'User({self.user.id}) does not have permission to update Project({project.id}) comments in Tenant({project.tenant_id})')
        raise AuthorizationError('User is not authorized to manage project comments')
    
    def can_user_delete_project_comment(self, project_id: int, comment_id: int) -> bool:
        if self._is_super_user():
            return True
        
        project, tenant, roles = self._get_project_with_tenant_and_user_roles(project_id)
        
        if self._can_access_tenant(roles):
            comment = ProjectCommentRepository.get_project_comment(comment_id)
            if not comment:
                raise ProjectCommentNotFound()
            
            if comment.owner_id == self.user.id:
                return True
            
            current_app.logger.error(f'User({self.user.id}) does not have permission to delete ProjectComment({comment.id})')
            raise AuthorizationError('User may only delete their own comments')
            
    def can_user_access_project_settings(self, project_id: int) -> bool:
        if self._is_super_user():
            return True
        
        project, tenant, roles = self._get_project_with_tenant_and_user_roles(project_id)

        if self._is_tenant_owner(tenant) or self._can_manage_tenant(roles):
            return True
        
        if self._can_access_tenant(roles):
            user_project_member = self._get_project_member(project_id)
            if user_project_member:
                if (
                    user_project_member.access_level != ProjectRoles.AUDITOR.value and 
                    user_project_member.access_level in ProjectRoles.values()
                ):
                    return True
                
        current_app.logger.error(f'User({self.user.id}) does not have permission to view Project({project.id}) settings')
        raise AuthorizationError('User is not authorized to view project settings')
    
    def can_user_update_project_settings(self, project_id: int) -> bool:
        if self._is_super_user():
            return True
        
        project, tenant, roles = self._get_project_with_tenant_and_user_roles(project_id)

        if self._is_tenant_owner(tenant) or self._can_manage_tenant(roles):
            return True
        
        if self._can_access_tenant(roles):
            user_project_member = self._get_project_member(project_id)
            if (
                user_project_member and
                user_project_member.access_level in ProjectRoles.get_roles_that_can_update_project_settings()
            ):
                return True
                
        current_app.logger.error(f'User({self.user.id}) does not have permission to change Project({project.id}) settings')
        raise AuthorizationError('User is not authorized to change project settings')
    
    def can_user_manage_project_members(self, project_id: int) -> bool:
        if self._is_super_user():
            return True
        
        project, tenant, roles = self._get_project_with_tenant_and_user_roles(project_id)

        if self._is_tenant_owner(tenant) or self._can_manage_tenant(roles):
            return True
        
        if self._can_access_tenant(roles):
            user_project_member = self._get_project_member(project_id)
            if (
                user_project_member and 
                user_project_member.access_level in ProjectRoles.get_roles_that_can_update_project_settings()
            ):
                return True
                
        current_app.logger.error(f'User({self.user.id}) does not have permission to manage Project({project.id}) memebrs')
        raise AuthorizationError('User is not authorized to change project settings')


    '''
    Collection of getters used by other authorization checks.
    TODO:
    Move into appropriate models/repos/services after refactoring them,
    right now there's a slight issue with circular imports.
    '''

    def _get_tenant_and_user_roles(self, tenant_id: int) -> List[Tuple[str, Union[Tenant, List[int]]]]:
        tenant, roles = TenantRepository.get_tenant_with_user_roles(self.user.id, tenant_id)
        print(tenant, roles)
        if not tenant:
            TenantNotFound()
        if not roles:
            current_app.logger.error(f'User({self.user.id}) does not have permission to access Tenant({tenant.id})')
            raise AuthorizationError('User is not authorized access this tenant')
        return tenant, roles
    
    def _get_project_with_tenant_and_user_roles(self, project_id: int):
        project, tenant, roles = ProjectRepository.get_project_with_tenant_and_user_roles(self.user.id, project_id)
        if not tenant:
            raise TenantNotFound()
        if not project:
            raise ProjectNotFound()
        if not roles:
            current_app.logger.error(f'User({self.user.id}) does not have permission to access Tenant({tenant.id})')
            raise AuthorizationError('User is not authorized access this tenant')
        return project, tenant, roles
    
    def _get_user_roles_for_tenant(self, tenant_id: int) -> List[UserRole]:
        return UserRoleRepository.get_all_user_roles_for_tenant(tenant_id)
    
    def _get_project_member(self, project_id: int) -> Optional[ProjectMember]:
        return ProjectMemberRepository.get_project_member(self.user.id, project_id)
    
    '''
    These are shared checks of basic access permissions for a project. They are used
    by all other access checks, before more granular service/view specific checks.
    Change with caution!
    '''

    def _is_super_user(self) -> bool:
        return self.user.super
    
    def _is_tenant_owner(self, tenant: Tenant) -> bool:
        return self.user.id == tenant.owner_id
    
    def _can_access_tenant(self, roles: List[str]) -> bool:
        return bool(set(roles).intersection(TenantRole.get_role_names_with_access_to_tenant()))
        
    def _can_manage_tenant(self, roles: List[str]) -> bool:
        return bool(set(roles).intersection(TenantRole.get_role_names_that_can_manage_tenant()))
    
    def _is_project_member(self, project_id: int) -> bool:
        if not self._get_project_member(project_id):
            return False
        return True
