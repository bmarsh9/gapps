from app.service.project import ProjectService
from app.utils.reports import Report

class ProjectReportService:

    @staticmethod
    def generate_project_report(project_id: int) -> str:
        project = ProjectService.get_project_or_404(project_id)
        return Report().generate(project)
