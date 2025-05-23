from sqlalchemy import func, distinct, case
from sqlalchemy.orm import validates
from app.utils.mixin_models import (
    DateMixin,
    SubControlMixin,
    ControlMixin,
    QueryMixin,
    AuthorizerMixin,
)
from flask_login import UserMixin
from flask import current_app, render_template, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.datastructures import FileStorage
from datetime import datetime
from sqlalchemy.event import listens_for
from app import db, login
from uuid import uuid4
from app.utils import misc
import arrow
import json
import os
from string import Formatter
from app.email import send_email
from random import randrange
from app.utils.authorizer import Authorizer
import email_validator
from werkzeug.utils import secure_filename
import shutil
import random
import logging
import shortuuid
from app.utils.file_handler import FileStorageHandler
from typing import List
from app.utils.exceptions import FileDoesNotExist


class Finding(db.Model):
    __tablename__ = "findings"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    title = db.Column(db.String())
    description = db.Column(db.String())
    mitigation = db.Column(db.String())
    status = db.Column(db.String(), default="open")
    risk = db.Column(db.Integer(), default=0)
    project_id = db.Column(db.String, db.ForeignKey("projects.id"))
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    @staticmethod
    def get_status_list():
        return ["open", "in progress", "closed"]

    @validates("status")
    def _validate_status(self, key, status):
        if not status or status.lower() not in Finding.get_status_list():
            raise ValueError("invalid status")
        return status

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return data


