const apiUrl = `${location.protocol}//${location.host}/api/v1`;

const apiMap = {
  getLanguagesUrl: () => `${apiUrl}/languages`,
  getUpdateUserLocaleUrl: () => `${apiUrl}/locale`,

  getTenantUsersUrl: (tenantId) => `${apiUrl}/tenants/${tenantId}/users`,

  getProjectSummaryUrl: (projectId) => `${apiUrl}/projects/${projectId}`,
  getProjectControlsUrl: (projectId) => `${apiUrl}/projects/${projectId}/controls`,
  getProjectSubControlsUrl: (projectId) => `${apiUrl}/projects/${projectId}/subcontrols`,
  getProjectPoliciesUrl: (projectId) => `${apiUrl}/projects/${projectId}/policies`,
  getProjectEvidenceUrl: (projectId) => `${apiUrl}/projects/${projectId}/evidence`,
  getProjectResponsibilityMatrixUrl: (projectId) => `${apiUrl}/projects/${projectId}/matrix`,
  getProjectScratchPadUrl: (projectId) => `${apiUrl}/projects/${projectId}/scratchpad`,
  getProjectCommentsUrl: (projectId) => `${apiUrl}/projects/${projectId}/comments`,
  getProjectDeleteCommentUrl: (projectId, commentId) => `${apiUrl}/projects/${projectId}/comments/${commentId}`,
  getProjectReportsUrl: (projectId) => `${apiUrl}/projects/${projectId}/reports`,
  getProjectSettingsUrl: (projectId) => `${apiUrl}/projects/${projectId}/settings`,
  getProjectAddMemberUrl: (projectId) => `${apiUrl}/projects/${projectId}/members`,
  getProjectRemoveMemberUrl: (projectId, userId) => `${apiUrl}/projects/${projectId}/members/${userId}`,
  getProjectUpdateMemberAccessLevelUrl: (projectId, userId) => `${apiUrl}/projects/${projectId}/members/${userId}/access`,

  getProjectControlSummaryUrl: (projectId, controlId) => `${apiUrl}/projects/${projectId}/controls/${controlId}`,
  
  getUpdateOwnerOperatorUrl: (projectId, subControlId) => `${apiUrl}/project-controls/${projectId}/subcontrols/${subControlId}`,
}
