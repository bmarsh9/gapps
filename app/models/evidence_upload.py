from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4

from app.db import db
from app.utils.mixin_models import LogMixin


class EvidenceUpload(db.Model):
    __tablename__ = 'evidence_uploads'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    filename = db.Column(db.String(100))
    upload_link = db.Column(UUID(as_uuid=True), unique=True, default=uuid4, nullable=False)
    evidence_id = db.Column(db.Integer, db.ForeignKey("evidence.id"), index=True, nullable=False)

    evidence = db.relationship("Evidence", lazy='select', backref=db.backref('evidence_uploads', lazy='joined'))

    def as_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "upload_link": f"api/v1/evidence_upload/{self.upload_link}"
        }