class VendorFile(db.Model, QueryMixin):
    __tablename__ = "vendor_files"
    __table_args__ = (db.UniqueConstraint("name", "vendor_id"),)
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    name = db.Column(db.String())
    description = db.Column(db.String())
    provider = db.Column(db.String(), nullable=False)
    collected_on = db.Column(db.DateTime, default=datetime.utcnow)
    vendor_id = db.Column(db.String, db.ForeignKey("vendors.id"), nullable=False)
    owner_id = db.Column(db.String, db.ForeignKey("users.id"), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return data

    def get_file(self):
        storage_method = current_app.config["STORAGE_METHOD"]
        if self.provider != storage_method:
            abort(
                500,
                f"Storage method mismatch. File provider:{self.provider}. STORAGE_METHOD:{storage_method}",
            )

        file_handler = FileStorageHandler(
            provider=current_app.config["STORAGE_METHOD"],
        )
        return file_handler.get_file(path=os.path.join(self.vendor_id, self.name))

    def save_file(self, file_object):
        storage_method = current_app.config["STORAGE_METHOD"]
        if self.provider != storage_method:
            abort(
                500,
                f"Storage method mismatch. File provider:{self.provider}. STORAGE_METHOD:{storage_method}",
            )

        if storage_method == "local":
            folder = self.vendor.create_evidence_folder()

        upload_params = {
            "file": file_object,
            "file_name": f"{self.id}_{self.name}",
            "folder": self.vendor.get_evidence_folder(storage_method),
        }
        file_handler = FileStorageHandler(provider=storage_method)
        return file_handler.upload_file(**upload_params)

    @validates("provider")
    def _validate_provider(self, key, value):
        if value not in current_app.config["STORAGE_PROVIDERS"]:
            return ValueError(f"Provider:{value} not supported")
        return value


class AppHistory(db.Model, QueryMixin):
    __tablename__ = "app_history"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    icon = db.Column(db.String())
    user_id = db.Column(db.String, db.ForeignKey("users.id"), nullable=False)
    app_id = db.Column(db.String, db.ForeignKey("vendor_apps.id"), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return data


class VendorHistory(db.Model, QueryMixin):
    __tablename__ = "vendor_history"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    icon = db.Column(db.String())
    user_id = db.Column(db.String, db.ForeignKey("users.id"), nullable=False)
    vendor_id = db.Column(db.String, db.ForeignKey("vendors.id"), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return data


class Form(db.Model, QueryMixin):
    __tablename__ = "forms"
    __table_args__ = (db.UniqueConstraint("name", "tenant_id"),)
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String())
    sections = db.relationship(
        "FormSection",
        backref="form",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    assessment_id = db.Column(db.String)
    tenant_id = db.Column(db.String, db.ForeignKey("tenants.id"), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}

        # If not attached to an assessment, it's a template
        data["is_template"] = True
        if self.assessment_id:
            data["is_template"] = False

        data["sections"] = []
        for section in self.sections.all():
            data["sections"].append(section.as_dict())

        if assessment := Assessment.query.filter(Assessment.form_id == self.id).first():
            data["assessment_name"] = assessment.name
            data["assessment_id"] = assessment.id
        return data

    def get_section(self, title):
        return self.sections.filter(
            func.lower(FormSection.title) == func.lower(title)
        ).first()

    def get_section_by_id(self, id):
        return self.sections.filter(func.lower(FormSection.id) == id).first()

    def get_items(self, edit_mode=None, flatten=False):
        """
        edit_mode: return all items, even disabled ones
        flatten: return only the items, otherwise return the items as a list in the section
        """
        items = []
        for section in self.sections.all():
            section_data = section.as_dict(edit_mode=edit_mode)
            if edit_mode or section_data["questions"]:
                if flatten:
                    for record in section_data.get("items"):
                        items.append(record)
                else:
                    items.append(section_data)
        return items

    def create_section(self, title, order=1):
        if not order:
            if latest_item := self.sections.order_by(FormSection.order.desc()).first():
                order = latest_item.order
            else:
                order = 1
        section = FormSection(title=title, order=order)
        self.sections.append(section)
        db.session.commit()
        return section


class VendorApp(db.Model, QueryMixin):
    __tablename__ = "vendor_apps"
    __table_args__ = (db.UniqueConstraint("name", "vendor_id"),)
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    name = db.Column(db.String(64), unique=True, nullable=False)
    disabled = db.Column(db.Boolean, default=False)
    description = db.Column(db.String())
    contact_email = db.Column(db.String())
    notes = db.Column(db.String())
    criticality = db.Column(db.String(), default="unknown")
    approved_use_cases = db.Column(db.String())
    exceptions = db.Column(db.String())
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    category = db.Column(db.String(), default="general")
    business_unit = db.Column(db.String(), default="general")
    last_reviewed = db.Column(db.DateTime)
    review_cycle = db.Column(db.Integer, default=12)
    review_status = db.Column(db.String(), default="new")
    status = db.Column(db.String(), default="pending")

    is_on_premise = db.Column(db.Boolean(), default=False)
    is_saas = db.Column(db.Boolean(), default=False)
    owner_id = db.Column(db.String, db.ForeignKey("users.id"), nullable=False)
    data_class_id = db.Column(db.String, db.ForeignKey("data_class.id"), nullable=True)
    vendor_id = db.Column(db.String, db.ForeignKey("vendors.id"), nullable=False)
    tenant_id = db.Column(db.String, db.ForeignKey("tenants.id"), nullable=False)
    history = db.relationship(
        "AppHistory", backref="app", lazy="dynamic", cascade="all, delete-orphan"
    )
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    VALID_CRITICALITY = ["unknown", "low", "moderate", "high"]
    VALID_REVIEW_STATUS = [
        "new",
        "pending_response",
        "pending_review",
        "info_required",
        "complete",
    ]
    VALID_STATUS = ["pending", "approved", "not approved"]

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["risk"] = random.randint(0, 101)
        data["next_review_date"] = self.get_next_review_date()
        data["type"] = "application"
        data["vendor"] = self.vendor.name
        if self.data_class_id:
            data["data_classification"] = self.data_class.name
            data["data_classification_color"] = self.data_class.color

        data["next_review_date"] = self.get_next_review_date()
        data["days_until_next_review_date"] = self.days_until_next_review()
        data["next_review_date_humanize"] = self.days_until_next_review(humanize=True)

        data["review_description"] = "compliant"
        if not self.last_reviewed:
            data["review_description"] = "never reviewed"
        else:
            data["last_reviewed"] = arrow.get(self.last_reviewed).format("YYYY-MM-DD")

        data["review_upcoming"] = False
        if data["days_until_next_review_date"] <= 14:
            data["review_upcoming"] = True
            if self.last_reviewed:
                data["review_description"] = "upcoming review"

        data["review_past_due"] = False
        if data["days_until_next_review_date"] <= 0:
            data["review_past_due"] = True
            if self.last_reviewed:
                data["review_description"] = "past due"

        return data

    def days_until_next_review(self, humanize=False):
        next_review_date = self.get_next_review_date()
        if humanize:
            return arrow.get(next_review_date).humanize(granularity=["day"])
        return (arrow.get(next_review_date).date() - arrow.utcnow().date()).days

    def is_ready_for_review(self, grace_period=7):
        today = arrow.get(arrow.utcnow().format("YYYY-MM-DD"))
        future_date = today.shift(days=grace_period)
        next_review_date = arrow.get(self.get_next_review_date())
        if future_date >= next_review_date:
            return True
        return False

    def get_next_review_date(self):
        if not self.last_reviewed:
            return arrow.utcnow().format("YYYY-MM-DD")
        if not self.review_cycle:
            return arrow.utcnow().format("YYYY-MM-DD")
        return (
            arrow.get(self.last_reviewed)
            .shift(months=self.review_cycle)
            .format("YYYY-MM-DD")
        )

    @validates("contact_email")
    def _validate_email(self, key, address):
        if address:
            try:
                email_validator.validate_email(address, check_deliverability=False)
            except:
                abort(422, "Invalid email")
        return address

    @validates("status")
    def _validate_status(self, key, value):
        if value.lower() not in self.VALID_STATUS:
            raise ValueError(f"Invalid status: {value}")
        return value.lower()

    @validates("review_status")
    def _validate_review_status(self, key, value):
        if value.lower() not in self.VALID_REVIEW_STATUS:
            raise ValueError(f"Invalid review status: {value}")
        return value.lower()

    @validates("criticality")
    def _validate_criticality(self, key, value):
        value = value or "unknown"
        if value.lower() not in self.VALID_CRITICALITY:
            raise ValueError(f"Invalid criticality: {value}")
        return value.lower()


class Vendor(db.Model, QueryMixin):
    __tablename__ = "vendors"
    __table_args__ = (db.UniqueConstraint("name", "tenant_id"),)
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String())
    contact_email = db.Column(db.String())
    vendor_contact_email = db.Column(db.String())
    location = db.Column(db.String())
    disabled = db.Column(db.Boolean(), default=False)
    review_status = db.Column(db.String(), default="new")
    status = db.Column(db.String(), default="pending")
    notes = db.Column(db.String())
    review_cycle = db.Column(db.Integer, default=12)
    last_reviewed = db.Column(db.DateTime)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    criticality = db.Column(db.String(), default="unknown")
    history = db.relationship(
        "VendorHistory", backref="vendor", lazy="dynamic", cascade="all, delete-orphan"
    )
    apps = db.relationship(
        "VendorApp", backref="vendor", lazy="dynamic", cascade="all, delete-orphan"
    )
    files = db.relationship(
        "VendorFile", backref="vendor", lazy="dynamic", cascade="all, delete-orphan"
    )
    assessments = db.relationship(
        "Assessment", backref="vendor", lazy="dynamic", cascade="all, delete-orphan"
    )
    data_class_id = db.Column(db.String, db.ForeignKey("data_class.id"), nullable=True)
    tenant_id = db.Column(db.String, db.ForeignKey("tenants.id"), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    VALID_CRITICALITY = ["unknown", "low", "moderate", "high"]
    VALID_REVIEW_STATUS = [
        "new",
        "pending_response",
        "pending_review",
        "info_required",
        "complete",
    ]
    VALID_STATUS = ["pending", "approved", "not approved"]

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["risk"] = random.randint(0, 101)
        if self.data_class_id:
            data["data_classification"] = self.data_class.name
        data["application_count"] = self.apps.count()
        data["assessment_count"] = self.apps.count()
        data["next_review_date"] = self.get_next_review_date()
        data["days_until_next_review_date"] = self.days_until_next_review()
        data["next_review_date_humanize"] = self.days_until_next_review(humanize=True)

        data["review_description"] = "compliant"
        if not self.last_reviewed:
            data["review_description"] = "never reviewed"
        else:
            data["last_reviewed"] = arrow.get(self.last_reviewed).format("YYYY-MM-DD")

        data["review_upcoming"] = False
        if data["days_until_next_review_date"] <= 14:
            data["review_upcoming"] = True
            if self.last_reviewed:
                data["review_description"] = "upcoming review"

        data["review_past_due"] = False
        if data["days_until_next_review_date"] <= 0:
            data["review_past_due"] = True
            if self.last_reviewed:
                data["review_description"] = "past due"

        data["type"] = "vendor"
        return data

    def create_evidence_folder(self):
        return self.tenant.create_vendor_evidence_folder(vendor_id=self.id)

    def get_evidence_folder(self):
        return self.tenant.get_vendor_evidence_folder(vendor_id=self.id)

    def days_until_next_review(self, humanize=False):
        next_review_date = self.get_next_review_date()
        if humanize:
            return arrow.get(next_review_date).humanize(granularity=["day"])
        return (arrow.get(next_review_date).date() - arrow.utcnow().date()).days

    def is_ready_for_review(self, grace_period=7):
        today = arrow.get(arrow.utcnow().format("YYYY-MM-DD"))
        future_date = today.shift(days=grace_period)
        next_review_date = arrow.get(self.get_next_review_date())
        if future_date >= next_review_date:
            return True
        return False

    def get_next_review_date(self):
        if not self.last_reviewed:
            return arrow.utcnow().format("YYYY-MM-DD")
        if not self.review_cycle:
            return arrow.utcnow().format("YYYY-MM-DD")
        return (
            arrow.get(self.last_reviewed)
            .shift(months=self.review_cycle)
            .format("YYYY-MM-DD")
        )

    @validates("contact_email", "vendor_contact_email")
    def _validate_email(self, key, address):
        try:
            email_validator.validate_email(address, check_deliverability=False)
        except:
            abort(422, "Invalid email")
        return address

    @validates("status")
    def _validate_status(self, key, value):
        if value.lower() not in self.VALID_STATUS:
            raise ValueError(f"Invalid status: {value}")
        return value.lower()

    @validates("review_status")
    def _validate_review_status(self, key, value):
        if value.lower() not in self.VALID_REVIEW_STATUS:
            raise ValueError(f"Invalid review status: {value}")
        return value.lower()

    @validates("criticality")
    def _validate_criticality(self, key, value):
        value = value or "unknown"
        if value.lower() not in self.VALID_CRITICALITY:
            raise ValueError(f"Invalid criticality: {value}")
        return value.lower()

    def create_history(self, name, description, user_id, icon=None):
        record = VendorHistory(
            name=name, description=description, icon=icon, user_id=user_id
        )
        self.history.append(record)
        db.session.commit()
        return record

    def get_assessments(self):
        return Assessment.query.filter(Assessment.vendor_id == self.id).all()

    def get_categories(self):
        records = (
            VendorApp.query.filter(VendorApp.tenant_id == self.tenant_id)
            .distinct(VendorApp.category)
            .all()
        )
        return [record.category for record in records]

    def get_bus(self):
        records = (
            VendorApp.query.filter(VendorApp.tenant_id == self.tenant_id)
            .distinct(VendorApp.business_unit)
            .all()
        )
        return [record.business_unit for record in records]

    def create_assessment(
        self,
        name,
        description,
        owner_id,
        due_date=None,
        vendor_id=None,
        clone_from=None,
    ):
        if (
            Assessment.query.filter(Assessment.vendor_id == self.id)
            .filter(func.lower(Assessment.name) == func.lower(name))
            .first()
        ):
            abort(422, f"Name already exists: {name}")

        if not due_date:
            due_date = str(arrow.utcnow().shift(days=+30))

        # TODO - update
        assessment = Assessment(
            name=name.lower(),
            description=description,
            due_before=due_date,
            owner_id=owner_id,
            tenant_id=self.tenant_id,
        )
        self.assessments.append(assessment)
        db.session.commit()

        form = self.tenant.create_form(
            name=f"Form for {name}",
            description=f"Form for {name}",
            assessment_id=assessment.id,
            clone_from=clone_from,
        )
        assessment.form_id = form.id
        db.session.commit()
        return assessment

    def create_app(self, name, **kwargs):
        if not name:
            abort(422, "Name is required")
        if (
            VendorApp.query.filter(VendorApp.vendor_id == self.id)
            .filter(func.lower(VendorApp.name) == func.lower(name))
            .first()
        ):
            abort(422, f"Name already exists: {name}")

        # TODO - check if requested data class is below vendor approved data class
        # if data_classification := kwargs.get("data_classification"):
        #     self.data_class ...

        app = VendorApp(
            name=name.lower(),
            **kwargs,
            tenant_id=self.tenant_id,
        )
        self.apps.append(app)
        db.session.commit()
        return app

    def create_file(self, name, file_object, owner_id, description=None, provider=None):
        """
        Create file

        Args
            name (str): file name
            file_object (object): request.files['file']
            owner_id: user id of the uploader
        """
        if provider is None:
            provider = current_app.config["STORAGE_METHOD"]

        if self.files.filter(func.lower(VendorFile.name) == func.lower(name)).first():
            abort(422, f"File already exists with the name: {name}")

        if provider not in current_app.config["STORAGE_PROVIDERS"]:
            abort(422, f"Provider not supported:{provider}")

        file = VendorFile(
            name=name.lower(),
            owner_id=owner_id,
            description=description,
            provider=provider,
        )
        self.files.append(file)
        file.save_file(file_object)
        try:
            # file.save_file(file_object)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            abort(500, f"Failed up upload file: {e}")
        return file


class DataClass(db.Model, QueryMixin):
    __tablename__ = "data_class"
    __table_args__ = (db.UniqueConstraint("name", "tenant_id"),)
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    name = db.Column(db.String(64), nullable=False)
    order = db.Column(db.Integer)
    color = db.Column(db.String)
    vendors = db.relationship("Vendor", backref="data_class", lazy="dynamic")
    apps = db.relationship("VendorApp", backref="data_class", lazy="dynamic")
    tenant_id = db.Column(db.String, db.ForeignKey("tenants.id"), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)


class Tenant(db.Model, QueryMixin, AuthorizerMixin):
    __tablename__ = "tenants"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    name = db.Column(db.String, nullable=False)
    logo_ref = db.Column(db.String())
    contact_email = db.Column(db.String())
    license = db.Column(
        db.String(),
        server_default="gold",
        info={"authorizer": {"update": Authorizer.can_user_manage_platform}},
    )
    is_default = db.Column(db.Boolean(), default=False)
    approved_domains = db.Column(db.String())
    magic_link_login = db.Column(db.Boolean(), default=False)
    ai_enabled = db.Column(db.Boolean(), default=True)
    ai_token_usage = db.Column(db.Integer(), default=0)
    ai_token_cap = db.Column(db.Integer(), default=500)
    user_cap = db.Column(db.Integer(), default=500)
    project_cap = db.Column(db.Integer(), default=2)
    storage_cap = db.Column(db.String(), default="10000000")
    data_class = db.relationship(
        "DataClass", backref="tenant", lazy="dynamic", cascade="all, delete-orphan"
    )
    members = db.relationship(
        "TenantMember", backref="tenant", lazy="dynamic", cascade="all, delete-orphan"
    )
    frameworks = db.relationship(
        "Framework", backref="tenant", lazy="dynamic", cascade="all, delete-orphan"
    )
    projects = db.relationship(
        "Project", backref="tenant", lazy="dynamic", cascade="all, delete-orphan"
    )
    policies = db.relationship(
        "Policy", backref="tenant", lazy="dynamic", cascade="all, delete-orphan"
    )
    controls = db.relationship(
        "Control", backref="tenant", lazy="dynamic", cascade="all, delete-orphan"
    )
    tags = db.relationship(
        "Tag", backref="tenant", lazy="dynamic", cascade="all, delete-orphan"
    )
    forms = db.relationship(
        "Form", backref="tenant", lazy="dynamic", cascade="all, delete-orphan"
    )
    assessments = db.relationship(
        "Assessment", backref="tenant", lazy="dynamic", cascade="all, delete-orphan"
    )
    vendors = db.relationship(
        "Vendor", backref="tenant", lazy="dynamic", cascade="all, delete-orphan"
    )
    risks = db.relationship(
        "RiskRegister", backref="tenant", lazy="dynamic", cascade="all, delete-orphan"
    )
    owner_id = db.Column(db.String, db.ForeignKey("users.id"), nullable=False)
    labels = db.relationship(
        "PolicyLabel", backref="tenant", lazy="dynamic", cascade="all, delete-orphan"
    )
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    VALID_LICENSE = ["trial", "silver", "gold"]

    def add_log(self, **kwargs):
        return Logs.add(tenant_id=self.id, **kwargs)

    def get_logs(self, **kwargs):
        return Logs.get(tenant_id=self.id, **kwargs)

    @staticmethod
    def get_default_tenant():
        return Tenant.query.filter(Tenant.is_default).first()

    def get_members(self):
        members = []
        for member in self.members.all():
            user = member.user.as_dict()
            roles = [role.name for role in member.roles.all()]
            user["roles"] = roles
            if "vendor" in roles:
                user["is_vendor"] = True
            user.pop("tenants", None)
            members.append(user)
        return members

    def send_member_email_invite(self, user):
        """
        Send email invite to a member of the tenant
        """
        response = {"access_link": None, "sent-email": False}

        if not self.has_member(user):
            response["message"] = "User is not a member of tenant"
            return response

        token = User.generate_invite_token(
            email=user.email, expiration=604800, attributes={"tenant": self.name}
        )
        link = "{}{}?token={}".format(current_app.config["HOST_NAME"], "accept", token)
        response["access_link"] = link

        if not current_app.is_email_configured:
            response["message"] = "Email is not configured"
            return response

        title = f"{current_app.config['APP_NAME']}: Tenant invite"
        content = f"You have been added to a new tenant: {self.name.capitalize()}"
        send_email(
            title,
            recipients=[user.email],
            text_body=render_template(
                "email/basic_template.txt",
                title=title,
                content=content,
                button_link=link,
            ),
            html_body=render_template(
                "email/basic_template.html",
                title=title,
                content=content,
                button_link=link,
            ),
        )
        response["sent-email"] = True
        response["access_link"] = link
        return response

    def has_member(self, user_or_email, get_user_object=False):
        if (
            isinstance(user_or_email, TenantMember)
            and user_or_email.tenant_id == self.id
        ):
            if get_user_object:
                return user_or_email.user
            return user_or_email

        if not (user := User.email_to_object(user_or_email)):
            return None

        if member := self.members.filter(TenantMember.user_id == user.id).first():
            if get_user_object:
                return user
        return member

    def get_roles_for_member(self, user_or_email):
        if not (user := self.has_member(user_or_email)):
            return []
        return [role.name for role in user.roles.all()]

    def has_member_with_role(self, user_or_email, role_name):
        if not role_name:
            return False
        if not (user := self.has_member(user_or_email)):
            return False
        if role_name.lower() in self.get_roles_for_member(user):
            return True
        return False

    def add_member(
        self,
        user_or_email,
        attributes={},
        send_notification=False,
    ):
        """
        Add user to the tenant. If user does not exist, they will be created and then added to tenant

        user_or_email: user object or email address
        attributes: see User class
        send_notification: send email notification

        Usage:
        response, user = tenant.add_member(
            user_or_email=data.get("email"),
            attributes={"roles": data.get("roles", [])},
            send_notification=True
        )
        """
        roles = self.get_default_roles(attributes.get("roles"))
        attributes.pop("roles", None)

        # User already exists
        if isinstance(user_or_email, User):
            user = user_or_email
            email = user.email

        # User does not exist
        else:
            email = user_or_email
            user = User.find_by_email(email)

        can_we_invite, error = self.can_we_invite_user(email)
        if not can_we_invite:
            abort(500, error)

        # If the user does not exist, create them
        if not user:
            user = User.add(email, **attributes, return_user_object=True)

        new_member = TenantMember(user_id=user.id, tenant_id=self.id)
        db.session.add(new_member)
        db.session.commit()

        # Set roles for the member
        self.patch_roles_for_member(user, role_names=roles)

        response = {
            "id": user.id,
            "success": True,
            "message": f"Added {user.email} to {self.name}",
            "sent-email": False,
            "confirm_code": user.email_confirm_code,
        }
        if send_notification:
            # haaaa
            email_invite = self.send_member_email_invite(user)
            response["sent-email"] = email_invite["sent-email"]
            response["access_link"] = email_invite["access_link"]

        return response, user

    def patch_roles_for_member(self, user, role_names):
        """
        Replaces a user's roles with new ones. Pass an empty list to remove all roles
        """
        member = self.has_member(user)
        if not member:
            raise ValueError(f"User {user.email} is not a member of {self.name}")

        new_roles = []
        for role_name in role_names:
            role = Role.find_by_name(role_name)
            if role:
                new_roles.append(role)

        member.roles = new_roles
        db.session.commit()
        return member

    def remove_member(self, user):
        """
        Removes a user from the tenant.
        """
        member = self.has_member(user)
        if member:
            db.session.delete(member)
            db.session.commit()
        return True

    def add_role_for_member(self, user, role_names):
        """
        Adds roles to a user in the tenant without affecting existing roles.

        :param user: User object to update
        :param role_names: List of role names (strings) to add
        """
        member = TenantMember.query.filter_by(
            user_id=user.id, tenant_id=self.id
        ).first()

        if not member:
            raise ValueError(f"User {user.email} is not a member of {self.name}")

        for role_name in role_names:
            role = Role.find_by_name(role_name)
            if role and role not in member.roles:
                member.roles.append(role)

        db.session.commit()
        return member

    def remove_role_for_member(self, user, role_names):
        """
        Removes roles from a user in the tenant without affecting other roles.

        :param user: User object to update
        :param role_names: List of role names (strings) to remove
        """
        member = TenantMember.query.filter_by(
            user_id=user.id, tenant_id=self.id
        ).first()

        if not member:
            raise ValueError(f"User {user.email} is not a member of {self.name}")

        for role_name in role_names:
            role = Role.find_by_name(role_name)
            if role and role in member.roles:
                member.roles.remove(role)

        db.session.commit()
        return member

    @validates("license")
    def _validate_license(self, key, value):
        if value not in self.VALID_LICENSE:
            raise ValueError(f"Invalid license: {value}")
        return value

    @validates("contact_email")
    def _validate_email(self, key, address):
        if address:
            try:
                email_validator.validate_email(address, check_deliverability=False)
            except:
                abort(422, "Invalid email")
        return address

    @validates("name")
    def _validate_name(self, key, name):
        special_characters = "!\"#$%&'()*+,-./:;<=>?@[\]^`{|}~"
        if any(c in special_characters for c in name):
            raise ValueError("Illegal characters in name")
        return name

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["owner_email"] = self.get_owner_email()
        data["approved_domains"] = []
        if self.approved_domains:
            data["approved_domains"] = self.approved_domains.split(",")
        return data

    def populate_data_classification(self):
        if self.data_class.count():
            return True

        defaults = [
            {"name": "restricted", "order": 1, "color": "red"},
            {"name": "confidential", "order": 2, "color": "orange"},
            {"name": "internal", "order": 3, "color": "yellow"},
            {"name": "public", "order": 4, "color": "green"},
        ]
        for record in defaults:
            dc = DataClass(
                name=record["name"], order=record["order"], color=record["color"]
            )
            self.data_class.append(dc)

        db.session.commit()
        return True

    def get_form_templates(self):
        return self.forms.filter(Form.assessment_id == None).all()

    def create_form(
        self,
        name,
        description=None,
        assessment_id=None,
        clone_from=None,
    ):
        """
        Create form for a tenant

        assessment_id: Attach the form to an existing assessment
        clone_form: Makes a clone of an existing form if supplied with the form ID
        """

        clone = None
        if clone_from:
            clone = self.forms.filter(Form.id == clone_from).first()
            if not clone:
                abort(400, f"Form: {clone_from} not found in the tenant")

        form = Form(
            name=name,
            description=description,
            assessment_id=assessment_id,
        )

        if clone:
            for section in clone.sections.all():
                new_section = FormSection(title=section.title, order=section.order)
                for item in section.items.all():
                    new_item = FormItem(
                        data_type=item.data_type,
                        order=item.order,
                        editable=item.editable,
                        disabled=item.disabled,
                        applicable=item.applicable,
                        score=item.score,
                        critical=item.critical,
                        attributes=item.attributes,
                        rule=item.rule,
                        rule_action=item.rule_action,
                    )
                    new_section.items.append(new_item)
                form.sections.append(new_section)

        self.forms.append(form)
        db.session.commit()

        if not clone:
            form.create_section(title="general")
        return form

    def create_risk(
        self,
        title,
        description=None,
        remediation=None,
        tags=[],
        assignee=None,
        enabled=True,
        status="new",
        risk="unknown",
        priority="unknown",
        project_id=None,
        vendor_id=None,
    ):
        risk = RiskRegister(
            title=title,
            description=description,
            remediation=remediation,
            enabled=enabled,
            status=status,
            risk=risk,
            priority=priority,
            project_id=project_id,
            vendor_id=vendor_id,
        )
        if tags:
            if not isinstance(tags, list):
                tags = [tags]

            for name in tags:
                tag = Tag(name=name, tenant_id=self.id)
                risk.tags.append(tag)

        if assignee:
            user = self.has_member(assignee, get_user_object=True)
            if not user:
                abort(
                    422, f"User:{assignee} does not exist or not a member of the tenant"
                )
            risk.assignee = user.id
        self.risks.append(risk)
        db.session.commit()
        return risk

    def create_vendor(self, name, contact_email):
        vendor = Vendor.find_by("name", name, tenant_id=self.id)
        if vendor:
            abort(422, f"Vendor already exists with name: {name}")

        vendor = Vendor(name=name.lower(), contact_email=contact_email)
        self.vendors.append(vendor)
        db.session.commit()
        return vendor

    def get_owner_email(self):
        if not (user := User.query.get(self.owner_id)):
            return "unknown"
        return user.email

    def get_valid_frameworks(self):
        frameworks = []
        folder = current_app.config["FRAMEWORK_FOLDER"]
        for file in os.listdir(folder):
            if file.endswith(".json"):
                name = file.split(".json")[0]
                frameworks.append(name.lower())
        return frameworks

    def check_valid_framework(self, name):
        if name.lower() not in self.get_valid_frameworks():
            raise ValueError("framework is not implemented")
        return True

    def create_framework(self, name, add_controls=False, add_policies=False):
        if Framework.find_by_name(name, self.id):
            return False
        Framework.create(name, self)
        if add_controls:
            self.create_base_controls_for_framework(name)
        if add_policies:
            self.create_base_policies()
        return True

    def create_base_controls_for_framework(self, name):
        name = name.lower()
        with open(
            os.path.join(current_app.config["FRAMEWORK_FOLDER"], f"{name}.json")
        ) as f:
            controls = json.load(f)
            # TODO - reformat, takes forever b/c of commit
            Control.create({"controls": controls, "framework": name}, self.id)
        return True

    def create_base_frameworks(self, init_controls=False):
        folder = current_app.config["FRAMEWORK_FOLDER"]
        if not os.path.isdir(folder):
            abort(422, f"Folder does not exist: {folder}")
        for file in os.listdir(folder):
            if file.endswith(".json"):
                name = file.split(".json")[0]
                if not Framework.find_by_name(name, self.id):
                    Framework.create(name, self)
                    if init_controls:
                        self.create_base_controls_for_framework(name)
        return True

    def create_base_policies(self):
        for filename in os.listdir(current_app.config["POLICY_FOLDER"]):
            if filename.endswith(".html"):
                name = filename.split(".html")[0].lower()
                if not Policy.find_by_name(name, self.id):
                    with open(
                        os.path.join(current_app.config["POLICY_FOLDER"], filename)
                    ) as f:
                        p = Policy(
                            name=name,
                            description=f"Content for the {name} policy",
                            content=f.read(),
                            template=f.read(),
                            tenant_id=self.id,
                        )
                        db.session.add(p)
        db.session.commit()
        return True

    def get_assessments_for_user(self, user):
        user_roles = self.get_roles_for_member(user)
        data = []
        if user.super or any(role in ["admin"] for role in user_roles):
            return self.assessments.all()
        for assessment in self.assessments.all():
            if assessment.has_guest(user.email):
                data.append(assessment)
        return data

    def can_we_invite_user(self, email):
        if not User.validate_email(email):
            return (False, "Invalid email")

        if self.has_member(email):
            return (False, "User already exists in the tenant")

        user_count = self.members.count()
        if user_count >= int(self.user_cap):
            return (False, "Tenant has reached user capacity")

        if not self.approved_domains:
            return (True, None)

        name, tld = email.split("@")
        for domain in self.approved_domains.split(","):
            if domain == tld:
                return (True, None)
        return (False, "User domain is not within the approved domains of the tenant")

    def remove_user_from_projects(self, user):
        for project in self.projects.all():
            project.members.filter(ProjectMember.user_id == user.id).delete()
        db.session.commit()
        return True

    def remove_user_from_assessments(self, user):
        for assessment in self.assessments:
            AssessmentGuest.query.filter(
                AssessmentGuest.assessment_id == assessment.id
            ).filter(AssessmentGuest.user_id == user.id).delete()
            db.session.commit()
        return True

    def get_default_roles(self, roles):
        if not roles:
            return ["user"]

        if not isinstance(roles, list):
            roles = [roles]

        if "vendor" in roles:
            roles = ["vendor"]
        else:
            if "user" not in roles:
                roles.append("user")
        return roles

    def get_vendor_evidence_folder(self, vendor_id, provider="local"):
        if provider not in current_app.config["STORAGE_PROVIDERS"]:
            abort(422, f"Provider not supported:{provider}")
        if provider != "local":
            # TODO - might have to remove the leading slash for s3 and maybe gcs
            path = os.path.join("vendors", vendor_id.lower())
            return path.lstrip(os.sep)
        return os.path.join(
            current_app.config["EVIDENCE_FOLDER"], "vendors", vendor_id.lower()
        )

    def get_evidence(self, as_dict=False):
        records = self.evidence.all()
        if as_dict:
            return [record.as_dict() for record in records]
        return records

    def get_evidence_folder(self, project_id=None, provider="local"):
        if provider not in current_app.config["STORAGE_PROVIDERS"]:
            abort(422, f"Provider not supported:{provider}")
        if provider != "local":
            path = os.path.join(
                "tenants",
                self.id.lower(),
                *(["projects", project_id.lower()] if project_id else []),
            )
            return path.lstrip(os.sep)
        return os.path.join(
            current_app.config["EVIDENCE_FOLDER"],
            "tenants",
            self.id.lower(),
            *(["projects", project_id.lower()] if project_id else []),
        )

    def can_save_file_in_folder(self, provider=None):
        if not provider:
            provider = current_app.config["STORAGE_METHOD"]
        handler = FileStorageHandler(provider=provider)
        current_size = handler.get_size(folder=self.get_evidence_folder())

        if current_size < int(self.storage_cap):
            return True

        return False

    def get_tenant_info(self):
        data = {
            "projects": self.projects.count(),
            "users": self.members.count(),
            "risks": self.risks.count(),
        }
        return data

    @staticmethod
    def create(
        user,
        name,
        email,
        approved_domains=None,
        license="gold",
        is_default=False,
        init_data=False,
    ):

        tenant = Tenant(
            owner_id=user.id,
            name=name.lower(),
            contact_email=email,
            approved_domains=approved_domains,
            is_default=is_default,
            license=license,
        )
        db.session.add(tenant)
        db.session.commit()

        tenant.populate_data_classification()

        # Add user as Admin to the tenant
        response, user = tenant.add_member(
            user_or_email=user,
            attributes={"roles": ["admin"]},
            send_notification=False,
        )

        if init_data:
            tenant.create_base_frameworks()
            tenant.create_base_policies()
        # create folder for evidence
        tenant.create_evidence_folder()
        return tenant

    def create_vendor_evidence_folder(self, vendor_id):
        vendor_folder = self.get_vendor_evidence_folder(vendor_id)
        if not os.path.exists(vendor_folder):
            os.makedirs(vendor_folder)
        return vendor_folder

    def create_evidence_folder(self, project_id=None):
        evidence_folder = self.get_evidence_folder(project_id=project_id)
        if not os.path.exists(evidence_folder):
            os.makedirs(evidence_folder)
        return evidence_folder

    def delete(self):
        evidence_folder = self.get_evidence_folder()
        if os.path.exists(evidence_folder):
            shutil.rmtree(evidence_folder)
        db.session.delete(self)
        db.session.commit()
        return True

    def create_project(
        self,
        name: str,
        owner_id: int,
        framework_id: int,
        description: str = None,
        controls: List[int] = [],
    ):
        if self.projects.count() >= int(self.project_cap):
            abort(422, f"Tenant has reached project capacity:{self.project_cap}")

        if not description:
            description = name

        project = Project(
            name=name, description=description, owner_id=owner_id, tenant_id=self.id
        )
        if framework_id:
            project.framework_id = framework_id

        self.projects.append(project)
        for control in controls:
            project.add_control(control, commit=False)

        evidence = ProjectEvidence(
            name="Evidence N/A",
            description="Evidence is not required. Used to satisfy evidence collection.",
        )
        project.evidence.append(evidence)
        db.session.commit()
        return project


class ProjectEvidence(db.Model, QueryMixin):
    __tablename__ = "project_evidence"
    __table_args__ = (db.UniqueConstraint("name", "project_id"),)
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String(), default="Empty description")
    content = db.Column(db.String())
    group = db.Column(db.String(), default="default")
    collected_on = db.Column(db.DateTime, default=datetime.utcnow)
    file_name = db.Column(db.String())
    file_provider = db.Column(db.String(), default="local")
    owner_id = db.Column(db.String, db.ForeignKey("users.id"), nullable=True)
    project_id = db.Column(db.String, db.ForeignKey("projects.id"))
    tenant_id = db.Column(db.String, db.ForeignKey("tenants.id"))
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["control_count"] = self.control_count()
        data["controls"] = [
            {"id": control.id, "name": control.subcontrol.name}
            for control in self.get_controls()
        ]
        data["has_file"] = self.has_file()
        return data

    def has_file(self):
        if self.file_name:
            return True
        return False

    def delete(self):
        try:
            self.delete_file()
        except:
            pass
        db.session.delete(self)
        db.session.commit()
        return True

    def update(
        self,
        name=None,
        owner_id=None,
        description=None,
        content=None,
        group=None,
        collected_on=None,
        file=None,
        associate_with=[],
    ):
        """
        Update evidence for a project

        Args:
            name: Name of the evidence
            owner_id: ID of the user who owns the evidence
            description: Description of the evidence
            content: Content, typically JSON/CSV results that represents the evidence
            group: Logically group the evidence for filtering
            collected_on: Date at which it is collected
            file: FileStorage file
            associate_with: List of control IDs to associate the evidence with

        Returns:
            evidence object
        """
        if file is not None and not isinstance(file, FileStorage):
            abort(500, "File must be type FileStorage")

        if name:
            self.name = name
        if description:
            self.description = description
        if content:
            self.content = content
        if group:
            self.group = group
        if collected_on:
            self.collected_on = collected_on
        if owner_id:
            self.owner_id = owner_id
        if file:
            self.save_file(file, overwrite=True)
        if associate_with:
            self.associate_with_controls(associate_with)
        db.session.commit()

        return self

    def remove_controls(self, control_ids: List[int] = []):
        if control_ids:
            EvidenceAssociation.query.filter(
                EvidenceAssociation.evidence_id == self.id
            ).filter(EvidenceAssociation.control_id.in_(control_ids)).delete()
        else:
            EvidenceAssociation.query.filter(
                EvidenceAssociation.evidence_id == self.id
            ).delete()
        db.session.commit()

    def associate_with_controls(self, control_ids: List[int]):
        """
        Associate evidence with a list of control_ids. This will patch the existing association.
        Passing an empty list will delete all associations with the evidence

        Args:
            control_ids: list of ProjectSubControls ids

        Returns:
            None
        """
        self.remove_controls()
        EvidenceAssociation.add(control_ids, self.id)

    def get_controls(self):
        id_list = [
            x.control_id
            for x in EvidenceAssociation.query.filter(
                EvidenceAssociation.evidence_id == self.id
            ).all()
        ]
        return ProjectSubControl.query.filter(ProjectSubControl.id.in_(id_list)).all()

    def control_count(self):
        return EvidenceAssociation.query.filter(
            EvidenceAssociation.evidence_id == self.id
        ).count()

    def has_control(self, control_id):
        return EvidenceAssociation.exists(control_id, self.id)

    def get_file(self, as_blob=False):
        if not self.file_name:
            return {}

        storage_method = current_app.config["STORAGE_METHOD"]
        if self.file_provider != storage_method:
            abort(500, f"File storage backend: {self.file_provider} is not enabled.")

        path = os.path.join(
            self.project.get_evidence_folder(provider=self.file_provider),
            self.file_name,
        )

        file_handler = FileStorageHandler(
            provider=self.file_provider,
        )
        return file_handler.get_file(path=path, as_blob=as_blob)

    def remove_file(self):
        """
        Disassociates the file with the evidence.
        If you want to delete the file, see delete_file()
        """
        if not self.file_name:
            abort(500, "Evidence does not contain a file")
        self.file_name = None
        db.session.commit()
        return True

    def delete_file(self, safe_delete=True):
        if not self.file_name:
            abort(500, "Evidence does not contain a file")

        if safe_delete:
            file_assoc = ProjectEvidence.query.filter(
                ProjectEvidence.file_name == self.file_name
            ).count()
            if file_assoc > 1:
                abort(
                    500,
                    f"Unable to delete the file. It is associated with {file_assoc} other evidence objects.",
                )

        storage_method = current_app.config["STORAGE_METHOD"]
        if self.file_provider != storage_method:
            abort(500, f"File storage backend: {self.file_provider} is not enabled.")

        path = os.path.join(
            self.project.tenant.get_evidence_folder(self.file_provider), self.file_name
        )
        file_handler = FileStorageHandler(
            provider=self.file_provider,
        )
        file_handler.delete_file(path=path)
        self.remove_file()
        return True

    def save_file(self, file_object, file_name=None, provider=None, overwrite=False):
        if not isinstance(file_object, FileStorage):
            abort(500, "File object must be type FileStorage")

        if self.file_name and not overwrite:
            abort(500, "File already exists for the evidence")

        if not provider:
            provider = current_app.config["STORAGE_METHOD"]

        if provider not in current_app.config["STORAGE_PROVIDERS"]:
            abort(500, f"Invalid storage provider: {str(provider)}")

        if not file_name:
            file_name = file_object.filename

        file_name = secure_filename(file_name).lower()

        self.file_name = file_name
        self.file_provider = provider

        if not self.project.tenant.can_save_file_in_folder(provider=provider):
            abort(400, "Tenant has exceeded storage limits")

        file_handler = FileStorageHandler(
            provider=provider,
        )
        # TODO - create does_file_exist method in FileStorageHandler class
        try:
            does_file_exist = file_handler.get_file(
                path=os.path.join(
                    self.project.get_evidence_folder(provider=self.file_provider),
                    file_name,
                )
            )
        except FileDoesNotExist:
            does_file_exist = False

        if does_file_exist:
            abort(
                422,
                f"File already exists with the name:{file_name} in {provider} storage.",
            )

        if provider == "local":
            # TODO - push logic to FileStorageHandler
            self.project.create_evidence_folder()

        upload_params = {
            "file": file_object,
            "file_name": file_name,
            "folder": self.project.tenant.get_evidence_folder(
                project_id=self.project_id, provider=provider
            ),
        }
        # TODO - fix the response, upload_file does not return false
        result = file_handler.upload_file(**upload_params)
        if result is False:
            self.file_name = None
            self.file_provider = None
            db.session.commit()
            abort(500, f"Unable to upload {file_name} to {provider}")
        return True


class EvidenceAssociation(db.Model):
    __tablename__ = "evidence_association"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    control_id = db.Column(
        db.String(), db.ForeignKey("project_subcontrols.id", ondelete="CASCADE")
    )
    evidence_id = db.Column(
        db.String(), db.ForeignKey("project_evidence.id", ondelete="CASCADE")
    )
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    @staticmethod
    def exists(control_id, evidence_id):
        return (
            EvidenceAssociation.query.filter(
                EvidenceAssociation.control_id == control_id
            )
            .filter(EvidenceAssociation.evidence_id == evidence_id)
            .first()
        )

    @staticmethod
    def add(control_ids, evidence_id, commit=True):
        if not isinstance(control_ids, list):
            control_ids = [control_ids]

        for control_id in control_ids:
            if not EvidenceAssociation.exists(control_id, evidence_id):
                evidence = EvidenceAssociation(
                    control_id=control_id, evidence_id=evidence_id
                )
                db.session.add(evidence)
        if commit:
            db.session.commit()
        return True

    @staticmethod
    def remove(control_ids, evidence_id, commit=True):
        if not isinstance(control_ids, list):
            control_ids = [control_ids]

        for control_id in control_ids:
            assoc = EvidenceAssociation.exists(control_id, evidence_id)
            if assoc:
                db.session.delete(assoc)
        if commit:
            db.session.commit()
        return True


class PolicyAssociation(db.Model):
    __tablename__ = "policy_associations"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    policy_id = db.Column(db.String(), db.ForeignKey("policies.id", ondelete="CASCADE"))
    control_id = db.Column(
        db.String(), db.ForeignKey("controls.id", ondelete="CASCADE")
    )
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)


class Framework(db.Model):
    __tablename__ = "frameworks"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String(), nullable=False)
    reference_link = db.Column(db.String())
    guidance = db.Column(db.String)
    """framework specific features"""
    feature_evidence = db.Column(db.Boolean(), default=False)

    controls = db.relationship("Control", backref="framework", lazy="dynamic")
    projects = db.relationship("Project", backref="framework", lazy="dynamic")
    tenant_id = db.Column(db.String, db.ForeignKey("tenants.id"), nullable=True)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["controls"] = self.controls.count()
        return data

    @staticmethod
    def create(name, tenant):
        data = {
            "name": name.lower(),
            "description": f"Framework for {name.capitalize()}",
            "feature_evidence": True,
            "tenant_id": tenant.id,
        }
        path = f"app/files/about_frameworks/{name}.html"
        if os.path.exists(path):
            with open(path) as f:
                data["guidance"] = f.read()
        f = Framework(**data)
        db.session.add(f)
        db.session.commit()
        return True

    @staticmethod
    def find_by_name(name, tenant_id):
        framework_exists = (
            Framework.query.filter(Framework.tenant_id == tenant_id)
            .filter(func.lower(Framework.name) == func.lower(name))
            .first()
        )
        if framework_exists:
            return framework_exists
        return False

    def get_features(self):
        features = []
        for c in self.__table__.columns:
            if c.startswith("feature_"):
                features.append(c)
        return features

    def has_feature(self, name):
        """
        helper method to check if the framework has a specific feature
        for adding new features, the Framework model must be extended
        with new fields such as feature_something
        """
        if not name.startswith("feature_"):
            raise ValueError("name must start with feature_")
        if not hasattr(self, name):
            return False
        return getattr(self, name)

    def has_controls(self):
        if self.controls.count():
            return True
        return False

    def init_controls(self):
        self.tenant.create_base_controls_for_framework(self.name)


