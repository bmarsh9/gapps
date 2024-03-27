from typing import List, Tuple, Optional, Union
import traceback

from flask import current_app
from flask_login import current_user
from sqlalchemy import asc

from app import db
from app.models import ProjectComment, User
from app.utils.custom_errors import PostgresError

class ProjectCommentRepository:

    @staticmethod
    def get_project_comment(comment_id: int) -> Optional[ProjectComment]:
        return ProjectComment.query.get(comment_id)

    @staticmethod
    def get_project_comments(project_id: int) -> List[Tuple[str, Union[ProjectComment, str]]]:
        return (
            db.session.query(
                ProjectComment,
                User.email.label("author_email"),
            )
            .join(User, User.id == ProjectComment.owner_id)
            .filter(ProjectComment.project_id == project_id)
            .order_by(asc(ProjectComment.date_added))
        ).all()
    
    @staticmethod
    def create_comment(project_id: int, message: str) -> ProjectComment:
        try:
            new_comment = ProjectComment(
                message = message,
                owner_id = current_user.id,
                project_id = project_id
            )

            db.session.add(new_comment)
            db.session.commit()

            return new_comment
        
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(traceback.format_exc())
            raise PostgresError("An error occurred while attempting to add comment")
    
    @staticmethod
    def delete_comment(comment_id: int) -> None:
        try:
            ProjectComment.query.filter_by(id=comment_id).delete()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(traceback.format_exc())
            raise PostgresError("An error occurred while attempting to delete comment")
