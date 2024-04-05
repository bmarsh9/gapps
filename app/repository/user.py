from typing import List, Optional, Tuple, Union
import traceback

from flask import current_app
from flask_login import current_user
from sqlalchemy import func

from app import db
from app.models import (
    ProjectSubControl,
    User
)
from app.utils.custom_errors import PostgresError

class UserRepository:

    @staticmethod
    def get_user_email(user_id: int) -> Optional[str]:
        return User.query.with_entities(User.email).filter_by(id=user_id).scalar()
    
    @staticmethod
    def update_user_locale(new_locale) -> None:
        try:
            User.query.filter_by(id=current_user.id).update({User.locale: new_locale})
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(traceback.format_exc())
            raise PostgresError('Failed to update user locale')

    @staticmethod
    def get_project_user_responsibility_matrix(project_id: int) -> List[Tuple[str, Union[int, str]]]:
        owner_subquery = (
            db.session.query(
                ProjectSubControl.owner_id,
                func.count(ProjectSubControl.id).label('subcontrols')
            )
            .filter(ProjectSubControl.project_id == project_id)
            .group_by(ProjectSubControl.owner_id)
            .subquery()
        )

        operator_subquery = (
            db.session.query(
                ProjectSubControl.operator_id,
                func.count(ProjectSubControl.id).label('subcontrols')
            )
            .filter(ProjectSubControl.project_id == project_id)
            .group_by(ProjectSubControl.operator_id)
            .subquery()
        )

        owner_alias = db.aliased(owner_subquery)
        operator_alias = db.aliased(operator_subquery)

        query = (
            db.session.query(
                User.id,
                User.email,
                func.coalesce(owner_alias.c.subcontrols, 0).label('owned_subcontrols'),
                func.coalesce(operator_alias.c.subcontrols, 0).label('operated_subcontrols')
            )
            .outerjoin(owner_alias, User.id == owner_alias.c.owner_id)
            .outerjoin(operator_alias, User.id == operator_alias.c.operator_id)
        )

        return query.all()