class Policy(db.Model):
    __tablename__ = "policies"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    name = db.Column(db.String(), nullable=False)
    ref_code = db.Column(db.String())
    description = db.Column(db.String())
    content = db.Column(db.String())
    template = db.Column(db.String())
    tenant_id = db.Column(db.String, db.ForeignKey("tenants.id"), nullable=True)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self, include=[]):
        data = {}
        for c in self.__table__.columns:
            if c.name in include or not include:
                data[c.name] = getattr(self, c.name)
        return data

    @staticmethod
    def find_by_name(name, tenant_id):
        policy_exists = (
            Policy.query.filter(Policy.tenant_id == tenant_id)
            .filter(func.lower(Policy.name) == func.lower(name))
            .first()
        )
        if policy_exists:
            return policy_exists
        return False

    def controls(self, as_id_list=False):
        control_id_list = []
        for assoc in PolicyAssociation.query.filter(
            PolicyAssociation.policy_id == self.id
        ).all():
            control_id_list.append(assoc.control_id)
        if as_id_list:
            return control_id_list
        return Control.query.filter(Control.id.in_(control_id_list)).all()

    def has_control(self, id):
        return (
            PolicyAssociation.query.filter(PolicyAssociation.policy_id == self.id)
            .filter(PolicyAssociation.control_id == id)
            .first()
        )

    def add_control(self, id):
        if not self.has_control(id):
            pa = PolicyAssociation(policy_id=self.id, control_id=id)
            db.session.add(pa)
            db.session.commit()
        return True

    def get_template_variables(self):
        template_vars = {}
        for label in self.tenant.labels.all():
            template_vars[label.key] = label.value
        template_vars["organization"] = self.tenant.name
        return template_vars


