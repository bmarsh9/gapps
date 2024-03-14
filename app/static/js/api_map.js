const apiUrl = `${location.protocol}//${location.host}/api/v1`;

const apiMap = {
  getProjectSummaryUrl: (projectId) => `${apiUrl}/projects/${projectId}`,
  getProjectControlsUrl: (projectId) => `${apiUrl}/projects/${projectId}/controls`,
  getProjectSubControlsUrl: (projectId) => `${apiUrl}/projects/${projectId}/subcontrols`,
  getProjectPoliciesUrl: (projectId) => `${apiUrl}/projects/${projectId}/policies`,
  getProjectEvidenceUrl: (projectId) => `${apiUrl}/projects/${projectId}/evidence`
}
