from typing import Optional

from app.localization import get_available_languages
from app.repository import UserRepository
from app.utils.custom_errors import LocaleNotFound, UserNotFound

class UserService:

    @staticmethod
    def get_user_email_or_raise_404(user_id: int) -> Optional[str]:
        email = UserRepository.get_user_email(user_id)
        if not email:
            raise UserNotFound()
        return email
    
    @staticmethod
    def update_user_locale(new_locale: str) -> None:
        available_languages = get_available_languages()
        if not new_locale or new_locale not in available_languages:
            raise LocaleNotFound(f'Submitted locale ({new_locale}) is not in the list of available languages ({available_languages})')
        UserRepository.update_user_locale(new_locale)
