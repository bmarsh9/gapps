from typing import Dict, List, Optional
import json
import os

from flask import current_app, Flask

DEFAULT_LANGUAGE_LIST = ['en']

def get_available_languages() -> List[str]:
    return current_app.config.get('LANGUAGES', DEFAULT_LANGUAGE_LIST)

def load_translations(app: Flask) -> List[Dict[str, Dict[str, str]]]:
    translations = {}
    langs = app.config.get('LANGUAGES', DEFAULT_LANGUAGE_LIST)
    for lang in langs:
        lang_folder = os.path.join(app.root_path, 'translations', lang)
        translations[lang] = {}
        for filename in os.listdir(lang_folder):
            if filename.endswith('.json'):
                category = filename.split('.')[0]
                with open(os.path.join(lang_folder, filename), 'r', encoding='utf-8') as f:
                    translations[lang][category] = json.load(f)
    return translations

def translate(text: str, values: Dict[str, str] = {}, language: Optional[str] = None) -> str:
    available_languages = get_available_languages()
    user_locale = current_app.babel_localeselector()
    user_language = user_locale[:2] if len(user_locale) > 2 else user_locale
    
    if language and language not in available_languages:
        current_app.logger.warning(f'Enforced language ({language}) not found in the list of available languages ({available_languages})')
        language = 'en'
    elif user_language not in available_languages:
        current_app.logger.warning(f'Users preferred language ({user_language}) not found in the list of available languages ({available_languages})')
        user_language = 'en'

    
    category, locale_string = text.split('.', 1)
    if not category or not locale_string:
        return text
    
    language_to_use = language if language else user_language

    translated_string = (
        current_app
            .babel_translations
            .get(language_to_use, {})
            .get(category, {})
            .get(locale_string, None)
    )

    if translated_string is None:
        current_app.logger.warning(f'Could not find translation string for key ({text}) for language ({language_to_use}))')
        return text

    if values:
        for var_name, var_value in values.items():
            placeholder = f'%{var_name}%'
            if placeholder in translated_string:
                translated_string = translated_string.replace(placeholder, str(var_value))
            else:
                current_app.logger.warning(f'Variable {var_name} not found in translation string for key ({text}) for language ({language_to_use})')
    
    return translated_string