from flask_login import current_user

from app.repository import ProjectRepository, ProjectCommentRepository
from app.utils.misc import obj_to_dict
from app.utils.notification_service import NotificationService
from app.utils.types import SerializedObjectType

class ProjectCommentService:

    @staticmethod
    def get_project_comments(project_id: int) -> SerializedObjectType:
        comments = ProjectCommentRepository.get_project_comments(project_id)

        data = []
        for comment, author_email in comments:
            comment_dict = obj_to_dict(comment)
            comment_dict['author_email'] = author_email
            data.append(comment_dict)

        return data
    
    @staticmethod
    def add_comment(project_id: int, message: str) -> SerializedObjectType:
        created_comment = ProjectCommentRepository.create_comment(project_id, message)
        project = ProjectRepository.get_project(project_id)
        
        NotificationService.send_email_to_users_tagged_in_project_comment(message, project)

        comment_dict = obj_to_dict(created_comment)
        comment_dict['author_email'] = current_user.email
        return comment_dict
    
    @staticmethod
    def remove_comment(comment_id: int) -> None:
        ProjectCommentRepository.delete_comment(comment_id)
