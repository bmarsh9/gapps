from enum import Enum
from typing import List, Union

class BaseEnum(Enum):
    @classmethod
    def get(cls, value: Union[str, int], default=None) -> Union[str, int]:
        try:
            return cls[value.upper()]
        except KeyError:
            return default

    @classmethod
    def keys(cls) -> List[Union[str, int]]:
        return list(cls.__members__.keys())

    @classmethod
    def values(cls) -> List[Union[str, int]]:
        return [member.value for member in cls]
    
class HttpResponseStatus(BaseEnum):
    OK = 200
    CREATED = 201
    NO_CONTENT = 204
    NOT_MODIFIED = 304
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    INTERNAL_SERVER_ERROR = 500

class FileType(BaseEnum):
    DOCUMENT = "document"
    IMAGE = "image"
    MEDIA = "media"
    UNKNOWN = "unknown"

class DocumentFormat(BaseEnum):
    DOC = "application/msword"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    RTF = "application/rtf"
    TXT = "text/plain"
    ODT = "application/vnd.oasis.opendocument.text"
    XLS = "application/vnd.ms-excel"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ODS = "application/vnd.oasis.opendocument.spreadsheet"
    PPT = "application/vnd.ms-powerpoint"
    PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    ODP = "application/vnd.oasis.opendocument.presentation"
    PDF = "application/pdf"

class TenantRole(BaseEnum):
    admin = 1
    editor = 2
    viewer = 3
    user = 4
    vendor = 5

    @classmethod
    def get_role_ids_with_access_to_tenant(cls) -> List[int]:
        roles_with_access = [cls.admin, cls.editor, cls.viewer, cls.user, cls.vendor]
        return [role.value for role in roles_with_access]

class ProjectControlsFilter(BaseEnum):
    HAS_EVIDENCE = "has_evidence"
    MISSING_EVIDENCE = "missing_evidence"
    IMPLEMENTED = "implemented"
    NOT_IMPLEMENTED = "not_implemented"
    IS_APPLICABLE = "is_applicable"
    NOT_APPLICABLE = "not_applicable"
    COMPLETE = "complete"
    NOT_COMPLETE = "not_complete"

class ProjectSubControlsFilter(BaseEnum):
    AM_OWNER = "am_owner"
    AM_OPERATOR = "am_operator"
    IS_APPLICABLE = "is_applicable"
    NOT_APPLICABLE = "not_applicable"
    HAS_EVIDENCE = "has_evidence"
    MISSING_EVIDENCE = "missing_evidence"
    IMPLEMENTED = "implemented"
    NOT_IMPLEMENTED = "not_implemented"
    COMPLETE = "complete"
    NOT_COMPLETE = "not_complete"
    REVIEW_NOT_STARTED = "review_not_started"
    REVIEW_INFOSEC_ACTION = "review_infosec_action"
    REVIEW_ACTION_REQUIRED = "review_action_required"
    REVIEW_READY_FOR_AUDITOR = "review_ready_for_auditor"
    REVIEW_COMPLETE = "review_complete"

class ProjectControlStatus(BaseEnum):
    NOT_APPLICABLE = "not applicable"
    NOT_STARTED = "not started"
    IN_PROGRESS = "in progress"
    COMPLETE = "complete"

class ProjectSubControlStatus(BaseEnum):
    NOT_STARTED = "not started"
    INFOSEC_ACTION = "infosec action"
    READY_FOR_AUDITOR = "ready for auditor"
    ACTION_REQUIRED = "action required"
    COMPLETE = "complete"