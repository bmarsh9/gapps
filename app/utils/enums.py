from enum import Enum

class BaseEnum(Enum):
    @classmethod
    def get(cls, value, default=None):
        try:
            return cls[value.upper()]
        except KeyError:
            return default

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
