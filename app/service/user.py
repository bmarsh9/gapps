from typing import Optional

from app.repository import UserRepository
from app.utils.custom_errors import UserNotFound

class UserService:

    @staticmethod
    def get_user_email_or_raise_404(user_id: int) -> Optional[str]:
        email = UserRepository.get_user_email(user_id)
        if not email:
            raise UserNotFound()
        return email
