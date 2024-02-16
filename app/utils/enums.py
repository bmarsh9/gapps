from enum import Enum

class BaseEnum(Enum):
    @classmethod
    def get(cls, value, default=None):
        try:
            return cls[value.upper()]
        except KeyError:
            return default

    @classmethod
    def keys(cls):
        return list(cls.__members__.keys())

    @classmethod
    def values(cls):
        return [member.value for member in cls]

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
    def get_role_ids_with_access_to_tenant(cls):
        roles_with_access = [cls.admin, cls.editor, cls.viewer, cls.user, cls.vendor]
        return [role.value for role in roles_with_access]