class Control(db.Model):
    __tablename__ = "controls"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    ref_code = db.Column(db.String())
    abs_ref_code = db.Column(db.String())
    visible = db.Column(db.Boolean(), default=True)
    system_level = db.Column(db.Boolean(), default=True)
    category = db.Column(db.String())
    subcategory = db.Column(db.String())
    guidance = db.Column(db.String)
    references = db.Column(db.String())
    mapping = db.Column(db.JSON(), default={})
    is_custom = db.Column(db.Boolean(), default=False)
    vendor_recommendations = db.Column(db.JSON(), default={})
    """framework specific fields"""
    # CMMC
    level = db.Column(db.Integer, default=1)

    # ISO27001
    operational_capability = db.Column(db.String())
    control_type = db.Column(db.String())

    # HIPAA
    dti = db.Column(db.String(), default="easy")
    dtc = db.Column(db.String(), default="easy")
    meta = db.Column(db.JSON(), default="{}")
    subcontrols = db.relationship(
        "SubControl", backref="control", lazy="dynamic", cascade="all, delete"
    )
    framework_id = db.Column(db.String, db.ForeignKey("frameworks.id"), nullable=False)
    project_controls = db.relationship(
        "ProjectControl", backref="control", lazy="dynamic", cascade="all, delete"
    )
    tenant_id = db.Column(db.String, db.ForeignKey("tenants.id"), nullable=True)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self, include=[], with_subcontrols=True):
        data = {}
        if with_subcontrols:
            data["subcontrols"] = []
            data["framework"] = self.framework.name
            subcontrols = self.subcontrols.all()
            data["subcontrol_count"] = len(subcontrols)
            for sub in subcontrols:
                data["subcontrols"].append(sub.as_dict())
        for c in self.__table__.columns:
            if c.name in include or not include:
                data[c.name] = getattr(self, c.name)
        return data

    @staticmethod
    def find_by_abs_ref_code(framework, ref_code):
        if not framework or not ref_code:
            raise ValueError("framework and ref_code is required")
        abs_ref_code = f"{framework.lower()}__{ref_code}"
        return Control.query.filter(
            func.lower(Control.abs_ref_code) == func.lower(abs_ref_code)
        ).first()

    def policies(self, as_id_list=False):
        policy_id_list = []
        for assoc in PolicyAssociation.query.filter(
            PolicyAssociation.policy_id == self.id
        ).all():
            policy_id_list.append(assoc.policy_id)
        if as_id_list:
            return policy_id_list
        return Policy.query.filter(Policy.id.in_(policy_id_list)).all()

    def in_policy(self, policy_id):
        return policy_id in self.policies(as_id_list=True)

    @staticmethod
    def create(data, tenant_id):
        """
        data = {
            "framework": data.get("framework"),
            "controls": [
                {
                    "name": data.get("name"),
                    "description": data.get("description"),
                    "ref_code": data.get("ref_code"),
                }
            ]
        }
        """
        created_controls = []
        if framework := data.get("framework"):
            if not (f := Framework.find_by_name(framework, tenant_id)):
                f = Framework(
                    name=framework,
                    description=data.get(
                        "framework_description", f"Framework for {framework}"
                    ),
                    tenant_id=tenant_id,
                )
                db.session.add(f)
                db.session.commit()
        else:
            abort(400, "Framework is required")

        # create controls and subcontrols
        for control in data.get("controls", []):
            c = Control(
                name=control.get("name"),
                description=control.get("description"),
                ref_code=control.get("ref_code"),
                abs_ref_code=f"{framework.lower()}__{control.get('ref_code')}",
                system_level=control.get("system_level"),
                category=control.get("category"),
                subcategory=control.get("subcategory"),
                references=control.get("references"),
                level=int(control.get("level", 1)),
                guidance=control.get("guidance"),
                mapping=control.get("mapping"),
                vendor_recommendations=control.get("vendor_recommendations"),
                dti=control.get("dti"),
                dtc=control.get("dtc"),
                meta=control.get("meta", {}),
                tenant_id=tenant_id,
            )
            """
            if there are no subcontrols for the control, we are going to add the
            top-level control itself as the first subcontrol
            """
            subcontrols = control.get("subcontrols", [])
            if not subcontrols:
                subcontrols = [
                    {
                        "name": c.name,
                        "description": c.description,
                        "ref_code": c.ref_code,
                        "mitigation": control.get(
                            "mitigation", "The mitigation has not been documented"
                        ),
                        "guidance": control.get("guidance"),
                        "tasks": control.get("tasks"),
                    }
                ]
            for sub in subcontrols:
                fa = SubControl(
                    name=sub.get("name"),
                    description=sub.get(
                        "description", "The description has not been documented"
                    ),
                    ref_code=sub.get("ref_code", c.ref_code),
                    mitigation=sub.get("mitigation"),
                    guidance=sub.get("guidance"),
                    implementation_group=sub.get("implementation_group"),
                    meta=sub.get("meta", {}),
                    tasks=sub.get("tasks", []),
                )
                c.subcontrols.append(fa)
            f.controls.append(c)
            created_controls.append(c)
        db.session.commit()
        return created_controls

        """
        data = {
            "framework": data.get("framework"),
            "controls": [
                {
                    "name": data.get("name"),
                    "description": data.get("description"),
                    "ref_code": data.get("ref_code"),
                }
            ]
        }
        """
        if framework := data.get("framework"):
            if not (f := Framework.find_by_name(framework, tenant_id)):
                f = Framework(
                    name=framework,
                    description=data.get(
                        "framework_description", f"Framework for {framework}"
                    ),
                    tenant_id=tenant_id,
                )
                db.session.add(f)
                db.session.commit()
        else:
            abort(400, "Framework is required")

        # create controls and subcontrols
        for control in data.get("controls", []):
            c = Control(
                name=control.get("name"),
                description=control.get("description"),
                ref_code=control.get("ref_code"),
                abs_ref_code=f"{framework.lower()}__{control.get('ref_code')}",
                system_level=control.get("system_level"),
                category=control.get("category"),
                subcategory=control.get("subcategory"),
                references=control.get("references"),
                level=int(control.get("level", 1)),
                guidance=control.get("guidance"),
                mapping=control.get("mapping"),
                vendor_recommendations=control.get("vendor_recommendations"),
                dti=control.get("dti"),
                dtc=control.get("dtc"),
                meta=control.get("meta", {}),
                tenant_id=tenant_id,
            )
            """
            if there are no subcontrols for the control, we are going to add the
            top-level control itself as the first subcontrol
            """
            subcontrols = control.get("subcontrols", [])
            if not subcontrols:
                subcontrols = [
                    {
                        "name": c.name,
                        "description": c.description,
                        "ref_code": c.ref_code,
                        "mitigation": control.get(
                            "mitigation", "The mitigation has not been documented"
                        ),
                        "guidance": control.get("guidance"),
                        "tasks": control.get("tasks"),
                    }
                ]
            for sub in subcontrols:
                fa = SubControl(
                    name=sub.get("name"),
                    description=sub.get(
                        "description", "The description has not been documented"
                    ),
                    ref_code=sub.get("ref_code", c.ref_code),
                    mitigation=sub.get("mitigation"),
                    guidance=sub.get("guidance"),
                    implementation_group=sub.get("implementation_group"),
                    meta=sub.get("meta", {}),
                    tasks=sub.get("tasks", []),
                )
                c.subcontrols.append(fa)
            f.controls.append(c)
        db.session.commit()
        return True


class SubControl(db.Model):
    __tablename__ = "subcontrols"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    ref_code = db.Column(db.String())
    mitigation = db.Column(db.String())
    guidance = db.Column(db.String)
    meta = db.Column(db.JSON(), default={})
    tasks = db.Column(db.JSON(), default={})
    """framework specific fields"""
    # CSC
    implementation_group = db.Column(db.Integer)

    control_id = db.Column(db.String, db.ForeignKey("controls.id"), nullable=False)
    project_subcontrols = db.relationship(
        "ProjectSubControl", backref="subcontrol", lazy="dynamic", cascade="all, delete"
    )
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self, include=[]):
        data = {}
        for c in self.__table__.columns:
            if c.name in include or not include:
                data[c.name] = getattr(self, c.name)
        return data


class ProjectMember(db.Model):
    __tablename__ = "project_members"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    user_id = db.Column(db.String(), db.ForeignKey("users.id", ondelete="CASCADE"))
    project_id = db.Column(
        db.String(), db.ForeignKey("projects.id", ondelete="CASCADE")
    )
    access_level = db.Column(db.String(), nullable=False, default="viewer")
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    VALID_ACCESS_LEVELS = ["manager", "contributor", "viewer", "auditor"]

    def user(self):
        return User.query.get(self.user_id)


class CompletionHistory(db.Model):
    __tablename__ = "completion_history"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    value = db.Column(db.Integer, nullable=False)
    project_id = db.Column(db.String, db.ForeignKey("projects.id"), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)


class Project(db.Model, DateMixin):
    __tablename__ = "projects"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    last_completion_update = db.Column(db.DateTime)
    controls = db.relationship(
        "ProjectControl",
        backref="project",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    policies = db.relationship(
        "ProjectPolicy", backref="project", lazy="dynamic", cascade="all, delete-orphan"
    )
    evidence = db.relationship(
        "ProjectEvidence",
        backref="project",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    format = db.Column(db.String(), default="default")  # ["default", "simple"]
    show_driver = db.Column(db.Boolean(), default=True)
    """
    permission toggles for project
    """
    auditor_enabled = db.Column(db.Boolean(), default=True)
    can_auditor_read_scratchpad = db.Column(db.Boolean(), default=True)
    can_auditor_write_scratchpad = db.Column(db.Boolean(), default=False)
    can_auditor_read_comments = db.Column(db.Boolean(), default=True)
    can_auditor_write_comments = db.Column(db.Boolean(), default=True)
    policies_require_cc = db.Column(db.Boolean(), default=True)

    """
    framework specific fields
    """
    # CMMC
    target_level = db.Column(db.Integer, default=1)

    # HIPAA
    tags = db.relationship(
        "Tag",
        secondary="project_tags",
        lazy="dynamic",
        backref=db.backref("projects", lazy="dynamic"),
    )
    comments = db.relationship(
        "ProjectComment",
        backref="project",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    completion_history = db.relationship(
        "CompletionHistory",
        backref="project",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    notes = db.Column(db.String())
    members = db.relationship(
        "ProjectMember", backref="project", lazy="dynamic", cascade="all, delete-orphan"
    )
    findings = db.relationship(
        "Finding", backref="project", lazy="dynamic", cascade="all, delete-orphan"
    )
    risks = db.relationship(
        "RiskRegister", backref="project", lazy="dynamic", cascade="all, delete-orphan"
    )
    owner_id = db.Column(db.String(), db.ForeignKey("users.id"), nullable=False)
    tenant_id = db.Column(db.String, db.ForeignKey("tenants.id"), nullable=False)
    framework_id = db.Column(db.String, db.ForeignKey("frameworks.id"))
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self, with_summary=False, with_controls=False, exclude_timely=False):
        # TODO - refactor
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["owner"] = self.user.email
        data["tenant"] = self.tenant.name
        data["auditors"] = [
            {"id": user.id, "email": user.email} for user in self.get_auditors()
        ]
        data["members"] = [
            {"id": member.user().id, "email": member.user().email}
            for member in self.members.all()
        ]
        if self.framework:
            data["framework"] = self.framework.name

        if with_summary:
            controls = self.controls.all()
            data["completion_progress"] = self.completion_progress(controls=controls)
            data["total_controls"] = len(controls)
            data["total_policies"] = self.policies.count()
            if with_controls:
                data["controls"] = [control.as_dict() for control in controls]
            data["status"] = "not started"
            if data["completion_progress"] > 0 and data["completion_progress"] < 100:
                data["status"] = "in progress"
            if data["completion_progress"] == 100:
                data["status"] = "complete"

            if not exclude_timely:
                data["implemented_progress"] = self.implemented_progress(
                    controls=controls
                )
                data["evidence_progress"] = self.evidence_progress(controls=controls)
                data["review_summary"] = self.review_summary()

        return data

    def generate_last_30_days(self):
        data_list = self.completion_history.order_by(
            CompletionHistory.date_added.desc()
        ).all()
        if not data_list:
            return []

        # Convert input data_list into a dictionary for easier lookup
        data_by_date = {
            arrow.get(item.date_added).date(): item.value for item in data_list
        }

        last_date = arrow.get(data_list[0].date_added).date()
        start_date = arrow.get(last_date).shift(days=-29).date()

        # Initialize the result list
        result = []
        last_valid_value = 0  # Default value if no prior data exists

        # Iterate from start_date to last_date
        for single_date in arrow.Arrow.range(
            "day", arrow.get(start_date), arrow.get(last_date)
        ):
            current_date = single_date.date()

            if current_date in data_by_date:
                # Use the value from the data_list if the date exists
                last_valid_value = data_by_date[current_date]
                result.append(
                    {
                        "date": current_date.strftime("%m/%d/%Y"),
                        "value": last_valid_value,
                    }
                )
            else:
                # Copy the last valid value if available
                result.append(
                    {
                        "date": current_date.strftime("%m/%d/%Y"),
                        "value": last_valid_value,
                    }
                )

        return result

    def add_custom_control(self, control):
        """
        See Control.create for data format
        """
        if not isinstance(control, dict):
            abort(400, "Control must be a dictionary")
        control["ref_code"] = f"cu-{random.randint(1000, 9999)}"
        data = {"framework": "custom", "controls": [control]}
        control = Control.create(data, tenant_id=self.tenant_id)
        if not control:
            abort(400, "Failed to create control")
        # Control.create returns a list of controls
        project_control = self.add_control(control[0])
        return project_control

    def ready_for_completion_update(self):
        if not self.last_completion_update:
            return True

        time_difference = arrow.now() - arrow.get(self.last_completion_update)

        return time_difference.days >= 1

    def create_tag(self, name):
        tag = Tag.add(name, tenant_id=self.tenant_id)
        project_tag = ProjectTags(tag_id=tag.id, project_id=self.id)
        db.session.add(project_tag)
        db.session.commit()
        return tag

    def add_completion_metric(self, completion=None):
        if completion is None:
            completion = self.completion_progress()
        history = CompletionHistory(value=completion)
        self.completion_history.append(history)
        self.last_completion_update = arrow.utcnow().format()
        db.session.commit()

    def get_evidence_folder(self, provider="local"):
        return self.tenant.get_evidence_folder(project_id=self.id, provider=provider)

    def create_evidence_folder(self):
        return self.tenant.create_evidence_folder(project_id=self.id)

    def create_evidence(
        self,
        name,
        owner_id,
        description=None,
        content=None,
        group=None,
        collected_on=None,
        file=None,
        associate_with=[],
    ):
        """
        Create evidence for a project

        Args:
            name: Name of the evidence
            owner_id: ID of the user who owns the evidence
            description: Description of the evidence
            content: Content, typically JSON/CSV results that represents the evidence
            group: Logically group the evidence for filtering
            collected_on: Date at which it is collected
            file: FileStorage file
            associate_with: List of control IDs to associate the evidence with

        Returns:
            evidence object
        """
        if file is not None and not isinstance(file, FileStorage):
            abort(500, "File must be type FileStorage")

        if self.evidence.filter(ProjectEvidence.name == name).first():
            abort(422, f"Evidence already exists with name:{name}")

        evidence = ProjectEvidence(
            name=name,
            description=description,
            content=content,
            group=group,
            collected_on=collected_on,
            owner_id=owner_id,
            tenant_id=self.tenant_id,
        )
        self.evidence.append(evidence)
        db.session.commit()
        if file:
            evidence.save_file(file_object=file, file_name=file.filename)

        if associate_with:
            evidence.associate_with_controls(associate_with)
        return evidence

    def create_risk(
        self, title, description, status="new", priority="unknown", risk="unknown"
    ):
        risk = RiskRegister(
            title=title,
            description=description,
            status=status,
            priority=priority,
            risk=risk,
            project_id=self.id,
            tenant_id=self.tenant_id,
        )
        db.session.add(risk)
        db.session.commit()
        return risk

    def review_summary(self):
        data = {"total": 0}
        for record in (
            ProjectControl.query.with_entities(
                ProjectControl.review_status,
                func.count(ProjectControl.review_status),
            )
            .group_by(ProjectControl.review_status)
            .filter(ProjectControl.project_id == self.id)
            .all()
        ):
            data[record[0]] = record[1]
            data["total"] += record[1]
        return data

    def get_auditors(self):
        auditors = []
        for member in self.members.filter(
            ProjectMember.access_level == "auditor"
        ).all():
            auditors.append(member.user())
        return auditors

    def has_auditor(self, user):
        return self.has_member_with_access(user, "auditor")

    def add_member(self, user, access_level="viewer"):
        if self.has_member(user):
            return True
        db.session.add(
            ProjectMember(
                user_id=user.id, access_level=access_level, project_id=self.id
            )
        )
        db.session.commit()
        return True

    def remove_member(self, user):
        if not self.has_member(user):
            return True
        self.members.filter(ProjectMember.user_id == user.id).delete()
        db.session.commit()
        return True

    def has_member(self, user_or_email):
        if not (user := User.email_to_object(user_or_email)):
            return False
        if result := self.members.filter(ProjectMember.user_id == user.id).first():
            return result
        return False

    def has_member_with_access(self, user_or_email, access):
        if not (user := User.email_to_object(user_or_email)):
            return False
        if not isinstance(access, list):
            access = [access]
        if result := self.members.filter(ProjectMember.user_id == user.id).first():
            if result.access_level in access:
                return True
        return False

    def update_member_access(self, user_id, access_level):
        if member := self.members.filter(ProjectMember.user_id == user_id).first():
            if access_level not in ProjectMember.VALID_ACCESS_LEVELS:
                return False
            member.access_level = access_level
            db.session.commit()
        return False

    def get_applicable_control_count(self):
        applicable_controls_count = (
            db.session.query(func.count(distinct(ProjectControl.id)))
            .join(
                ProjectSubControl,
                ProjectControl.id == ProjectSubControl.project_control_id,
            )
            .filter(
                ProjectControl.project_id == self.id,
                ProjectSubControl.is_applicable == True,
            )
            .group_by(ProjectControl.id)
            .having(
                func.count(ProjectSubControl.id)
                == func.sum(
                    case([(ProjectSubControl.is_applicable == True, 1)], else_=0)
                )
            )
            .count()
        )
        return applicable_controls_count

    def evidence_groupings(self):
        data = {}
        for sub in self.subcontrols():
            for evidence in sub.evidence.all():
                if evidence.id not in data:
                    data[evidence.id] = {
                        "id": evidence.id,
                        "name": evidence.name,
                        "count": 0,
                    }
                else:
                    data[evidence.id]["count"] += 1
        return data

    def completion_progress(self, controls=None, default=100):
        total = 0
        total_applicable_controls = self.get_applicable_control_count()
        if not total_applicable_controls:
            return default
        if controls is None:
            controls = self.controls.all()
        for control in controls:
            total += control.completed_progress()
        return round((total / total_applicable_controls), 0)

    def evidence_progress(self, controls=None):
        total = 0
        if controls is None:
            controls = self.controls.all()
        if not controls:
            return total
        for control in controls:
            total += control.progress("with_evidence")
        return round((total / len(controls)), 0)

    def implemented_progress(self, controls=None):
        total = 0
        if not controls:
            controls = self.controls.all()
        if not controls:
            return total
        for control in controls:
            if control.is_applicable():
                total += control.implemented_progress()
        return round((total / len(controls)), 0)

    def has_control(self, control_id):
        return self.controls.filter(ProjectControl.control_id == control_id).first()

    def has_policy(self, name):
        return self.policies.filter(ProjectPolicy.name == name).first()

    def add_control(self, control, commit=True):
        if not control:
            return False
        if self.has_control(control.id):
            return control
        project_control = ProjectControl(control_id=control.id)
        for sub in control.subcontrols.all():
            control_sub = ProjectSubControl(subcontrol_id=sub.id, project_id=self.id)
            project_control.subcontrols.append(control_sub)
            # Add tasks (e.g. AuditorFeedback)
            if sub.tasks:
                for task in sub.tasks:
                    control_sub.feedback.append(
                        AuditorFeedback(
                            title=task.get("title"),
                            description=task.get("description"),
                            owner_id=self.owner_id,
                        )
                    )

        self.controls.append(project_control)
        if commit:
            db.session.commit()
        return project_control

    def create_policy(self, name, description, template=None):
        policy = ProjectPolicy(name=name, description=description)

        self.policies.append(policy)
        db.session.commit()

        if template:
            if policy_template := (
                self.tenant.policies.filter(
                    func.lower(Policy.name) == func.lower(template)
                ).first()
            ):
                policy.add_version(policy_template.content)

        return policy

    def remove_policy(self, id):
        if policy := self.policies.filter(ProjectPolicy.id == id).first():
            db.session.delete(policy)
            db.session.commit()
        return True

    def remove_control(self, id):
        if control := self.controls.filter(ProjectControl.id == id).first():
            db.session.delete(control)
            db.session.commit()
        return True


class ProjectPolicyAssociation(db.Model):
    __tablename__ = "project_policy_associations"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    policy_id = db.Column(
        db.String(), db.ForeignKey("project_policies.id", ondelete="CASCADE")
    )
    control_id = db.Column(
        db.String(), db.ForeignKey("project_controls.id", ondelete="CASCADE")
    )
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)


class ProjectPolicy(db.Model):
    __tablename__ = "project_policies"
    __table_args__ = (db.UniqueConstraint("name", "project_id"),)
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    name = db.Column(db.String(), nullable=True)
    ref_code = db.Column(db.String())
    description = db.Column(db.String())
    visible = db.Column(db.Boolean(), default=True)
    tags = db.relationship(
        "Tag",
        secondary="policy_tags",
        lazy="dynamic",
        backref=db.backref("project_policies", lazy="dynamic"),
    )
    versions = db.relationship("PolicyVersion", backref="policy", lazy="dynamic")
    project_id = db.Column(db.String, db.ForeignKey("projects.id"), nullable=False)
    owner_id = db.Column(db.String(), db.ForeignKey("users.id"))
    reviewer_id = db.Column(db.String(), db.ForeignKey("users.id"))
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self, include=[]):
        data = {}
        for c in self.__table__.columns:
            if c.name in include or not include:
                data[c.name] = getattr(self, c.name)
        data["owner"] = self.owner_email()
        data["reviewer"] = self.reviewer_email()
        data["version_id"] = 1

        """
        By default, load the published version and then the 
        latest version (if there is not a published version)
        """
        if not (version := self.get_published_version()):
            version = self.get_latest_version()

        if version:
            data["version_id"] = version.id
            data["content"] = version.content
            data["version"] = version.version

        versions = self.get_versions()
        data["versions"] = versions
        data["is_published"] = False
        for record in versions:
            if record["published"]:
                data["is_published"] = True
                break
        return data

    def get_published_version(self):
        return self.versions.filter(PolicyVersion.published == True).first()

    def publish_version(self, version):
        if not (has_version := self.get_version(version)):
            abort(404, f"Version:{version} not found")
        has_version.published = True
        for record in self.versions.all():
            if record != has_version:
                record.published = False
        db.session.commit()
        return has_version

    def update(self, name=None, description=None, reviewer=None):
        if name:
            self.name = name
        if description:
            self.description = description
        if reviewer:
            if member := self.project.has_member(reviewer):
                self.reviewer_id = member.user_id
        db.session.commit()
        return self

    def update_version(self, version, content=None, status=None, publish=False):
        record = self.get_version(version)
        if content is not None:
            record.content = content
        if status:
            record.status = status
        db.session.commit()
        if publish:
            self.publish_version(version)
        return record

    def get_versions(self, content=False, include_object=False):
        data = []
        latest = True
        for version in self.versions.order_by(PolicyVersion.version.desc()).all():
            last_changed = arrow.get(version.date_updated or version.date_added).format(
                "MMM, YY"
            )
            record = {
                "version_id": version.id,
                "version": version.version,
                "status": version.status,
                "published": version.published,
                "last_changed": last_changed,
                "is_latest": latest,
            }
            latest = False
            if content:
                record["content"] = version.content
            if include_object:
                record["object"] = version
            data.append(record)
        return data

    def get_latest_version(self, status=None):
        _query = self.versions
        if status:
            _query = _query.filter(PolicyVersion.status == status)
        return _query.order_by(PolicyVersion.version.desc()).first()

    def delete_version(self, version):
        if record := self.get_version(version):
            db.session.delete(record)
            db.session.commit()
        return True

    def get_version(self, version, status=None, published=None, as_dict=False):
        if version == "latest":
            record = self.get_latest_version(status=status)
            """
            If there are no versions, create one and return it.
            Should probably move this to init of a policy
            """
            if not record:
                record = self.add_version(content="")

        elif version == "published":
            if not (record := self.get_published_version()):
                abort(404, "Policy has not been published")
        else:
            record = self.versions.filter(PolicyVersion.version == version).first()
        if not record:
            abort(404, "Version not found")
        if as_dict:
            return record.as_dict()
        return record

    def add_version(self, content, status="draft"):
        latest_version = self.get_latest_version()
        next_version = latest_version.version + 1 if latest_version else 1
        new_version = PolicyVersion(
            content=content, status=status, version=next_version
        )
        self.versions.append(new_version)
        db.session.commit()
        return new_version

    def get_controls(self):
        return ProjectPolicyAssociation.query.filter(
            ProjectPolicyAssociation.policy_id == self.id
        ).all()

    def has_control(self, id):
        return (
            ProjectPolicyAssociation.query.filter(
                ProjectPolicyAssociation.policy_id == self.id
            )
            .filter(ProjectPolicyAssociation.control_id == id)
            .first()
        )

    def add_control(self, id):
        if not self.has_control(id):
            pa = ProjectPolicyAssociation(policy_id=self.id, control_id=id)
            db.session.add(pa)
            db.session.commit()
        return True

    def remove_control(self, id):
        if self.has_control(id):
            pa = ProjectPolicyAssociation(policy_id=self.id, control_id=id)
            db.session.delete(pa)
            db.session.commit()
        return True

    def owner_email(self):
        if user := User.query.get(self.owner_id):
            return user.email
        return None

    def reviewer_email(self):
        if user := User.query.get(self.reviewer_id):
            return user.email
        return None

    def get_template_variables(self):
        template = self.as_dict(
            include=["uuid", "version", "name", "description", "ref_code"]
        )
        template["organization"] = self.project.tenant.name
        template["owner_email"] = self.owner_email()
        template["reviewer_email"] = self.reviewer_email()
        for label in PolicyLabel.query.all():
            template[label.key] = label.value
        return template

    def translate_to_html(self):
        class CustomFormatter(Formatter):
            def get_value(self, key, args, kwds):
                if isinstance(key, str):
                    try:
                        return kwds[key]
                    except KeyError:
                        return key
                else:
                    return Formatter.get_value(key, args, kwds)

        fmt = CustomFormatter()
        return fmt.format(self.content, **self.get_template_variables())


class PolicyVersion(db.Model):
    __tablename__ = "policy_versions"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    content = db.Column(db.String())
    version = db.Column(db.Integer())
    status = db.Column(db.String(), default="draft")
    published = db.Column(db.Boolean(), default=False)
    policy_id = db.Column(
        db.String, db.ForeignKey("project_policies.id"), nullable=False
    )
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    VALID_STATUSES = ["draft", "in_review", "ready"]

    def as_dict(self):
        data = {}
        for c in self.__table__.columns:
            data[c.name] = getattr(self, c.name)
        data["is_latest"] = self.is_latest()
        if not self.status:
            data["status"] = "draft"
        return data

    def is_latest(self):
        latest = (
            PolicyVersion.query.filter(PolicyVersion.policy_id == self.policy_id)
            .order_by(PolicyVersion.version.desc())
            .first()
        )
        if latest == self:
            return True
        return False


class ProjectControl(db.Model, ControlMixin):
    __tablename__ = "project_controls"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    notes = db.Column(db.String())
    auditor_notes = db.Column(db.String())
    review_status = db.Column(db.String(), default="infosec action")
    comments = db.relationship(
        "ControlComment",
        backref="control",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    tags = db.relationship(
        "Tag",
        secondary="control_tags",
        lazy="dynamic",
        backref=db.backref("project_controls", lazy="dynamic"),
    )
    feedback = db.relationship(
        "AuditorFeedback",
        backref="control",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    subcontrols = db.relationship(
        "ProjectSubControl",
        backref="p_control",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    project_id = db.Column(db.String, db.ForeignKey("projects.id"), nullable=False)
    control_id = db.Column(db.String, db.ForeignKey("controls.id"), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    VALID_REVIEW_STATUS = ["infosec action", "ready for auditor", "complete"]

    def set_as_applicable(self):
        for subcontrol in self.subcontrols.all():
            subcontrol.is_applicable = True
        db.session.commit()

    def set_as_not_applicable(self):
        for subcontrol in self.subcontrols.all():
            subcontrol.is_applicable = False
        db.session.commit()

    def set_assignee(self, assignee_id):
        for subcontrol in self.subcontrols.all():
            subcontrol.owner_id = assignee_id
        db.session.commit()

    def add_tag(self, tag_name):
        if self.has_tag(tag_name):
            return True

        if not (tag := Tag.find_by_name(tag_name, self.project.tenant_id)):
            tag = Tag.add(tag_name.lower(), tenant_id=self.project.tenant_id)

        control_tag = ControlTags(control_id=self.id, tag_id=tag.id)
        db.session.add(control_tag)
        db.session.commit()
        return tag

    def remove_tag(self, tag_name):
        if tag := self.has_tag(tag_name):
            self.tags.remove(tag)
            db.session.commit()
        return True

    def has_tag(self, tag_name):
        has_tag = next(
            (i for i in self.tags.all() if i.name.lower() == tag_name.lower()), False
        )
        return has_tag

    def set_tags(self, tag_names):
        ControlTags.query.filter(ControlTags.control_id == self.id).delete()
        db.session.commit()
        # Add new tags
        for tag_name in tag_names:
            self.add_tag(tag_name)
        return True

    def create_feedback(
        self,
        title,
        owner_id,
        description=None,
        is_complete=None,
        response=None,
        relates_to=None,
    ):
        feedback = AuditorFeedback(title=title, owner_id=owner_id)
        if description:
            feedback.description = description
        if response:
            feedback.response = response
        if is_complete is not None:
            feedback.is_complete = is_complete
        if relates_to and isinstance(relates_to, int):
            if self.subcontrols.filter(ProjectSubControl.id == relates_to).first():
                feedback.relates_to = relates_to

        self.feedback.append(feedback)
        db.session.commit()
        return feedback

    def update_feedback(
        self,
        feedback_id,
        title=None,
        description=None,
        is_complete=None,
        response=None,
        relates_to=None,
    ):
        feedback = self.feedback.filter(AuditorFeedback.id == feedback_id).first()
        if not feedback:
            abort(422, f"Feedback:{feedback_id} not found")
        if title:
            feedback.title = title
        if description:
            feedback.description = description
        if response:
            feedback.response = response
        if is_complete is not None:
            feedback.is_complete = is_complete
        if relates_to and isinstance(relates_to, int):
            if self.subcontrols.filter(ProjectSubControl.id == relates_to).first():
                feedback.relates_to = relates_to
        db.session.commit()
        return feedback


class AuditorFeedback(db.Model):
    __tablename__ = "auditor_feedback"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    title = db.Column(db.String())
    description = db.Column(db.String())
    response = db.Column(db.String())
    is_complete = db.Column(db.Boolean(), default=False)
    owner_id = db.Column(db.String, db.ForeignKey("users.id"), nullable=False)
    control_id = db.Column(
        db.String, db.ForeignKey("project_controls.id"), nullable=False
    )
    relates_to = db.Column(db.String, db.ForeignKey("project_subcontrols.id"))
    risk_relation = db.Column(db.String, db.ForeignKey("risk_register.id"))
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["auditor_email"] = User.query.get(self.owner_id).email
        data["status"] = self.status
        return data

    @property
    def status(self):
        if self.is_complete:
            return "complete"
        if not self.response:
            return "response required from infoSec"
        return "waiting on auditor"

    def create_risk_record(self):
        title = f"[Auditor Feedback]: {self.title}"
        risk = self.control.project.create_risk(
            title=title, description=self.description
        )
        self.risk_relation = risk.id
        db.session.commit()
        return True


class SubControlComment(db.Model):
    __tablename__ = "subcontrol_comments"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    message = db.Column(db.String())
    owner_id = db.Column(db.String, db.ForeignKey("users.id"), nullable=False)
    subcontrol_id = db.Column(
        db.String, db.ForeignKey("project_subcontrols.id"), nullable=False
    )
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["author_email"] = User.query.get(self.owner_id).email
        return data


class ControlComment(db.Model):
    __tablename__ = "control_comments"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    message = db.Column(db.String())
    owner_id = db.Column(db.String, db.ForeignKey("users.id"), nullable=False)
    control_id = db.Column(
        db.String, db.ForeignKey("project_controls.id"), nullable=False
    )
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["author_email"] = User.query.get(self.owner_id).email
        return data


class ProjectComment(db.Model):
    __tablename__ = "project_comments"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    message = db.Column(db.String())
    owner_id = db.Column(db.String, db.ForeignKey("users.id"), nullable=False)
    project_id = db.Column(db.String, db.ForeignKey("projects.id"), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["author_email"] = User.query.get(self.owner_id).email
        return data


class RiskComment(db.Model):
    __tablename__ = "risk_comments"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    message = db.Column(db.String())
    owner_id = db.Column(db.String, db.ForeignKey("users.id"), nullable=False)
    risk_id = db.Column(db.String, db.ForeignKey("risk_register.id"), nullable=False)
    tenant_id = db.Column(db.String, db.ForeignKey("tenants.id"), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["author_email"] = User.query.get(self.owner_id).email
        return data


class RiskRegister(db.Model):
    __tablename__ = "risk_register"
    __table_args__ = (db.UniqueConstraint("title", "tenant_id"),)
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.String, default="No description")
    remediation = db.Column(db.String)
    enabled = db.Column(db.Boolean(), default=True)
    risk = db.Column(db.String, default="unknown", nullable=False)
    status = db.Column(db.String, default="new", nullable=False)
    priority = db.Column(db.String, default="unknown", nullable=False)
    assignee = db.Column(db.String, db.ForeignKey("users.id"))
    tags = db.relationship(
        "Tag",
        secondary="risk_tags",
        lazy="dynamic",
        backref=db.backref("risk_register", lazy="dynamic"),
    )
    comments = db.relationship(
        "RiskComment",
        backref="risk",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    vendor_id = db.Column(db.String, db.ForeignKey("vendors.id"), nullable=True)
    project_id = db.Column(db.String, db.ForeignKey("projects.id"), nullable=True)
    tenant_id = db.Column(db.String, db.ForeignKey("tenants.id"), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    ALLOWED_RISKS = ["unknown", "low", "moderate", "high", "critical"]
    ALLOWED_PRIORITY = ["unknown", "low", "moderate", "high"]
    ALLOWED_STATUS = ["new", "in_progress", "accepted", "mitigated"]

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["scope"] = "tenant"
        parsed_date = arrow.get(self.date_added)
        data["created_at"] = parsed_date.format("MMM D, YYYY")
        if self.project_id:
            data["scope"] = "project"
            data["project"] = Project.query.get(self.project_id).name

        if self.vendor_id:
            data["vendor"] = Vendor.query.get(self.vendor_id).name

        data["comments"] = [comment.as_dict() for comment in self.comments.all()]
        data["tags"] = []
        if self.tags:
            for tag in self.tags.all():
                data["tags"].append(tag.as_dict())
        return data

    @validates("status")
    def _validate_status(self, key, value):
        value = value or "new"
        if value not in self.ALLOWED_STATUS:
            raise ValueError(f"Invalid status: {value}")
        return value

    @validates("priority")
    def _validate_priority(self, key, value):
        value = value or "unknown"
        if value not in self.ALLOWED_PRIORITY:
            raise ValueError(f"Invalid priority: {value}")
        return value

    @validates("risk")
    def _validate_risk(self, key, value):
        value = value or "unknown"
        if value not in self.ALLOWED_RISKS:
            raise ValueError(f"Invalid risk: {value}")
        return value

    def update(self, **kwargs):
        """
        Update the risk with the provided fields.
        Validates the input fields and updates the risk accordingly.

        Args:
            **kwargs: Fields to update with their new values

        Returns:
            self: The updated risk object

        Raises:
            ValueError: If any of the provided values are invalid
        """
        allowed_fields = {
            "title": str,
            "description": str,
            "remediation": str,
            "status": str,
            "risk": str,
            "priority": str,
            "assignee": str,
            "owner_id": str,
            "enabled": bool,
        }

        for field, value in kwargs.items():
            if field not in allowed_fields:
                continue

            if field in ["status", "risk", "priority"]:
                # Use the existing validators
                setattr(self, field, value)
            else:
                setattr(self, field, value)
        db.session.commit()
        return self


class ProjectSubControl(db.Model, SubControlMixin):
    __tablename__ = "project_subcontrols"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    sort_id = db.Column(
        db.Integer,
        default=lambda: random.randint(0, 999),
    )
    implemented = db.Column(db.Integer(), default=0)
    is_applicable = db.Column(db.Boolean(), default=True)
    context = db.Column(db.String())
    notes = db.Column(db.String())
    """
    framework specific fields
    """
    # SOC2
    auditor_feedback = db.Column(db.String())
    # CMMC
    process_maturity = db.Column(db.Integer(), default=0)

    """
    may have multiple evidence items for each control
    """
    evidence = db.relationship(
        "ProjectEvidence",
        secondary="evidence_association",
        lazy="dynamic",
        backref=db.backref("project_subcontrols", lazy="dynamic"),
    )
    comments = db.relationship(
        "SubControlComment",
        backref="subcontrol",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    operator_id = db.Column(db.String(), db.ForeignKey("users.id"))
    owner_id = db.Column(db.String(), db.ForeignKey("users.id"))
    subcontrol_id = db.Column(
        db.String, db.ForeignKey("subcontrols.id"), nullable=False
    )
    project_control_id = db.Column(
        db.String, db.ForeignKey("project_controls.id"), nullable=False
    )
    project_id = db.Column(db.String, db.ForeignKey("projects.id"), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    @property
    def project(self):
        return Project.query.get(self.project_id)

    def associate_with_evidence(self, evidence_id):
        if isinstance(evidence_id, str):
            evidence_id = [evidence_id]

        for record in evidence_id:
            EvidenceAssociation.add(self.id, record)
        return True

    def disassociate_with_evidence(self, evidence_id):
        if isinstance(evidence_id, str):
            evidence_id = [evidence_id]

        for record in evidence_id:
            EvidenceAssociation.remove(self.id, record)
        return True

    def update(
        self,
        applicable=None,
        implemented=None,
        notes=None,
        context=None,
        evidence=None,
        owner_id=None,
    ):
        """
        Update subcontrol for a project

        Args:

        Returns:
            subcontrol object
        """
        if applicable is not None:
            self.is_applicable = applicable
        if implemented is not None:
            self.implemented = implemented
        if notes is not None:
            self.notes = notes
        if context is not None:
            self.context = context
        if evidence:
            self.associate_with_evidence(evidence)

        if owner_id:
            self.owner_id = owner_id

        db.session.commit()
        return self


class RiskTags(db.Model):
    __tablename__ = "risk_tags"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    risk_id = db.Column(
        db.String(), db.ForeignKey("risk_register.id", ondelete="CASCADE")
    )
    tag_id = db.Column(db.String(), db.ForeignKey("tags.id", ondelete="CASCADE"))

    def as_dict(self):
        tag = Tag.query.get(self.tag_id)
        return {"name": tag.name, "color": tag.color}


class ProjectTags(db.Model):
    __tablename__ = "project_tags"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    project_id = db.Column(
        db.String(), db.ForeignKey("projects.id", ondelete="CASCADE")
    )
    tag_id = db.Column(db.String(), db.ForeignKey("tags.id", ondelete="CASCADE"))

    def as_dict(self):
        tag = Tag.query.get(self.tag_id)
        return {"name": tag.name, "color": tag.color}


class ControlTags(db.Model):
    __tablename__ = "control_tags"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    control_id = db.Column(
        db.String(), db.ForeignKey("project_controls.id", ondelete="CASCADE")
    )
    tag_id = db.Column(db.String(), db.ForeignKey("tags.id", ondelete="CASCADE"))


class PolicyTags(db.Model):
    __tablename__ = "policy_tags"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    policy_id = db.Column(
        db.String(), db.ForeignKey("project_policies.id", ondelete="CASCADE")
    )
    tag_id = db.Column(db.String(), db.ForeignKey("tags.id", ondelete="CASCADE"))


class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    name = db.Column(db.String(50), nullable=False, server_default="")
    label = db.Column(db.Unicode(255), server_default="")

    @staticmethod
    def find_by_name(name):
        return Role.query.filter(func.lower(Role.name) == func.lower(name)).first()

    @staticmethod
    def ids_to_names(list_of_role_ids):
        roles = []
        for role_id in list_of_role_ids:
            if role := Role.query.get(role_id):
                roles.append(role.name)
        return roles

    VALID_ROLE_NAMES = [
        "admin",
        "viewer",
        "user",
        "riskmanager",
        "riskviewer",
        "vendor",
    ]


class TenantMember(db.Model):
    """
    Represents a user in a specific tenant, with roles assigned.
    """

    __tablename__ = "tenant_members"
    __table_args__ = (db.UniqueConstraint("user_id", "tenant_id"),)

    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )

    user_id = db.Column(db.String, db.ForeignKey("users.id", ondelete="CASCADE"))
    tenant_id = db.Column(db.String, db.ForeignKey("tenants.id", ondelete="CASCADE"))

    # Many-to-Many Relationship: TenantMember <-> Role
    roles = db.relationship(
        "Role",
        secondary="tenant_member_roles",
        lazy="dynamic",
        backref=db.backref("tenant_members", lazy="dynamic"),
    )


class TenantMemberRole(db.Model):
    """
    This table assigns a specific role to a TenantMember (user in a specific tenant).
    """

    __tablename__ = "tenant_member_roles"

    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )

    tenant_member_id = db.Column(
        db.String, db.ForeignKey("tenant_members.id", ondelete="CASCADE")
    )
    role_id = db.Column(db.String, db.ForeignKey("roles.id", ondelete="CASCADE"))


class UserRole(db.Model):
    __tablename__ = "user_roles"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    user_id = db.Column(db.String(), db.ForeignKey("users.id", ondelete="CASCADE"))
    role_id = db.Column(db.String(), db.ForeignKey("roles.id", ondelete="CASCADE"))
    tenant_id = db.Column(db.String(), db.ForeignKey("tenants.id", ondelete="CASCADE"))

    @staticmethod
    def get_roles_for_user_in_tenant(user_id, tenant_id):
        roles = []
        role_mappings = (
            UserRole.query.filter(UserRole.user_id == user_id)
            .filter(UserRole.tenant_id == tenant_id)
            .all()
        )
        for mapping in role_mappings:
            role = Role.query.get(mapping.role_id)
            roles.append({"name": role.name.lower(), "user_role_id": mapping.id})
        return roles

    @staticmethod
    def get_mappings_for_role_in_tenant(role_name, tenant_id):
        role = Role.find_by_name(role_name)
        if not role:
            return []
        return (
            UserRole.query.filter(UserRole.role_id == role.id)
            .filter(UserRole.tenant_id == tenant_id)
            .all()
        )


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    is_active = db.Column(db.Boolean(), nullable=False, server_default="1")
    email = db.Column(db.String(255), nullable=False, unique=True)
    username = db.Column(db.String(100), unique=True)
    email_confirmed_at = db.Column(db.DateTime())
    email_confirm_code = db.Column(
        db.String,
        default=lambda: str(shortuuid.ShortUUID().random(length=6)).lower(),
    )
    password = db.Column(db.String(255), nullable=False, server_default="")
    last_password_change = db.Column(db.DateTime())
    login_count = db.Column(db.Integer, default=0)
    first_name = db.Column(db.String(100), nullable=False, server_default="")
    last_name = db.Column(db.String(100), nullable=False, server_default="")
    super = db.Column(db.Boolean(), nullable=False, server_default="0")
    built_in = db.Column(db.Boolean(), default=False)
    tenant_limit = db.Column(db.Integer, default=1)
    trial_days = db.Column(db.Integer, default=14)
    can_user_create_tenant = db.Column(db.Boolean(), nullable=False, server_default="1")
    license = db.Column(db.String(255), nullable=False, server_default="gold")
    memberships = db.relationship("TenantMember", backref="user", lazy="dynamic")
    projects = db.relationship("Project", backref="user", lazy="dynamic")
    assessments = db.relationship("AssessmentGuest", backref="user", lazy="dynamic")
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    VALID_LICENSE = ["trial", "silver", "gold"]

    @validates("license")
    def _validate_license(self, key, value):
        if value not in self.VALID_LICENSE:
            raise ValueError(f"Invalid license: {value}")
        return value

    @validates("email")
    def _validate_email(self, key, address):
        if address:
            try:
                email_validator.validate_email(address, check_deliverability=False)
            except:
                abort(422, "Invalid email")
        return address

    @staticmethod
    def validate_registration(email, password, password2):
        if not email:
            abort(500, "Invalid or empty email")
        if not misc.perform_pwd_checks(password, password_two=password2):
            abort(500, "Invalid password")
        if User.find_by_email(email):
            abort(500, "Email already exists")
        if not User.validate_email(email):
            abort(500, "Invalid email")

    @staticmethod
    def validate_email(email):
        if not email:
            return False
        try:
            email_validator.validate_email(email, check_deliverability=False)
        except:
            return False
        return True

    @staticmethod
    def email_to_object(user_or_email, or_404=False):
        if isinstance(user_or_email, User):
            return user_or_email
        if user := User.find_by_email(user_or_email):
            return user
        if or_404:
            abort(404, "User not found")
        return None

    def as_dict(self, tenant=None):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        if tenant:
            data["roles"] = self.roles_for_tenant(tenant)
        else:
            data["tenants"] = [tenant.name for tenant in self.get_tenants()]
        data.pop("password", None)
        return data

    def is_password_change_required(self):
        if not self.last_password_change:
            return True
        return False

    @staticmethod
    def add(
        email,
        password=None,
        username=None,
        first_name=None,
        last_name=None,
        confirmed=None,
        super=False,
        built_in=False,
        tenants=[],
        license="gold",
        is_active=True,
        require_pwd_change=False,
        send_notification=False,
        return_user_object=False,
    ):
        """
        Add user

        tenants: [{"id":1,"roles":["user"]}]
        """
        if not password:
            password = uuid4().hex

        User.validate_registration(email, password, password)

        email_confirmed_at = None
        if confirmed:
            email_confirmed_at = datetime.utcnow()
        if not username:
            username = f'{email.split("@")[0]}_{randrange(100, 1000)}'

        new_user = User(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            email_confirmed_at=email_confirmed_at,
            built_in=built_in,
            super=super,
            license=license,
            is_active=is_active,
        )
        new_user.set_password(password, set_pwd_change=not require_pwd_change)
        db.session.add(new_user)
        db.session.commit()
        for record in tenants:
            if tenant := Tenant.query.get(record["id"]):
                tenant.add_user(
                    user_or_email=new_user,
                    attributes={"roles": record["roles"]},
                    send_notification=False,
                )

        token = User.generate_invite_token(email=new_user.email, expiration=604800)
        link = "{}{}?token={}".format(
            current_app.config["HOST_NAME"], "register", token
        )
        sent_email = False
        if send_notification and current_app.is_email_configured:
            title = f"{current_app.config['APP_NAME']}: Invite"
            content = f"You have been added as a super user to {current_app.config['APP_NAME']}"
            send_email(
                title,
                recipients=[new_user.email],
                text_body=render_template(
                    "email/basic_template.txt",
                    title=title,
                    content=content,
                    button_link=link,
                ),
                html_body=render_template(
                    "email/basic_template.html",
                    title=title,
                    content=content,
                    button_link=link,
                ),
            )
            sent_email = True

        if return_user_object:
            return new_user

        return {
            "id": new_user.id,
            "success": True,
            "message": f"Added {new_user.email}",
            "access_link": link,
            "sent-email": sent_email,
        }

    def send_email_confirmation(self):
        if self.email_confirmed_at:
            abort(422, "user is already confirmed")
        if not current_app.is_email_configured:
            abort(500, "email is not configured")

        title = "Confirm Email"
        content = f"Please enter the following code to confirm your email: {self.email_confirm_code}"
        link = "{}{}?code={}".format(
            current_app.config["HOST_NAME"], "confirm-email", self.email_confirm_code
        )
        send_email(
            title,
            recipients=[self.email],
            text_body=render_template(
                "email/basic_template.txt",
                title=title,
                content=content,
                button_link=link,
            ),
            html_body=render_template(
                "email/basic_template.html",
                title=title,
                content=content,
                button_link=link,
                button_label="Confirm",
            ),
        )
        return True

    @staticmethod
    def find_by_email(email):
        if user := User.query.filter(
            func.lower(User.email) == func.lower(email)
        ).first():
            return user
        return False

    @staticmethod
    def find_by_username(username):
        if user := User.query.filter(
            func.lower(User.username) == func.lower(username)
        ).first():
            return user
        return False

    @staticmethod
    def verify_auth_token(token):
        data = misc.verify_jwt(token)
        if data is False:
            return False
        return User.query.get(data["id"])

    def generate_auth_token(self, expiration=600):
        data = {"id": self.id}
        return misc.generate_jwt(data, expiration)

    @staticmethod
    def verify_invite_token(token):
        if not token:
            return False
        data = misc.verify_jwt(token)
        if data is False:
            return False
        return data

    @staticmethod
    def generate_invite_token(email, tenant_id=None, expiration=600, attributes={}):
        data = {**attributes, **{"email": email}}
        if tenant_id:
            data["tenant_id"] = tenant_id
        return misc.generate_jwt(data, expiration)

    @staticmethod
    def verify_magic_token(token):
        data = misc.verify_jwt(token)
        if data is False:
            return False
        if data.get("type") != "magic_link":
            return False
        return data

    def generate_magic_link(self, tenant_id, expiration=600):
        data = {
            "email": self.email,
            "user_id": self.id,
            "tenant_id": tenant_id,
            "type": "magic_link",
        }
        return misc.generate_jwt(data, expiration)

    def get_username(self):
        if self.username:
            return self.username
        return self.email.split("@")[0]

    def get_projects(self, tenant_id=None):
        tenants = [t for t in self.get_tenants() if not tenant_id or t.id == tenant_id]
        return [
            project
            for tenant in tenants
            for project in tenant.projects.all()
            if Authorizer(self)._can_user_access_project(project)
        ]

    def get_tenants(self, own=False):
        if own:
            return Tenant.query.filter(Tenant.owner_id == self.id).all()
        if self.super:
            return Tenant.query.all()

        tenants_user_is_member_of = [member.tenant for member in self.memberships.all()]

        for tenant in Tenant.query.filter(Tenant.owner_id == self.id).all():
            if tenant not in tenants_user_is_member_of:
                tenants_user_is_member_of.append(tenant)
        return tenants_user_is_member_of

    def has_tenant(self, tenant):
        return tenant.has_member(self, get_user_object=True)

    def has_role_for_tenant(self, tenant, role_name):
        return tenant.has_member_with_role(self, role_name)

    def has_any_role_for_tenant(self, tenant, role_names):
        if not isinstance(role_names, list):
            role_names = [role_names]
        for role in role_names:
            if tenant.has_member_with_role(self, role):
                return True
        return False

    def has_all_roles_for_tenant(self, tenant, role_names):
        if not isinstance(role_names, list):
            role_names = [role_names]
        for role in role_names:
            if not tenant.has_member_with_role(self, role):
                return False
        return True

    def all_roles_by_tenant(self, tenant):
        data = []
        for role in Role.query.all():
            enabled = True if tenant.has_member_with_role(self, role.name) else False
            data.append(
                {"role_name": role.name, "role_id": role.id, "enabled": enabled}
            )
        return data

    def roles_for_tenant(self, tenant):
        return tenant.get_roles_for_member(self)

    def roles_for_tenant_by_id(self, tenant_id):
        tenant = Tenant.query.get(str(tenant_id))
        if not tenant:
            return []
        return self.roles_for_tenant(tenant)

    def set_password(self, password, set_pwd_change=True):
        if not misc.perform_pwd_checks(password, password_two=password):
            abort(422, "Invalid password - failed checks")

        self.password = generate_password_hash(password)
        if set_pwd_change:
            self.last_password_change = str(datetime.utcnow())

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def set_confirmation(self):
        self.email_confirmed_at = str(arrow.utcnow())


class PolicyLabel(db.Model):
    __tablename__ = "policy_labels"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    key = db.Column(db.String(), unique=True, nullable=False)
    value = db.Column(db.String(), nullable=False)
    owner_id = db.Column(db.String, db.ForeignKey("users.id"), nullable=False)
    tenant_id = db.Column(db.String, db.ForeignKey("tenants.id"), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return data

    @validates("key")
    def validate_key(self, table_key, key):
        if not key.startswith("policy_label_"):
            raise ValueError("key must start with policy_label_")
        return key


class Tag(db.Model):
    __tablename__ = "tags"
    __table_args__ = (db.UniqueConstraint("name", "tenant_id"),)
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    name = db.Column(db.String())
    color = db.Column(db.String(), default="blue")
    tenant_id = db.Column(db.String, db.ForeignKey("tenants.id"), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @staticmethod
    def find_by_name(name, tenant_id):
        tag_exists = (
            Tag.query.filter(Tag.tenant_id == tenant_id)
            .filter(func.lower(Tag.name) == func.lower(name))
            .first()
        )
        if tag_exists:
            return tag_exists
        return False

    @staticmethod
    def add(tag_name, tenant_id):
        if existing_tag := Tag.find_by_name(tag_name, tenant_id):
            return existing_tag

        tag = Tag(name=tag_name, tenant_id=tenant_id)
        db.session.add(tag)
        db.session.commit()
        return tag


class AssessmentGuest(db.Model):
    __tablename__ = "assessment_guests"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    assessment_id = db.Column(
        db.String, db.ForeignKey("assessments.id"), nullable=False
    )
    user_id = db.Column(db.String, db.ForeignKey("users.id"), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)


class FormItemMessage(db.Model, QueryMixin):
    __tablename__ = "form_item_messages"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    text = db.Column(db.String(), nullable=False)
    owner_id = db.Column(db.String(), db.ForeignKey("users.id"))
    is_vendor = db.Column(db.Boolean, default=False)
    item_id = db.Column(db.String, db.ForeignKey("form_items.id"), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["author"] = User.query.get(self.owner_id).email
        return data


class FormItem(db.Model, QueryMixin, DateMixin):
    __tablename__ = "form_items"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    review_status = db.Column(db.String(), nullable=False, default="info_required")
    data_type = db.Column(db.String(), nullable=False, default="text")
    order = db.Column(db.Integer, nullable=False)
    editable = db.Column(db.Boolean, default=True)
    disabled = db.Column(db.Boolean, default=True)
    applicable = db.Column(db.Boolean, default=True)
    score = db.Column(db.Integer, default=1)
    critical = db.Column(db.Boolean, default=False)
    attributes = db.Column(db.JSON(), default={})
    messages = db.relationship(
        "FormItemMessage",
        backref="item",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    response = db.Column(db.String)

    # TODO - Not implemented... see app.utils.misc.apply_rule
    rule = db.Column(db.JSON(), default={})
    rule_action = db.Column(db.String)

    # Used when status == 'info_required'
    info_required = db.Column(db.String)
    additional_response = db.Column(db.String)  # provided by vendor

    # Used when status == 'remediation_required'
    remediation_gap = db.Column(db.String)
    remediation_due_date = db.Column(db.DateTime)
    remediation_risk = db.Column(db.String, default="unknown")
    remediation_vendor_plan = db.Column(db.String)  # provided by vendor
    remediation_vendor_agreed = db.Column(db.Boolean)  # provided by vendor
    remediation_complete = db.Column(db.Boolean, default=False)
    remediation_complete_from_vendor = db.Column(db.Boolean, default=False)
    remediation_plan_required = db.Column(db.Boolean, default=False)
    # remediation_required_before_approval = db.Column(db.Boolean, default=False)

    # Used when status == 'complete'
    complete_notes = db.Column(db.String)

    responder_id = db.Column(db.String(), db.ForeignKey("users.id"))
    section_id = db.Column(db.String, db.ForeignKey("form_sections.id"), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    VALID_REVIEW_STATUS = [
        "pending",
        "info_required",
        "complete",
    ]
    VALID_REMEDIATION_RISK = ["unknown", "low", "moderate", "high"]

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["section"] = self.section.title
        messages = self.messages.all()
        data["messages"] = [message.as_dict() for message in messages]
        status = self.get_status()
        data["status"] = status
        data["get_review_description"] = self.get_review_description()
        data["vendor_answered"] = False
        if status == "answered":
            data["vendor_answered"] = True

        data["has_messages"] = False
        if len(data["messages"]) > 0:
            data["has_messages"] = True
        data["remediation_plan_complete"] = self.has_vendor_completed_remediation_plan()
        if self.remediation_due_date:
            data["remediation_due_date"] = self.simple_date(self.remediation_due_date)
        data["remediation_status"] = self.get_remediation_status()

        data["days_until_remediation_due_date"] = self.days_until_remediation_due_date()
        data["remediation_past_due"] = False
        data["remediation_due_date_upcoming"] = False

        if self.remediation_plan_required:
            if data["days_until_remediation_due_date"] <= 0:
                data["remediation_past_due"] = True
            if data["days_until_remediation_due_date"] <= 14:
                data["remediation_due_date_upcoming"] = True

        return data

    def days_until_remediation_due_date(self, humanize=False):
        if not self.remediation_due_date:
            return 0
        due_date = arrow.get(self.remediation_due_date).format("YYYY-MM-DD")
        if humanize:
            return arrow.get(due_date).humanize(granularity=["day"])
        return (arrow.get(due_date).date() - arrow.utcnow().date()).days

    def update_review_status(self, status):
        if status not in self.VALID_REVIEW_STATUS:
            abort(422, f"Invalid status: {status}")

        if status == self.review_status:
            abort(422, f"Status is already set to: {status}")

    def has_vendor_completed_remediation_plan(self):
        """
        Checks whether the vendor has filled out AND agreed to the remediation plan
        """
        if self.remediation_vendor_agreed and self.remediation_vendor_plan:
            return True

        return False

    def get_review_description(self):
        mapping = {
            "pending": "Waiting on completion from respondent",
            "info_required": "Requires more information from respondent",
            "remediation_required": "Requires remediation from the vendor",
            "complete": "Completed",
        }
        if self.remediation_plan_required:
            mapping["info_required"] = (
                "Requires more information (remediation plan) from respondent"
            )

        return mapping.get(self.review_status)

    def get_remediation_status(self):
        if self.remediation_plan_required is False:
            return "Remediation is not required"

        if self.remediation_vendor_agreed is None:
            return "Vendor has not responded"

        if self.remediation_vendor_agreed is False:
            return "Vendor has disagreed"

        if self.remediation_complete:
            return "Remediation is complete"

        if self.remediation_complete_from_vendor is False:
            return "Vendor has not completed the remediation"

        if self.remediation_complete_from_vendor is True:
            return "Vendor has completed the remediation however the InfoSec team has not responded."

        return "Unknown status"

    def create_message(self, text, owner, is_vendor=False):
        if not text:
            abort(422, "Text is required")

        if owner.has_role_for_tenant(self.section.form.tenant, "vendor"):
            is_vendor = True

        message = FormItemMessage(text=text, owner_id=owner.id, is_vendor=is_vendor)
        self.messages.append(message)
        db.session.commit()
        return message

    def get_status(self):
        if self.disabled:
            return "disabled"
        # if self.satisfied:
        #     return "satisfied"
        if not self.applicable:
            return "not applicable"
        if not self.response:
            return "unanswered"
        if self.response:
            return "answered"
        return "unknown"

    @validates("review_status")
    def _validate_review_status(self, key, value):
        if value not in self.VALID_REVIEW_STATUS:
            raise ValueError(f"Invalid review status: {value}")
        return value

    @validates("remediation_risk")
    def _validate_remediation_risk(self, key, value):
        if value not in self.VALID_REMEDIATION_RISK:
            raise ValueError(f"Invalid risk value: {value}")
        return value

    @validates("remediation_vendor_agreed")
    def _validate_remediation_vendor_agreed(self, key, value):
        if value is True and not self.remediation_vendor_plan:
            abort(422, "Remediation plan must be completed")
        return value

    @staticmethod
    def default_attributes():
        return {
            "placeholder": "Please complete",
            "label": "Please insert your question here",
            "required": True,
        }

    def update(
        self, section=None, attributes={}, disabled=None, critical=None, score=None
    ):
        # set attributes
        if attributes:
            if not isinstance(attributes, dict):
                abort(422)
            default_attributes = FormItem.default_attributes()
            attributes.update(
                {
                    key: value
                    for key, value in default_attributes.items()
                    if key not in attributes
                }
            )
            self.attributes = attributes

        if section:
            if found_section := self.section.form.get_section(section):
                self.section_id = found_section.id
        if disabled is not None:
            self.disabled = disabled
        if critical is not None:
            self.critical = critical
        if score is not None:
            self.score = int(score)
        db.session.commit()
        return self


class FormSection(db.Model, QueryMixin):
    __tablename__ = "form_sections"
    __table_args__ = (db.UniqueConstraint("title", "form_id"),)

    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    title = db.Column(db.String(), nullable=False, default="general")
    status = db.Column(db.String(), nullable=False, default="not_started")
    order = db.Column(db.Integer, nullable=False)
    items = db.relationship(
        "FormItem",
        backref="section",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    form_id = db.Column(db.String, db.ForeignKey("forms.id"), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self, edit_mode=True):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["disabled"] = 0
        data["responses"] = 0
        items = []
        for item in self.items.all():
            if not edit_mode and item.disabled:
                continue
            if item.disabled:
                data["disabled"] += 1
            if item.response:
                data["responses"] += 1
            items.append(item.as_dict())
        data["questions"] = len(items)
        data["items"] = items
        return data

    @validates("title")
    def _validate_title(self, key, title):
        if not title:
            raise ValueError("Invalid title")
        return title.lower()

    def update(self, title):
        if not title:
            abort(422, "Title is required")
        if self.title.lower() == "general":
            abort(422, "The 'general' section must not be updated")
        if self.assessment.get_section(title):
            abort(422, f"Title already exists:{title}")
        self.title = title.lower()
        db.session.commit()
        return self

    def create_item(self, **kwargs):
        data_type = kwargs.get("data_type")
        if data_type not in ["text", "select", "file_input", "checkbox"]:
            abort(422)

        order = kwargs.get("order")
        if not order:
            if latest_item := self.items.order_by(FormItem.order.desc()).first():
                order = latest_item.order
            else:
                order = 1
        kwargs["order"] = order
        item = FormItem(**kwargs)
        if not kwargs.get("attributes"):
            item.attributes = FormItem.default_attributes()
        self.items.append(item)
        db.session.commit()
        return item


class Assessment(db.Model, QueryMixin):
    __tablename__ = "assessments"
    __table_args__ = (db.UniqueConstraint("name", "vendor_id"),)
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    review_status = db.Column(db.String(), default="new")
    status = db.Column(db.String(), default="pending")
    disabled = db.Column(db.Boolean(), default=False)
    notes = db.Column(db.String())
    guests = db.relationship(
        "AssessmentGuest",
        backref="assessment",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    form_id = db.Column(db.String, db.ForeignKey("forms.id"), nullable=True)
    reviewer_id = db.Column(db.String, db.ForeignKey("users.id"), nullable=True)
    vendor_id = db.Column(db.String, db.ForeignKey("vendors.id"), nullable=True)
    owner_id = db.Column(db.String(), db.ForeignKey("users.id"), nullable=False)
    tenant_id = db.Column(db.String, db.ForeignKey("tenants.id"), nullable=False)
    due_before = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    VALID_REVIEW_STATUS = [
        "new",
        "pending_response",
        "pending_review",
        "complete",
    ]
    VALID_STATUS = ["pending", "approved", "not approved"]

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["guests"] = self.get_available_guests()
        if self.vendor_id:
            data["vendor"] = self.vendor.name
        data["owner"] = User.query.get(self.owner_id).email
        data["is_review_complete"] = self.is_review_complete()
        data["is_complete"] = self.is_complete()

        data["due_date_humanize"] = self.days_until_due_date(humanize=True)
        days_until_due_date = self.days_until_due_date()
        data["days_until_due_date"] = days_until_due_date
        data["due_date_upcoming"] = False
        data["past_due"] = False
        data["due_date"] = arrow.get(self.due_before).format("YYYY-MM-DD")
        if days_until_due_date <= 14 and not data["is_review_complete"]:
            data["due_date_upcoming"] = True
        if days_until_due_date <= 0 and not data["is_review_complete"]:
            data["past_due"] = True

        data["assessment_published"] = self.is_assessment_published()
        data["review_description"] = self.get_review_description()
        data["is_vendor_status"] = self.is_vendor_status()

        items = self.get_items(flatten=True)
        (
            total_items,
            total_vendor_answered,
            vendor_answered_percentage,
        ) = self.get_vendor_answered_percentage(items=items)
        data["total_items"] = total_items
        data["total_vendor_answered"] = total_vendor_answered
        data["vendor_answered_percentage"] = vendor_answered_percentage

        data["question_statuses"] = self.get_grouping_for_question_review_status(
            items=items
        )
        data["infosec_review_percentage"] = self.get_question_review_percentage(
            items=items
        )
        data["vendor_review_percentage"] = (
            self.get_question_review_percentage_for_vendor(items=items)
        )
        data["all_questions_complete"] = False
        if data["question_statuses"]["complete"] == total_items:
            data["all_questions_complete"] = True

        return data

    def update_review_status(self, status, send_notification=False, override=False):
        if status not in self.VALID_REVIEW_STATUS:
            abort(422, f"Invalid status: {status}")

        if self.review_status != "new" and status == "new":
            abort(422, "Assessment can not be reset to New")

        if override is False:
            if self.review_status == "pending_response" and status == "pending_review":
                can_change, can_change_response = self.can_vendor_submit_for_review()
                if not can_change:
                    abort(422, can_change_response)

            if self.review_status == "pending_review" and status == "pending_response":
                (
                    can_infosec_change,
                    can_infosec_change_response,
                ) = self.can_infosec_submit_for_response()
                if not can_infosec_change:
                    abort(422, can_infosec_change_response)

        self.review_status = status
        db.session.commit()

        if send_notification:
            self.send_status_update_to_vendor(status=status)
        return True

    def can_infosec_submit_for_response(self):
        if self.get_question_review_percentage() != 100:
            return (False, "InfoSec has not reviewed all of the questions")
        return (True, "InfoSec can submit for response")

    def can_vendor_submit_for_review(self):
        items = self.get_items(flatten=True)
        are_questions_answered = self.get_vendor_answered_percentage(items=items)
        if not are_questions_answered:
            return (False, "Vendor has incomplete questions")

        incomplete_info_required = 0
        incomplete_remediation_plans = 0
        for item in items:
            if (
                item.get("review_status") == "info_required"
                and item.get("additional_response") is None
            ):
                incomplete_info_required += 1

            if item.get("review_status") == "info_required" and not item.get(
                "remediation_plan_complete"
            ):
                incomplete_remediation_plans += 1

        if incomplete_info_required:
            return (
                False,
                f"Vendor has not provided additional information for {incomplete_info_required} questions",
            )

        if incomplete_remediation_plans:
            return (
                False,
                f"Vendor has not provided remediation plans for {incomplete_remediation_plans} questions",
            )

        return (True, "Vendor can submit for review")

    def get_vendor_answered_percentage(self, items=[]):
        """
        Returns total, total_answered, total_percentage
        """
        if not items:
            items = self.get_items(flatten=True)

        total_items = 0
        total_vendor_answered = 0

        for item in items:
            total_items += 1
            if item.get("vendor_answered"):
                total_vendor_answered += 1
        if total_items == 0:
            return (0, 0, 0)
        return (
            total_items,
            total_vendor_answered,
            round((total_vendor_answered / total_items) * 100),
        )

    def get_grouping_for_question_review_status(self, items=[]):
        """
        Get a grouping of FormItem review_status in dict form
        """
        review_status_count = {
            "pending": 0,
            "info_required": 0,
            # "remediation_required": 0,
            "complete": 0,
        }

        if not items:
            items = self.get_items(flatten=True)

        for item in items:
            status = item["review_status"]
            # if status in ("pending", "info_required") and not item["remediation_plan_complete"]:
            #     status = "remediation_required"
            review_status_count[status] += 1
        return review_status_count

    def get_question_review_percentage(self, items=[]):
        """
        Gets the percentage of questions that are reviewed by infosec
        by adding the remediation_required and complete status
        """
        review_status = self.get_grouping_for_question_review_status(items=items)
        if not review_status:
            return 0
        total_questions = sum(review_status.values())
        pending_questions = review_status.get("pending", 0)
        infosec_status = total_questions - pending_questions
        if not total_questions:
            return 0
        return round((infosec_status / total_questions) * 100)

    def get_question_review_percentage_for_vendor(self, items=[]):
        """
        Gets the percentage of questions that are reviewed by vendor
        by adding the remediation_required and complete status
        """
        review_status = self.get_grouping_for_question_review_status(items=items)
        if not review_status:
            return 0
        total_questions = sum(review_status.values())
        pending_questions = review_status.get("info_required", 0)
        infosec_status = total_questions - pending_questions
        if not total_questions:
            return 0
        return round((infosec_status / total_questions) * 100)

    def is_assessment_published(self):
        if self.review_status in ["pending_response", "pending_review", "complete"]:
            return True
        return False

    def is_vendor_status(self):
        """
        Checks to see if the status is waiting on the infosec team or the vendor
        """
        if self.review_status in [
            "pending_response",
        ]:
            return True
        return False

    def get_review_description(self):
        mapping = {
            "new": "Please edit and publish the assessment",
            "pending_response": "Waiting on completion from respondent",
            "pending_review": "Waiting on InfoSec to review",
            "complete": "Completed",
        }
        return mapping.get(self.review_status)

    def create_section(self, title, order=1):
        form = Form.query.get(self.form_id)
        return form.create_section(title, order)

    def get_section(self, title):
        if not self.form_id:
            return None
        form = Form.query.get(self.form_id)
        return form.get_section(title)

    def get_items(self, edit_mode=None, flatten=False):
        if not self.form_id:
            return []
        form = Form.query.get(self.form_id)
        return form.get_items(edit_mode=edit_mode, flatten=flatten)

    def is_review_complete(self):
        if self.review_status.lower() == "complete":
            return True
        return False

    def is_complete(self):
        if not self.is_review_complete() or self.status == "pending":
            return False
        return True

    def days_until_due_date(self, humanize=False):
        if not self.due_before:
            return 0
        if humanize:
            return arrow.get(self.due_before).humanize(granularity=["day"])
        return (arrow.get(self.due_before).date() - arrow.utcnow().date()).days

    @validates("status")
    def _validate_status(self, key, value):
        if value.lower() not in self.VALID_STATUS:
            raise ValueError(f"Invalid status: {value}")
        return value.lower()

    @validates("review_status")
    def _validate_review_status(self, key, value):
        if (
            self.review_status == "pending_response"
            and value.lower() == "pending_review"
        ):
            if self.get_vendor_answered_percentage()[2] != 100:
                abort(
                    422,
                    "All questions must be answered before moving to pending_review",
                )

        if value.lower() not in self.VALID_REVIEW_STATUS:
            abort(422, f"Invalid review status: {value}")

        return value.lower()

    def send_status_update_to_vendor(self, status):
        link = "{}{}".format(current_app.config["HOST_NAME"], "assessments")
        title = f"{current_app.config['APP_NAME']}: Form Status Update"
        content = f"Your assessment has changed status to: {status}. Please click the button below to view"
        send_email(
            title,
            recipients=[self.vendor.contact_email],
            text_body=render_template(
                "email/basic_template.txt",
                title=title,
                content=content,
                button_link=link,
            ),
            html_body=render_template(
                "email/basic_template.html",
                title=title,
                content=content,
                button_link=link,
            ),
        )
        return True

    def send_invite(self, email):
        link = "{}{}".format(current_app.config["HOST_NAME"], "assessments")
        title = f"{current_app.config['APP_NAME']}: Vendor Assessment"
        content = f"You have been invited to {current_app.config['APP_NAME']} for a assessment. Please click the button below to begin."
        send_email(
            title,
            recipients=[email],
            text_body=render_template(
                "email/basic_template.txt",
                title=title,
                content=content,
                button_link=link,
            ),
            html_body=render_template(
                "email/basic_template.html",
                title=title,
                content=content,
                button_link=link,
            ),
        )
        return True

    def send_reminder_email_to_vendor(self):
        guests = [guest.get("email") for guest in self.get_guests()]
        if not guests:
            abort(422, "There are no guests for the assessment")

        link = "{}{}/{}".format(current_app.config["HOST_NAME"], "assessments", self.id)
        title = f"{current_app.config['APP_NAME']}: Please complete the Assessment."
        content = f"Please remember to complete and submit the assessment."
        send_email(
            title,
            recipients=guests,
            text_body=render_template(
                "email/basic_template.txt",
                title=title,
                content=content,
                button_link=link,
            ),
            html_body=render_template(
                "email/basic_template.html",
                title=title,
                content=content,
                button_link=link,
            ),
        )
        return True

    def delete_guests(self, guests=[]):
        if not guests:
            self.guests.delete()
        else:
            if not isinstance(guests, list):
                guests = [guests]
            current_guests = self.guests.all()
            for record in current_guests:
                if record.user.email in guests:
                    db.session.delete(record)
        db.session.commit()
        return True

    def get_available_guests(self):
        """
        Returns a list of all users inside the tenant with the
        vendor role. Users already added as a vendor for this assessment
        will be marked with access:True
        """
        users = []
        for user in self.tenant.members.all():
            record = {"id": user.id, "email": user.email, "access": False}
            if self.can_user_be_added_as_a_guest(user):
                if self.has_guest(user.email):
                    record["access"] = True
                users.append(record)
        return users

    def can_user_be_added_as_a_guest(self, user):
        if self.tenant.has_member_with_role(user, "vendor"):
            return True
        return False

    def has_guest(self, email):
        return email in [x.user.email for x in self.guests.all()]

    def get_guests(self):
        return [{"id": x.user_id, "email": x.user.email} for x in self.guests.all()]

    def add_guest(self, email, send_notification=False):
        current_guest_emails = [x.user.email for x in self.guests.all()]
        if email not in current_guest_emails:
            current_guest_emails.append(email)
        return self.set_guests(
            guests=current_guest_emails, send_notification=send_notification
        )

    def set_guests(self, guests, send_notification=False):
        """
        Set guests for an assessment. If an email is not found
        in the tenant, the user will be invited with the vendor role
        and added to the assessment

        guests: list of emails
        send_notification: send email notification

        """
        guests_to_notify = []
        guests_to_add = []

        current_guests = [x.user_id for x in self.guests.all()]
        self.delete_guests()
        if not isinstance(guests, list):
            guests = [guests]

        for email in guests:
            if user := User.find_by_email(email):
                if self.can_user_be_added_as_a_guest(user) and not self.has_guest(
                    user.email
                ):
                    self.guests.append(AssessmentGuest(user_id=user.id))
                    if user.id not in current_guests and send_notification:
                        guests_to_notify.append(user.email)
            else:
                # Invite user to the tenant
                user = self.tenant.add_user(
                    user_or_email=email,
                    attributes={"roles": ["vendor"]},
                    send_notification=False,
                )
                self.guests.append(AssessmentGuest(user_id=user.get("id")))
                if send_notification:
                    guests_to_notify.append(email)

        db.session.commit()
        for email in guests_to_notify:
            self.send_invite(email)

        for email in guests_to_add:
            self.send_invite(email)
        return True

    def remove_guests(self, guests):
        """
        guests: list of emails
        """
        self.delete_guests(guests)


class ConfigStore(db.Model):
    __tablename__ = "config_store"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    key = db.Column(db.String())
    value = db.Column(db.String())
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @staticmethod
    def find(key):
        return ConfigStore.query.filter(ConfigStore.key == key).first()

    @staticmethod
    def upsert(key, value):
        found = ConfigStore.find(key)
        if found:
            found.value = value
            db.session.commit()
        else:
            c = ConfigStore(key=key, value=value)
            db.session.add(c)
            db.session.commit()
        return True


class Logs(db.Model):
    __tablename__ = "logs"
    id = db.Column(
        db.String,
        primary_key=True,
        default=lambda: str(shortuuid.ShortUUID().random(length=8)).lower(),
        unique=True,
    )
    namespace = db.Column(db.String(), nullable=False, default="general")
    level = db.Column(db.String(), nullable=False, default="info")
    action = db.Column(db.String(), default="get")
    message = db.Column(db.String(), nullable=False)
    success = db.Column(db.Boolean(), default=True)
    meta = db.Column(db.JSON(), default={})
    user_id = db.Column(db.String(), db.ForeignKey("users.id"), nullable=True)
    tenant_id = db.Column(db.String(), db.ForeignKey("tenants.id"), nullable=True)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    """
    """

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        if self.user_id:
            data["user_email"] = User.query.get(self.user_id).email
        if self.tenant_id:
            data["tenant_name"] = Tenant.query.get(self.tenant_id).name
        return data

    def as_readable(self):
        formatted_date = arrow.get(self.date_added).format("YYYY-MM-DD HH:mm:ss")
        user_str = f"User:{self.user_id}" if self.user_id else "User:N/A"
        tenant_str = f"Tenant:{self.tenant_id}" if self.tenant_id else "Tenant:N/A"
        level_str = f"{self.level.upper()}"
        action_str = f"Action:{self.action.upper()}"
        success_str = f"Success:{'Yes' if self.success else 'No'}"
        return f"[{formatted_date} - {level_str}] | {tenant_str} | {user_str} | {action_str} | {success_str} | {self.message}"

    @staticmethod
    def add_system_log(**kwargs):
        """
        Add system log - system logs are not necessarily tied to a tenant

        Logs.add_system_log(message="testing", level="error", action="put")
        """
        return Logs.add(namespace="system", **kwargs)

    @staticmethod
    def get_system_log(**kwargs):
        return Logs.get(namespace="system", **kwargs)

    @staticmethod
    def add(
        message="unknown",
        action="get",
        level="info",
        namespace="general",
        success=True,
        user_id=None,
        tenant_id=None,
        meta={},
        stdout=False,
    ):
        """
        Add log

        Logs.add(message="testing", level="error", action="put")
        """
        if level.lower() not in ["debug", "info", "warning", "error", "critical"]:
            level = "info"
        level = level.upper()
        action = action.upper()
        if meta is None:
            meta = {}
        msg = Logs(
            namespace=namespace.lower(),
            message=message,
            level=level,
            action=action,
            success=success,
            user_id=user_id,
            tenant_id=tenant_id,
            meta=meta,
        )
        db.session.add(msg)
        db.session.commit()
        if stdout:
            getattr(current_app.logger, level.lower())(
                f"Audit: {tenant_id} | {user_id} | {namespace} |  {success} | {action} | {message}"
            )
        return msg

    @staticmethod
    def get(
        id=None,
        message=None,
        action=None,
        namespace=None,
        level=None,
        user_id=None,
        tenant_id=None,
        success=None,
        limit=100,
        as_query=False,
        span=None,
        as_count=False,
        paginate=False,
        page=1,
        meta={},
        as_dict=False,
    ):
        """
        get_logs(level='error', namespace="my_namespace", meta={"key":"value":"key2":"value2"})
        """
        _query = Logs.query.order_by(Logs.date_added.desc()).limit(limit)

        if id:
            _query = _query.filter(Logs.id == id)
        if message:
            _query = _query.filter(Logs.message == message)
        if namespace:
            _query = _query.filter(func.lower(Logs.namespace) == func.lower(namespace))
        if action:
            _query = _query.filter(func.lower(Logs.action) == func.lower(action))
        if success is not None:
            _query = _query.filter(Logs.success == success)
        if user_id:
            _query = _query.filter(Logs.user_id == user_id)
        if tenant_id:
            _query = _query.filter(Logs.tenant_id == tenant_id)
        if level:
            if not isinstance(level, list):
                level = [level]
            _query = _query.filter(
                func.lower(Logs.level).in_([lvl.lower() for lvl in level])
            )

        if meta:
            for key, value in meta.items():
                _query = _query.filter(Logs.meta.op("->>")(key) == value)
        if span:
            _query = _query.filter(
                Logs.date_added >= arrow.utcnow().shift(hours=-span).datetime
            )
        if as_query:
            return _query
        if as_count:
            return _query.count()
        if paginate:
            return _query.paginate(page=page, per_page=10)
        if as_dict:
            return [log.as_dict() for log in _query.all()]
        return _query.all()


@login.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@listens_for(FormItem.remediation_vendor_agreed, "set")
def before_update_vendor_remediation_listener(target, value, old_value, initiator):
    """
    When remediation_vendor_agreed is set to True, we will update the review_status to complete
    b/c the vendor submitted a remediation plan and agreed to the Gap

    When set to False, we will update the review_status to "pending", so that the InfoSec team
    can review the rejected remediation
    """
    if value is True:
        target.review_status = "complete"
    if value is False:
        target.review_status = "pending"


@listens_for(ProjectSubControl.implemented, "set")
def after_update_project_sub_control_implementation_listener(
    target, value, old_value, initiator
):
    """
    When the implementation of a subcontrol is updated, we are going to calculate the project
    completion so that we can show a progress chart overtime
    """
    project = target.project
    if project.ready_for_completion_update():
        completion = project.completion_progress()
        project.add_completion_metric(completion=completion)
