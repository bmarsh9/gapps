from sqlalchemy.dialects.postgresql import JSON, ARRAY
from sqlalchemy import func, and_, or_, not_, Integer, cast, desc, asc, exc
from sqlalchemy.orm import validates
from app.utils.mixin_models import LogMixin,DateMixin,SubControlMixin,ControlMixin
from flask_login import UserMixin
from flask import current_app, request,render_template
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)
from datetime import datetime, timedelta
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
from app.utils.bg_worker import bg_app
from app.utils.bg_helper import BgHelper
from werkzeug.utils import secure_filename
import glob
import shutil
import string
import random
import logging


logger = logging.getLogger(__name__)

class Finding(LogMixin, db.Model):
    __tablename__ = 'findings'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    uuid = db.Column(db.String,  default=lambda: uuid4().hex, unique=True)
    title = db.Column(db.String())
    description = db.Column(db.String())
    mitigation = db.Column(db.String())
    status = db.Column(db.String(), default="open")
    risk = db.Column(db.Integer(), default=0)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    @staticmethod
    def get_status_list():
        return ["open", "in progress", "closed"]

    @validates('status')
    def _validate_status(self, key, status):
        if not status or status.lower() not in Finding.get_status_list():
            raise ValueError("invalid status")
        return status

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return data

class Locker(LogMixin, db.Model):
    __tablename__ = 'lockers'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    uuid = db.Column(db.String,  default=lambda: uuid4().hex, unique=True)
    name = db.Column(db.String())
    value = db.Column(db.JSON(), default={})
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'))
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for field in ["date_added", "date_updated"]:
            data[field] = str(getattr(self, field)) if getattr(self, field) else None
        return data

    @staticmethod
    def find_by_name(name, tenant_id):
        return Locker.query.filter(Locker.tenant_id == tenant_id).filter(func.lower(Locker.name) == func.lower(name)).first()

    @staticmethod
    def add(name, value, tenant_id):
        if Locker.find_by_name(name, tenant_id):
            raise ValueError("name already exists for tenant")
        locker = Locker(name=name, value=value, tenant_id=tenant_id)
        db.session.add(locker)
        db.session.commit()
        return True

    def has_integration(self, integration_id):
        return LockerAssociation.query.filter(LockerAssociation.locker_id==self.id).filter(LockerAssociation.integration_id==integration_id).first()

    def add_integration(self, integration_id):
        if self.has_integration(integration_id):
            return True
        assoc = LockerAssociation(locker_id=self.id, integration_id=integration_id)
        db.session.add(assoc)
        db.session.commit()
        return True

    def remove_integration(self, integration_id):
        if assoc := self.has_integration(integration_id):
            db.session.delete(assoc)
            db.session.commit()
        return True

class LockerAssociation(db.Model):
    __tablename__ = 'locker_association'
    id = db.Column(db.Integer(), primary_key=True)
    locker_id = db.Column(db.Integer(), db.ForeignKey('lockers.id', ondelete='CASCADE'))
    integration_id = db.Column(db.Integer(), db.ForeignKey('integrations.id', ondelete='CASCADE'))
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

class Integration(LogMixin, db.Model):
    __tablename__ = 'integrations'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    uuid = db.Column(db.String,  default=lambda: uuid4().hex, unique=True)
    name = db.Column(db.String())
    url = db.Column(db.String())
    tasks = db.relationship('Task', backref='integration',lazy='dynamic', cascade="all, delete-orphan")
    lockers = db.relationship('Locker', secondary='locker_association', lazy='dynamic',
        backref=db.backref('integration', lazy='dynamic'))
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["project"] = self.project.name
        data["project_id"] = self.project.id
        data["tasks"] = [task.as_dict() for task in self.tasks.all()]
        return data

    def add_task(self, name, cron, disabled=False):
        task = Task(name=name, cron=cron, disabled=disabled,
            queue=self.project.tenant_id)
        self.tasks.append(task)
        db.session.commit()
        return task

    def get_lockers(self, as_dict=False):
        data = {}
        for locker in self.lockers.all():
            if as_dict:
                data[locker.name] = locker.as_dict()
            else:
                data[locker.name] = locker
        return data

    def get_locker_by_name(self, name):
        return self.lockers.filter(Locker.name == name).first()

class Task(LogMixin, db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    uuid = db.Column(db.String,  default=lambda: uuid4().hex, unique=True)
    name = db.Column(db.String())
    queue = db.Column(db.String())
    disabled = db.Column(db.Boolean(), default=False)
    last_run = db.Column(db.DateTime)
    not_before = db.Column(db.DateTime)
    cron = db.Column(db.String())
    findings = db.relationship('Finding', backref='task',lazy='dynamic', cascade="all, delete-orphan")
    results = db.relationship('TaskResult', backref='task',lazy='dynamic', cascade="all, delete-orphan")
    integration_id = db.Column(db.Integer, db.ForeignKey('integrations.id'))
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self, with_lockers=False):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["integration"] = self.integration.name
        data["tenant"] = self.integration.project.tenant.name
        data["lock"] = self.get_lock()
        data["full_name"] = self.get_full_name()
        for field in ["last_run", "not_before", "date_added", "date_updated"]:
            data[field] = str(getattr(self, field)) if getattr(self, field) else None
        if with_lockers:
            data["lockers"] = self.integration.get_lockers(as_dict=True)
        return data

    @staticmethod
    def find_by_name(name, tenant_id):
        return Task.query.filter(Task.tenant_id == tenant_id).filter(func.lower(Task.name) == func.lower(name)).first()

    def add_finding(self, **kwargs):
        if not kwargs.get("status") or kwargs.get("status") not in Finding.get_status_list():
            kwargs["status"] = "open"
        finding = Finding(project_id=self.integration.project_id, **kwargs)
        self.findings.append(finding)
        db.session.commit()
        return finding

    def get_full_name(self):
        return f"{self.integration.name}:{self.name}"

    def get_lock(self):
        """
        the lock will be namespaced by tenant_id:integration_name:task_name
        """
        return f"{self.integration.project.tenant_id}:{self.integration.name}:{self.name}"

    def get_executions(self):
        with bg_app.open():
            return BgHelper().list_jobs(lock=self.get_lock())

    def get_summary(self):
        with bg_app.open():
            return BgHelper().list_tasks(name=self.get_lock())

    def save_results(self, data, version=None, update=False):
        result = None
        if version:
            # update data for the version
            result = self.get_result_by_version(version)
            if result and update:
                result.data = data
        # add new result
        if not result:
            result = TaskResult(data=data)
            if version:
                result.version = str(version)
            self.results.append(result)
        # commit the result
        try:
            db.session.commit()
            return result
        except exc.SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(e)
            return None

    def get_first_result(self, sort="id"):
        if sort == "version":
            return self.results.order_by(asc(cast(func.string_to_array(TaskResult.version, '.'), ARRAY(Integer)))).first()
        return self.results.order_by(TaskResult.id.asc()).first()

    def get_latest_result(self, sort="id"):
        if sort == "version":
            return self.results.order_by(desc(cast(func.string_to_array(TaskResult.version, '.'), ARRAY(Integer)))).first()
        return self.results.order_by(TaskResult.id.desc()).first()

    def get_result_by_version(self, version):
        return self.results.filter(TaskResult.version == str(version)).first()

    def sort_results(self, sort="id"):
        if sort == "version":
            return self.results.order_by(desc(cast(func.string_to_array(TaskResult.version, '.'), ARRAY(Integer)))).all()
        return self.results.order_by(TaskResult.id.desc()).all()

class TaskResult(LogMixin, db.Model):
    __tablename__ = 'task_results'
    __table_args__ = (db.UniqueConstraint('version', 'task_id'),)
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    uuid = db.Column(db.String,  default=lambda: uuid4().hex, unique=True)
    data = db.Column(db.JSON(), default={})
    version = db.Column(db.String())
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'))
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    @validates('version')
    def _validate_version(self, key, version):
        if not all([c.isdigit() or c == '.' for c in str(version)]):
            raise ValueError("invalid characters in version")
        return version

class Job(LogMixin, db.Model):
    __tablename__ = 'jobs'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    uuid = db.Column(db.String,  default=lambda: uuid4().hex, unique=True)
    result = db.Column(db.JSON(),default="{}")
    bg_id = db.Column(db.Integer, nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=True)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

class Tenant(LogMixin, db.Model):
    __tablename__ = 'tenants'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    uuid = db.Column(db.String,  default=lambda: uuid4().hex, unique=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    logo_ref = db.Column(db.String())
    contact_email = db.Column(db.String())
    license = db.Column(db.String())
    approved_domains = db.Column(db.String())
    magic_link_login = db.Column(db.Boolean(), default=False)
    storage_cap = db.Column(db.String(), default="10000000")
    user_roles = db.relationship('UserRole', backref='tenant',lazy='dynamic', cascade="all, delete-orphan")
    frameworks = db.relationship('Framework', backref='tenant', lazy='dynamic', cascade="all, delete-orphan")
    projects = db.relationship('Project', backref='tenant', lazy='dynamic', cascade="all, delete-orphan")
    policies = db.relationship('Policy', backref='tenant', lazy='dynamic', cascade="all, delete-orphan")
    controls = db.relationship('Control', backref='tenant', lazy='dynamic', cascade="all, delete-orphan")
    evidence = db.relationship('Evidence', backref='tenant', lazy='dynamic', cascade="all, delete-orphan")
    tags = db.relationship('Tag', backref='tenant', lazy='dynamic', cascade="all, delete-orphan")
    questionnaires = db.relationship('Questionnaire', backref='tenant', lazy='dynamic', cascade="all, delete-orphan")
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    labels = db.relationship('PolicyLabel', backref='tenant', lazy='dynamic', cascade="all, delete-orphan")
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    @validates('contact_email')
    def _validate_email(self, key, address):
        email_validator.validate_email(address, check_deliverability=False)
        return address

    @validates('name')
    def _validate_name(self, key, name):
        special_characters="!\"#$%&'()*+,-./:;<=>?@[\]^`{|}~"
        if any(c in special_characters for c in name):
            raise ValueError("Illegal characters in name")
        return name

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["owner_email"] = self.get_owner_email()
        return data

    @staticmethod
    def find_by_name(name):
        if tenant_exists := Tenant.query.filter(func.lower(Tenant.name) == func.lower(name)).first():
            return tenant_exists
        return False

    def get_owner_email(self):
        if not (user := User.query.get(self.owner_id)):
            return "unknown"
        return user.email

    def roles(self):
        return Role.query.all()

    def get_valid_frameworks(self):
        frameworks = []
        folder = current_app.config['FRAMEWORK_FOLDER']
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
        with open(os.path.join(current_app.config["FRAMEWORK_FOLDER"], f"{name}.json")) as f:
            controls=json.load(f)
            Control.create({"controls":controls,"framework":name}, self.id)
        return True

    def create_base_frameworks(self):
        for file in os.listdir(current_app.config['FRAMEWORK_FOLDER']):
            if file.endswith(".json"):
                name = file.split(".json")[0]
                if not Framework.find_by_name(name, self.id):
                    Framework.create(name, self)
                    self.create_base_controls_for_framework(name)
        return True

    def create_base_policies(self):
        for filename in os.listdir(current_app.config["POLICY_FOLDER"]):
            if filename.endswith(".html"):
                name = filename.split(".html")[0].lower()
                if not Policy.find_by_name(name, self.id):
                    with open(os.path.join(current_app.config["POLICY_FOLDER"], filename)) as f:
                        p = Policy(name=name,
                            description=f"Content for the {name} policy",
                            content=f.read(),
                            template=f.read(),
                            tenant_id=self.id
                        )
                        db.session.add(p)
        db.session.commit()
        return True

    def users_as_dict(self):
        users = []
        for user in self.users:
            d = user.as_dict()
            d["roles"] = self.get_roles_for_user(user)
            users.append(d)
        return users

    def users(self):
        user_ids = UserRole.query.filter(UserRole.tenant_id == self.id).distinct(UserRole.user_id).all()
        return [User.query.get(x.user_id) for x in user_ids]

    def get_questionnaires_for_user(self, user):
        user_roles = self.get_roles_for_user(user)
        data = []
        if user.super or any(role in ["admin", "editor"] for role in user_roles):
            return self.questionnaires.all()
        for questionnaire in self.questionnaires.all():
            if questionnaire.has_guest(user.email):
                data.append(questionnaire)
        return data

    def can_we_invite_user(self, email):
        if not self.approved_domains:
            return True
        name, tld = email.split("@")
        for domain in self.approved_domains.split(","):
            if domain == tld:
                return True
        return False

    def remove_user_from_projects(self, user):
        for project in self.projects.all():
            project.members.filter(ProjectMember.user_id == user.id).delete()
        db.session.commit()
        return True

    def remove_user_from_questionnaires(self, user):
        for questionnaire in self.questionnaires:
            QuestionnaireGuest.query.filter(QuestionnaireGuest.questionnaire_id == questionnaire.id).filter(QuestionnaireGuest.user_id == user.id).delete()
            db.session.commit()
        return True

    def set_roles_by_id_for_user(self, user, list_of_role_ids=[]):
        # convert id's to role names, sent by select2 js library
        new_roles = Role.ids_to_names(list_of_role_ids)
        current_roles = user.roles_for_tenant(self)
        # if vendor tag is removed, user will lose guest access to questionnaires
        if "vendor" in current_roles and "vendor" not in new_roles:
            self.remove_user_from_questionnaires(user)
        # remove user from tenant
        self.remove_user(user, skip_dependencies=True)
        self.add_user(user, new_roles)
        return True

    def add_user(self, user, roles=[]):
        if not roles:
            roles = ["user"]
        if not isinstance(roles, list):
            roles = [roles]
        # vendor role will override all other roles
        if "vendor" in roles:
            roles = ["vendor"]
        else:
            if "user" not in roles:
                roles.append("user")
        for role_name in roles:
            if not self.has_user_with_role(user, role_name):
                if role := Role.find_by_name(role_name):
                    user_role = UserRole(user_id=user.id, role_id=role.id, tenant_id=self.id)
                    db.session.add(user_role)
        db.session.commit()
        return True

    def remove_user(self, user, skip_dependencies=False):
        # update owner
        if self.owner_id == user.id:
            self.owner_id = User.query.filter(User.built_in == True).first().id

        # delete roles for user
        UserRole.query.filter(UserRole.tenant_id == self.id).filter(UserRole.user_id == user.id).delete()
        db.session.commit()
        # does not remove the user from dependencies
        # such as projects and questionnaires
        if skip_dependencies:
            return True
        self.remove_user_from_projects(user)
        self.remove_user_from_questionnaires(user)
        return True

    def remove_role_from_user(self, user, role_name):
        if role_name.lower() in ["user"]:
            return False
        if role := Role.find_by_name(role_name):
            UserRole.query.filter(UserRole.tenant_id == self.id).filter(UserRole.user_id == user.id).filter(UserRole.role_id == role.id).delete()
            db.session.commit()
        return True

    def get_roles_for_user(self, user):
        roles = []
        for record in UserRole.query.filter(UserRole.tenant_id == self.id).filter(UserRole.user_id == user.id).all():
            roles.append(Role.query.get(record.role_id).name)
        return roles

    def get_roles_by_user(self, by_email=False):
        data = {}
        for user in self.users():
            if by_email:
                data[user.email] = self.get_roles_for_user(user)
            else:
                data[user] = self.get_roles_for_user(user)
        return data

    def has_user(self, user):
        return UserRole.query.filter(UserRole.tenant_id == self.id).filter(UserRole.user_id == user.id).first() or self.owner_id == user.id

    def has_user_with_role(self, user, role_name):
        if role := Role.find_by_name(role_name):
            return UserRole.query.filter(UserRole.tenant_id == self.id).filter(UserRole.user_id == user.id).filter(UserRole.role_id == role.id).first()
        return False

    def get_evidence_folder(self):
        return os.path.join(current_app.config['EVIDENCE_FOLDER'], self.uuid)

    def get_size_of_evidence_folder(self):
        return sum(os.path.getsize(f) for f in glob.glob(f"{self.get_evidence_folder()}/*") if os.path.isfile(f))

    def can_save_file_in_folder(self, file):
        # calculate size from file object
        old_file_position = file.tell()
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(old_file_position, os.SEEK_SET)
        if self.get_size_of_evidence_folder() + size > int(self.storage_cap):
            return False
        return True

    @staticmethod
    def create(user, name, email, approved_domains=None, init=False):
        if Tenant.find_by_name(name):
            raise ValueError("tenant name already exists")
        tenant = Tenant(owner_id=user.id, name=name.lower(),
            contact_email=email, approved_domains=approved_domains)
        evidence = Evidence(name="Evidence N/A",
            description="Built-in evidence that can be used to satisfy evidence collection")
        tenant.evidence.append(evidence)
        db.session.add(tenant)
        db.session.commit()
        # add user as Admin to the tenant
        tenant.add_user(user, roles=["admin"])
        if init:
            tenant.create_base_frameworks()
            tenant.create_base_policies()
        # create folder for evidence
        tenant.create_evidence_folder()
        return tenant

    def create_evidence_folder(self):
        evidence_folder = self.get_evidence_folder()
        if not os.path.exists(evidence_folder):
            os.makedirs(evidence_folder)

    def delete(self):
        evidence_folder = self.get_evidence_folder()
        if os.path.exists(evidence_folder):
            shutil.rmtree(evidence_folder)
        db.session.delete(self)
        db.session.commit()
        return True

    def create_project(self, name, owner, framework=None, description=None, controls=[]):
        if not description:
            description = name
        project = Project(name=name,description=description,
            owner_id=owner.id, tenant_id=self.id)
        if framework:
            project.framework_id = framework.id
        self.projects.append(project)
        for control in controls:
            project.add_control(control, commit=False)
        db.session.commit()
        return project

class Evidence(LogMixin, db.Model):
    __tablename__ = 'evidence'
    __table_args__ = (db.UniqueConstraint('name', 'tenant_id'),)
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    name = db.Column(db.String())
    description = db.Column(db.String())
    content = db.Column(db.String())
    collected_on= db.Column(db.DateTime, default=datetime.utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=True)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["control_count"] = self.control_count()
        data["files"] = self.get_files(basename=True)
        return data

    def delete(self):
        [os.remove(file) for file in self.get_files()]
        db.session.delete(self)
        db.session.commit()
        return True

    def remove_controls(self, control_ids=[]):
        if control_ids:
            EvidenceAssociation.query.filter(EvidenceAssociation.evidence_id == self.id).filter(EvidenceAssociation.control_id.in_(control_ids)).delete()
        else:
            EvidenceAssociation.query.filter(EvidenceAssociation.evidence_id == self.id).delete()
        db.session.commit()
        return True

    def associate_with_controls(self, control_ids):
        """
        control_ids = list of ProjectSubControls id's. The operation will patch
        the current list (e.g. empty list will delete all associations with the evidence)
        """
        self.remove_controls()
        EvidenceAssociation.add(control_ids, self.id)
        return True

    def controls(self):
        id_list = [x.control_id for x in EvidenceAssociation.query.filter(EvidenceAssociation.evidence_id == self.id).all()]
        return ProjectSubControl.query.filter(ProjectSubControl.id.in_(id_list)).all()

    def control_count(self):
        return EvidenceAssociation.query.filter(EvidenceAssociation.evidence_id == self.id).count()

    def has_control(self, control_id):
        return EvidenceAssociation.exists(control_id, self.id)

    def get_files(self, as_dict=False, basename=False):
        files = glob.glob(os.path.join(self.tenant.get_evidence_folder(), f"{self.id}_*"))
        if as_dict:
            return [{"name":os.path.basename(file),"path":file} for file in files]
        if basename:
            return [os.path.basename(file) for file in files]
        return files

    def get_files_wo_prefix(self):
        files = []
        current_files = glob.glob(os.path.join(self.tenant.get_evidence_folder(), f"{self.id}_*"))
        for file in current_files:
            os.path.basename(file)
            files.append("_".join(os.path.basename(file).split("_")[2:]))
        return files

    def delete_files(self):
        [os.remove(file) for file in self.get_files()]
        return True

    def delete_file_by_name(self, name):
        for file in glob.glob(os.path.join(self.tenant.get_evidence_folder(), f"{self.id}_*_{name}")):
            os.remove(file)
        return True

    def get_secure_name_from_uploaded_file(self, filename):
        if ":upload:" not in filename:
            raise ValueError("invalid naming convention")
        name = filename.split(":upload:")[0].lower()
        file_ext = os.path.splitext(name)[1]
        if file_ext not in current_app.config['UPLOAD_EXTENSIONS']:
            raise ValueError("file type is not allowed")
        return secure_filename(name)

    def diff_files_with_checks(self, request_files, execute=False):
        """
        pass request.files.getlist("file") into this function
        """
        files = {}
        new_list = []
        # create list/dict of the new list of files
        for file in request_files:
            secure_name = self.get_secure_name_from_uploaded_file(file.filename)
            if secure_name.startswith(f"{self.id}_"):
                secure_name = "_".join(secure_name.split("_")[2:])
            files[secure_name] = file
            new_list.append(secure_name)

        # perform diff with existing list
        new_set = set(new_list)
        old_set = set(self.get_files_wo_prefix())
        inter = new_set & old_set
        added, deleted, unchanged = new_set - inter, old_set - inter, inter

        # add and delete files
        if execute:
            [self.save_file(file, files[file]) for file in added]
            [self.delete_file_by_name(file) for file in deleted]
        return added, deleted, unchanged

    def save_file(self, name, file_object):
        if not self.tenant.can_save_file_in_folder(file_object):
            raise ValueError("tenant does not have enough storage capacity")

        # create evidence folder if it doesnt exist
        self.tenant.create_evidence_folder()
        
        # generate new name for file
        file_uuid = ''.join(random.choices(string.ascii_uppercase +
                             string.digits, k=7))
        full_path = os.path.join(self.tenant.get_evidence_folder(), f"{self.id}_{file_uuid}_{name}".lower())
        file_object.save(full_path)
        return full_path

class EvidenceAssociation(db.Model):
    __tablename__ = 'evidence_association'
    id = db.Column(db.Integer(), primary_key=True)
    control_id = db.Column(db.Integer(), db.ForeignKey('project_subcontrols.id', ondelete='CASCADE'))
    evidence_id = db.Column(db.Integer(), db.ForeignKey('evidence.id', ondelete='CASCADE'))
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    @staticmethod
    def exists(control_id, evidence_id):
        return EvidenceAssociation.query.filter(EvidenceAssociation.control_id == control_id).filter(EvidenceAssociation.evidence_id == evidence_id).first()

    @staticmethod
    def add(control_id_list, evidence_id, commit=True):
        if not isinstance(control_id_list, list):
            control_id_list = [control_id_list]
        for control_id in control_id_list:
            if not EvidenceAssociation.exists(control_id, evidence_id):
                evidence = EvidenceAssociation(control_id=control_id,evidence_id=evidence_id)
                db.session.add(evidence)
        if commit:
            db.session.commit()
        return True

class PolicyAssociation(LogMixin, db.Model):
    __tablename__ = 'policy_associations'
    id = db.Column(db.Integer(), primary_key=True)
    policy_id = db.Column(db.Integer(), db.ForeignKey('policies.id', ondelete='CASCADE'))
    control_id = db.Column(db.Integer(), db.ForeignKey('controls.id', ondelete='CASCADE'))
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

class Framework(LogMixin, db.Model):
    __tablename__ = 'frameworks'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    uuid = db.Column(db.String,  default=lambda: uuid4().hex, unique=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String(), nullable=False)
    reference_link = db.Column(db.String())
    guidance = db.Column(db.String)
    """framework specific features"""
    feature_evidence = db.Column(db.Boolean(), default=False)

    controls = db.relationship('Control', backref='framework', lazy='dynamic')
    projects = db.relationship('Project', backref='framework', lazy='dynamic')
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=True)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["controls"] = self.controls.count()
        return data

    @staticmethod
    def create(name, tenant):
        data = {
            "name":name.lower(),
            "description":f"Framework for {name.capitalize()}",
            "feature_evidence":True,
            "tenant_id":tenant.id
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
        framework_exists = Framework.query.filter(Framework.tenant_id == tenant_id).filter(func.lower(Framework.name) == func.lower(name)).first()
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

class Policy(LogMixin, db.Model):
    __tablename__ = 'policies'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    uuid = db.Column(db.String,  default=lambda: uuid4().hex, unique=True)
    name = db.Column(db.String(), nullable=False)
    ref_code = db.Column(db.String())
    description = db.Column(db.String())
    content = db.Column(db.String())
    template = db.Column(db.String())
    version = db.Column(db.Integer(), default=1)
    visible = db.Column(db.Boolean(), default=True)
    project_policies = db.relationship('ProjectPolicy', backref='policy', lazy='dynamic', cascade="all, delete")
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=True)
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
        policy_exists = Policy.query.filter(Policy.tenant_id == tenant_id).filter(func.lower(Policy.name) == func.lower(name)).first()
        if policy_exists:
            return policy_exists
        return False

    def controls(self, as_id_list=False):
        control_id_list = []
        for assoc in PolicyAssociation.query.filter(PolicyAssociation.policy_id == self.id).all():
            control_id_list.append(assoc.control_id)
        if as_id_list:
            return control_id_list
        return Control.query.filter(Control.id.in_(control_id_list)).all()

    def has_control(self, id):
        return PolicyAssociation.query.filter(PolicyAssociation.policy_id == self.id).filter(PolicyAssociation.control_id == id).first()

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

class Control(LogMixin, db.Model):
    __tablename__ = 'controls'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    uuid = db.Column(db.String,  default=lambda: uuid4().hex, unique=True)
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
    mapping = db.Column(db.JSON(),default={})
    vendor_recommendations = db.Column(db.JSON(),default={})
    """framework specific fields"""
    # CMMC
    level = db.Column(db.Integer, default=1)

    # ISO27001
    operational_capability = db.Column(db.String())
    control_type = db.Column(db.String())

    # HIPAA
    dti = db.Column(db.String(), default="easy")
    dtc = db.Column(db.String(), default="easy")
    meta = db.Column(db.JSON(),default="{}")
    subcontrols = db.relationship('SubControl', backref='control', lazy='dynamic', cascade="all, delete")
    framework_id = db.Column(db.Integer, db.ForeignKey('frameworks.id'), nullable=False)
    project_controls = db.relationship('ProjectControl', backref='control', lazy='dynamic', cascade="all, delete")
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=True)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self, include=[], meta=True):
        data = {}
        if meta:
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
        return Control.query.filter(func.lower(Control.abs_ref_code) == func.lower(abs_ref_code)).first()

    def policies(self, as_id_list=False):
        policy_id_list = []
        for assoc in PolicyAssociation.query.filter(PolicyAssociation.policy_id == self.id).all():
            policy_id_list.append(assoc.policy_id)
        if as_id_list:
            return policy_id_list
        return Policy.query.filter(Policy.id.in_(policy_id_list)).all()

    def in_policy(self, policy_id):
        return policy_id in self.policies(as_id_list=True)

    @staticmethod
    def create(data, tenant_id):
        if framework := data.get("framework"):
            if not (f := Framework.find_by_name(framework, tenant_id)):
                f = Framework(name=framework,
                    description=data.get("framework_description",f"Framework for {framework}"),
                    tenant_id=tenant_id
                )
                db.session.add(f)
                db.session.commit()
        else:
            return False
        # create controls and subcontrols
        for control in data.get("controls",[]):
            c = Control(
                name=control.get("name"),
                description=control.get("description"),
                ref_code=control.get("ref_code"),
                abs_ref_code=f"{framework.lower()}__{control.get('ref_code')}",
                system_level=control.get("system_level"),
                category=control.get("category"),
                subcategory=control.get("subcategory"),
                references=control.get("references"),
                level=int(control.get("level",1)),
                guidance=control.get("guidance"),
                mapping=control.get("mapping"),
                vendor_recommendations=control.get("vendor_recommendations"),
                dti=control.get("dti"),
                dtc=control.get("dtc"),
                meta=control.get("meta",{}),
                tenant_id=tenant_id
            )
            """
            if there are no subcontrols for the control, we are going to add the
            top-level control itself as the first subcontrol
            """
            subcontrols = control.get("subcontrols",[])
            if not subcontrols:
                subcontrols = [{
                    "name":c.name,
                    "description":c.description,
                    "ref_code":c.ref_code,
                    "mitigation":control.get("mitigation","The mitigation has not been documented"),
                    "guidance":control.get("guidance"),
                    "tasks":control.get("tasks")
                }]
            for sub in subcontrols:
                fa = SubControl(
                    name=sub.get("name"),
                    description=sub.get("description","The description has not been documented"),
                    ref_code=sub.get("ref_code",c.ref_code),
                    mitigation=sub.get("mitigation"),
                    guidance=sub.get("guidance"),
                    implementation_group=sub.get("implementation_group"),
                    meta=sub.get("meta",{}),
                    tasks=sub.get("tasks",[])
                )
                c.subcontrols.append(fa)
            f.controls.append(c)
        db.session.commit()
        return True

class SubControl(LogMixin, db.Model):
    __tablename__ = 'subcontrols'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    uuid = db.Column(db.String,  default=lambda: uuid4().hex, unique=True)
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

    control_id = db.Column(db.Integer, db.ForeignKey('controls.id'), nullable=False)
    project_subcontrols = db.relationship('ProjectSubControl', backref='subcontrol', lazy='dynamic', cascade="all, delete")
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self, include=[]):
        data = {}
        for c in self.__table__.columns:
            if c.name in include or not include:
                data[c.name] = getattr(self, c.name)
        return data

class ProjectMember(LogMixin, db.Model):
    __tablename__ = 'project_members'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
    project_id = db.Column(db.Integer(), db.ForeignKey('projects.id', ondelete='CASCADE'))
    access_level = db.Column(db.String(), nullable=False, default="viewer") # manager, contributor, viewer, auditor
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def user(self):
        return User.query.get(self.user_id)

class Project(LogMixin, db.Model, DateMixin):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    uuid = db.Column(db.String,  default=lambda: uuid4().hex, unique=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    controls = db.relationship('ProjectControl', backref='project', lazy='dynamic',cascade="all, delete-orphan")
    policies = db.relationship('ProjectPolicy', backref='project', lazy='dynamic',cascade="all, delete-orphan")
    """
    permission toggles for project
    """
    can_auditor_read_scratchpad = db.Column(db.Boolean(), default=True)
    can_auditor_write_scratchpad = db.Column(db.Boolean(), default=False)
    can_auditor_read_comments = db.Column(db.Boolean(), default=True)
    can_auditor_write_comments = db.Column(db.Boolean(), default=True)

    """
    framework specific fields
    """
    # CMMC
    target_level = db.Column(db.Integer, default=1)

    # HIPAA
    tags = db.relationship('Tag', secondary='project_tags', lazy='dynamic',
        backref=db.backref('projects', lazy='dynamic'))
    comments = db.relationship('ProjectComment', backref='project', lazy='dynamic', cascade="all, delete-orphan")
    notes = db.Column(db.String())
    members = db.relationship('ProjectMember', backref='project', lazy='dynamic',cascade="all, delete-orphan")
    integrations = db.relationship('Integration', backref='project', lazy='dynamic', cascade="all, delete-orphan")
    findings = db.relationship('Finding', backref='project', lazy='dynamic', cascade="all, delete-orphan")
    owner_id = db.Column(db.Integer(), db.ForeignKey('users.id'), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    framework_id = db.Column(db.Integer, db.ForeignKey('frameworks.id'))
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self, with_controls=False, with_review_summary=False):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["completion_progress"] = self.progress("complete")
        data["implemented_progress"] = self.implemented_progress()
        data["evidence_progress"] = self.evidence_progress()
        data["total_controls"] = self.controls.count()
        data["total_policies"] = self.policies.count()
        if self.framework:
            data["framework"] = self.framework.name
        data["owner"] = self.user.email
        data["tenant"] = self.tenant.name
        data["auditors"] = [{"id":user.id,"email":user.email} for user in self.get_auditors()]
        if with_controls:
            data["controls"] = [x.as_dict() for x in self.controls.all()]
        if with_review_summary:
            data["review_summary"] = self.review_summary()
        return data

    @staticmethod
    def _query(tenant_ids=[], framework_ids=[], user=None):
        _query = Project.query
        if tenant_ids:
            if not isinstance(tenant_ids, list):
                tenant_ids = [tenant_ids]
            _query = _query.filter(Project.tenant_id.in_(tenant_ids))
        if framework_ids:
            if not isinstance(framework_ids, list):
                framework_ids = [framework_ids]
            _query = _query.filter(Project.framework_id.in_(framework_ids))
        return _query.all()

    def get_integration_summary(self):
        return []

    def add_integration(self, name):
        if self.integrations.filter(func.lower(Integration.name) == func.lower(self.name)).first():
            raise ValueError("integration already exists for tenant")
        integration = Integration(name=name)
        self.integrations.append(integration)
        db.session.commit()
        return integration

    def can_user_manage(self, user):
        if user.super:
            return True
        if user.id == self.owner_id:
            return True
        if user.has_role_for_tenant(self.project.tenant, "admin"):
            return True
        return False

    def review_summary(self):
        '''
        generate a dict summary of the different
        review statuses
        '''
        data = {"total":0}
        for record in ProjectSubControl.query.with_entities(ProjectSubControl.review_status, func.count(ProjectSubControl.review_status)).group_by(ProjectSubControl.review_status).filter(ProjectSubControl.project_id == self.id).all():
            data[record[0]] = record[1]
            data["total"] += record[1]
        return data

    def get_auditors(self):
        auditors = []
        for member in self.members.filter(ProjectMember.access_level == "auditor").all():
            auditors.append(member.user())
        return auditors

    def has_auditor(self, user):
        return self.has_member_with_access(user, "auditor")

    def add_member(self, user):
        if self.has_member(user):
            return True
        db.session.add(ProjectMember(user_id=user.id,project_id=self.id))
        db.session.commit()
        return True

    def remove_member(self, user):
        if not self.has_member(user):
            return True
        self.members.filter(ProjectMember.user_id == user.id).delete()
        db.session.commit()
        return True

    def has_member(self, user):
        if result := self.members.filter(ProjectMember.user_id == user.id).first():
            return result
        return False

    def has_member_with_access(self, user, access):
        if not isinstance(access, list):
            access = [access]
        if result := self.members.filter(ProjectMember.user_id == user.id).first():
            if result.access_level in access:
                return True
        return False

    def update_member_access(self, user_id, access_level):
        if member := self.members.filter(ProjectMember.user_id == user_id).first():
            if access_level not in ["manager", "viewer", "contributor","auditor"]:
                return False
            member.access_level = access_level
            db.session.commit()
        return False

    def set_auditors_by_id(self, user_ids):
        for auditor in self.auditors.all():
            self.remove_auditor(auditor.user())
        for user_id in user_ids:
            if user := User.query.get(user_id):
                self.add_auditor(user)
        return True

    def set_members_by_id(self, user_ids):
        for member in self.members.all():
            self.remove_member(member.user())
        for user_id in user_ids:
            if user := User.query.get(user_id):
                self.add_member(user)
        return True

    def subcontrols(self, as_query=False):
        _query = ProjectSubControl.query.filter(ProjectSubControl.p_control.has(project_id=self.id))
        if as_query:
            return _query
        return _query.all()

    def evidence_groupings(self):
        data = {}
        for sub in self.subcontrols():
            for evidence in sub.evidence.all():
                if evidence.id not in data:
                    data[evidence.id] = {"id":evidence.id,"name":evidence.name,"count":0}
                else:
                    data[evidence.id]["count"] += 1
        return data

    def evidence_progress(self):
        total = 0
        controls = self.controls.all()
        if not controls:
            return total
        for control in controls:
            total += control.progress("with_evidence")
        return round((total/len(controls)),2)

    def implemented_progress(self):
        total = 0
        controls = self.controls.all()
        if not controls:
            return total
        for control in controls:
            if control.is_applicable():
                total += control.implemented_progress()
        return round((total/len(controls)),2)

    def has_control(self, control_id):
        return self.controls.filter(ProjectControl.control_id == control_id).first()

    def has_policy(self, policy_id):
        return self.policies.filter(ProjectPolicy.policy_id == policy_id).first()

    def add_control(self, control, commit=True):
        if not control:
            return False
        if self.has_control(control.id):
            return True
        project_control = ProjectControl(control_id=control.id)
        for sub in control.subcontrols.all():
            control_sub = ProjectSubControl(subcontrol_id=sub.id, project_id=self.id)
            project_control.subcontrols.append(control_sub)
            # Add tasks (e.g. AuditorFeedback)
            if sub.tasks:
                for task in sub.tasks:
                    control_sub.feedback.append(AuditorFeedback(
                        title=task.get("title"), description=task.get("description"),
                        owner_id=self.owner_id
                    ))

        self.controls.append(project_control)
        if commit:
            db.session.commit()
        return True

    def add_policy(self, policy, commit=True):
        if not policy:
            return False
        if self.has_policy(policy.id):
            return True
        project_policy = ProjectPolicy(content=policy.content,policy_id=policy.id)
        self.policies.append(project_policy)
        if commit:
            db.session.commit()
        return True

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

    def progress(self, filter, percentage=True):
        total = 0
        controls = self.controls.all()
        if not controls:
            return total
        for control in controls:
            result = control.progress(filter)
            total+=result
        if not percentage:
            return total
        return round(total/len(controls),2)

    def completed_controls(self):
        controls = []
        for control in self.controls.all():
            if control.is_complete():
                controls.append(control)
        return controls

class ProjectPolicyAssociation(LogMixin, db.Model):
    __tablename__ = 'project_policy_associations'
    id = db.Column(db.Integer(), primary_key=True)
    policy_id = db.Column(db.Integer(), db.ForeignKey('project_policies.id', ondelete='CASCADE'))
    control_id = db.Column(db.Integer(), db.ForeignKey('project_controls.id', ondelete='CASCADE'))
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

class ProjectPolicy(LogMixin, db.Model):
    __tablename__ = 'project_policies'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    uuid = db.Column(db.String,  default=lambda: uuid4().hex, unique=True)
    public_viewable = db.Column(db.Boolean(), default=False)
    content = db.Column(db.String())
    version = db.Column(db.Integer(), default=1)
    tags = db.relationship('Tag', secondary='policy_tags', lazy='dynamic',
        backref=db.backref('project_policies', lazy='dynamic'))
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    owner_id = db.Column(db.Integer(), db.ForeignKey('users.id'))
    reviewer_id = db.Column(db.Integer(), db.ForeignKey('users.id'))
    policy_id = db.Column(db.Integer, db.ForeignKey('policies.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self, include=[]):
        data = {}
        for c in self.__table__.columns:
            if c.name in include or not include:
                data[c.name] = getattr(self, c.name)
        data["name"] = self.policy.name
        data["description"] = self.policy.description
        data["ref_code"] = self.policy.ref_code
        data["owner"] = self.owner()
        data["reviewer"] = self.reviewer()
        return data

    def owner(self):
        if self.owner_id:
            if user := User.query.get(self.owner_id):
                return user.email
        return None

    def reviewer(self):
        if self.reviewer_id:
            if user := User.query.get(self.reviewer_id):
                return user.email
        return None

    def get_controls(self):
        controls = []
        for control in ProjectPolicyAssociation.query.filter(ProjectPolicyAssociation.policy_id == self.id).all():
            controls.append(ProjectControl.query.get(control.control_id))
        return controls

    def has_control(self, id):
        return ProjectPolicyAssociation.query.filter(ProjectPolicyAssociation.policy_id == self.id).filter(ProjectPolicyAssociation.control_id == id).first()

    def total_controls(self):
        return ProjectPolicyAssociation.query.filter(ProjectPolicyAssociation.policy_id == self.id).count()

    def add_control(self, id):
        if not self.has_control(id):
            pa = ProjectPolicyAssociation(policy_id=self.id, control_id=id)
            db.session.add(pa)
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
        template = self.as_dict(include=["uuid","version", "name",
            "description","ref_code"])
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

class ProjectControl(LogMixin, db.Model, ControlMixin):
    __tablename__ = 'project_controls'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    uuid = db.Column(db.String,  default=lambda: uuid4().hex, unique=True)
    notes = db.Column(db.String())
    auditor_notes = db.Column(db.String())
    comments = db.relationship('ControlComment', backref='control', lazy='dynamic', cascade="all, delete-orphan")
    tags = db.relationship('Tag', secondary='control_tags', lazy='dynamic',
        backref=db.backref('project_controls', lazy='dynamic'))
    subcontrols = db.relationship('ProjectSubControl', backref='p_control', lazy='dynamic',cascade="all, delete-orphan")
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    control_id = db.Column(db.Integer, db.ForeignKey('controls.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

class AuditorFeedback(LogMixin, db.Model):
    __tablename__ = 'auditor_feedback'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    title = db.Column(db.String())
    description = db.Column(db.String())
    response = db.Column(db.String())
    is_complete = db.Column(db.Boolean(), default=False)
    auditor_complete = db.Column(db.Boolean(), default=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subcontrol_id = db.Column(db.Integer, db.ForeignKey('project_subcontrols.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["auditor_email"] = User.query.get(self.owner_id).email
        return data

    def complete(self):
        '''
        May need to revamp this code... but currently if the auditor
        says the feedback is complete, then it is

        is_complete = the infosec team's completion indication
        auditor_complete = the auditors indication
        '''
        return self.auditor_complete

class SubControlComment(LogMixin, db.Model):
    __tablename__ = 'subcontrol_comments'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    message = db.Column(db.String())
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subcontrol_id = db.Column(db.Integer, db.ForeignKey('project_subcontrols.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["author_email"] = User.query.get(self.owner_id).email
        return data

class ControlComment(LogMixin, db.Model):
    __tablename__ = 'control_comments'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    message = db.Column(db.String())
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    control_id = db.Column(db.Integer, db.ForeignKey('project_controls.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["author_email"] = User.query.get(self.owner_id).email
        return data

class ProjectComment(LogMixin, db.Model):
    __tablename__ = 'project_comments'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    message = db.Column(db.String())
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["author_email"] = User.query.get(self.owner_id).email
        return data

class ProjectSubControl(LogMixin, db.Model, SubControlMixin):
    __tablename__ = 'project_subcontrols'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    uuid = db.Column(db.String,  default=lambda: uuid4().hex, unique=True)
    implemented = db.Column(db.Integer(),default=0)
    is_applicable = db.Column(db.Boolean(), default=True)
    context = db.Column(db.String())
    notes = db.Column(db.String())
    auditor_notes = db.Column(db.String())
    review_status = db.Column(db.String(), default="not started") #["not started","infosec action","ready for auditor","action required","complete"]
    """
    framework specific fields
    """
    # SOC2
    auditor_feedback = db.Column(db.String())
    # CMMC
    process_maturity = db.Column(db.Integer(),default=0)

    """
    may have multiple evidence items for each control
    """
    evidence = db.relationship('Evidence', secondary='evidence_association', lazy='dynamic',
        backref=db.backref('project_subcontrols', lazy='dynamic'))
    comments = db.relationship('SubControlComment', backref='subcontrol', lazy='dynamic', cascade="all, delete-orphan")
    feedback = db.relationship('AuditorFeedback', backref='subcontrol', lazy='dynamic', cascade="all, delete-orphan")
    operator_id = db.Column(db.Integer(), db.ForeignKey('users.id'))
    owner_id = db.Column(db.Integer(), db.ForeignKey('users.id'))
    subcontrol_id = db.Column(db.Integer, db.ForeignKey('subcontrols.id'), nullable=False)
    project_control_id = db.Column(db.Integer, db.ForeignKey('project_controls.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

class ProjectTags(db.Model):
    __tablename__ = 'project_tags'
    id = db.Column(db.Integer(), primary_key=True)
    project_id = db.Column(db.Integer(), db.ForeignKey('projects.id', ondelete='CASCADE'))
    tag_id = db.Column(db.Integer(), db.ForeignKey('tags.id', ondelete='CASCADE'))

class ControlTags(db.Model):
    __tablename__ = 'control_tags'
    id = db.Column(db.Integer(), primary_key=True)
    control_id = db.Column(db.Integer(), db.ForeignKey('project_controls.id', ondelete='CASCADE'))
    tag_id = db.Column(db.Integer(), db.ForeignKey('tags.id', ondelete='CASCADE'))

class PolicyTags(db.Model):
    __tablename__ = 'policy_tags'
    id = db.Column(db.Integer(), primary_key=True)
    policy_id = db.Column(db.Integer(), db.ForeignKey('project_policies.id', ondelete='CASCADE'))
    tag_id = db.Column(db.Integer(), db.ForeignKey('tags.id', ondelete='CASCADE'))

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(50), nullable=False, server_default=u'')
    label = db.Column(db.Unicode(255), server_default=u'')

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
'''
class TenantUsers(db.Model):
    __tablename__ = 'tenant_users'
    id = db.Column(db.Integer(), primary_key=True)
    tenant_id = db.Column(db.Integer(), db.ForeignKey('tenants.id', ondelete='CASCADE'))
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
'''

class UserRole(db.Model):
    __tablename__ = 'user_roles'
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
    role_id = db.Column(db.Integer(), db.ForeignKey('roles.id', ondelete='CASCADE'))
    tenant_id = db.Column(db.Integer(), db.ForeignKey('tenants.id', ondelete='CASCADE'))

class User(LogMixin, db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean(), nullable=False, server_default='1')
    email = db.Column(db.String(255), nullable=False, unique=True)
    username = db.Column(db.String(100), unique=True)
    email_confirmed_at = db.Column(db.DateTime())
    password = db.Column(db.String(255), nullable=False, server_default='')
    last_password_change = db.Column(db.DateTime())
    first_name = db.Column(db.String(100), nullable=False, server_default='')
    last_name = db.Column(db.String(100), nullable=False, server_default='')
    super = db.Column(db.Boolean(), nullable=False, server_default='0')
    built_in = db.Column(db.Boolean(), default=False)
    tenant_limit = db.Column(db.Integer, default=1)
    can_user_create_tenant = db.Column(db.Boolean(), nullable=False, server_default='1')
    roles = db.relationship('Role', secondary='user_roles',lazy='dynamic',
                            backref=db.backref('users', lazy='dynamic'))
    projects = db.relationship('Project', backref='user', lazy='dynamic')
    questionnaires = db.relationship('QuestionnaireGuest', backref='user', lazy='dynamic')
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    @validates('email')
    def _validate_email(self, key, address):
        email_validator.validate_email(address, check_deliverability=False)
        return address

    @staticmethod
    def validate_registration(email, username, password, password2):
        if not email or not username:
            return False
        if not misc.perform_pwd_checks(password, password_two=password2):
            return False
        if User.find_by_email(email):
            return False
        if User.find_by_username(username):
            return False
        if not User.validate_email(email):
            return False
        return True

    @staticmethod
    def validate_email(email):
        if not email:
            return False
        try:
            email_validator.validate_email(email, check_deliverability=False)
        except:
            return False
        return True

    def as_dict(self, tenant=None):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        if tenant:
            data["roles"] = self.roles_for_tenant(tenant)
        else:
            data["tenants"] = [tenant.name for tenant in self.tenants()]
        data.pop("password",None)
        return data

    @staticmethod
    def add(email, password=None, username=None,
        confirmed=None, super=False, built_in=False, tenants=[]):
        '''
        tenants = [{"id":1,"roles":["user"]}]
        '''
        email_confirmed_at = None
        if not password:
            password = uuid4().hex
        if confirmed:
            email_confirmed_at = datetime.utcnow()
        if not username:
            username = f'{email.split("@")[0]}_{randrange(100, 1000)}'
        new_user = User(
            email=email,
            username=username,
            email_confirmed_at=email_confirmed_at,
            built_in=built_in,
            super=super
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        for record in tenants:
            if tenant := Tenant.query.get(record["id"]):
                tenant.add_user(new_user, roles=record["roles"])
        return new_user

    @staticmethod
    def find_by_email(email):
        if user := User.query.filter(func.lower(User.email) == func.lower(email)).first():
            return user
        return False

    @staticmethod
    def find_by_username(username):
        if user := User.query.filter(func.lower(User.username) == func.lower(username)).first():
            return user
        return False

    @staticmethod
    def verify_auth_token(token):
        data = misc.verify_jwt(token)
        if data is False:
            return False
        return User.query.get(data['id'])

    def generate_auth_token(self, expiration=600):
        data = {'id': self.id}
        return misc.generate_jwt(data, expiration)

    @staticmethod
    def verify_invite_token(token):
        data = misc.verify_jwt(token)
        if data is False:
            return False
        return data

    @staticmethod
    def generate_invite_token(email, tenant_id=None, expiration=600, attributes={}):
        data = {**attributes, **{'email': email}}
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
        data = {"email": self.email, "user_id":self.id, "tenant_id":tenant_id, "type":"magic_link"}
        return misc.generate_jwt(data, expiration)

    def get_username(self):
        if self.username:
            return self.username
        return self.email.split("@")[0]

    def get_projects_with_access_in_tenant(self, tenant):
        projects = []
        if not self.has_tenant(tenant) and not self.super:
            return projects
        for project in tenant.projects.all():
            if Authorizer(self)._can_user_access_project(project):
                projects.append(project)
        return projects

    def tenants(self, own=False):
        if own:
            return Tenant.query.filter(Tenant.owner_id == self.id).all()
        if self.super:
            return Tenant.query.all()
        tenant_ids = UserRole.query.filter(UserRole.user_id == self.id).distinct(UserRole.tenant_id).all()
        tenants_user_is_member_of = [Tenant.query.get(x.tenant_id) for x in tenant_ids]
        # tenants owned by user
        for tenant in Tenant.query.filter(Tenant.owner_id == self.id).all():
            if tenant not in tenants_user_is_member_of:
                tenants_user_is_member_of.append(tenant)
        return tenants_user_is_member_of

    def tenant_ids(self):
        return [x.id for x in self.tenants()]

    def has_tenant(self,tenant):
        return tenant.has_user(self)

    def has_tenant_or_super(self,tenant):
        if self.super:
            return True
        return self.has_tenant(tenant)

    def has_role_for_tenant(self, tenant, role_name):
        return tenant.has_user_with_role(self, role_name)

    def has_role_for_tenant_by_id(self, tenant_id, role_name):
        if not (tenant := Tenant.query.get(tenant_id)):
            return False
        return self.has_role_for_tenant(tenant, role_name)

    def has_any_role_for_tenant(self, tenant, role_names):
        if not isinstance(role_names, list):
            role_names = [role_names]
        for role in role_names:
            if tenant.has_user_with_role(self, role):
                return True
        return False

    def has_any_role_for_tenant_by_id(self, tenant_id, role_names):
        if not isinstance(role_names, list):
            role_names = [role_names]
        if not (tenant := Tenant.query.get(tenant_id)):
            return False
        return self.has_any_role_for_tenant(tenant, role_names)

    def has_all_roles_for_tenant(self, tenant, role_names):
        if not isinstance(role_names, list):
            role_names = [role_names]
        for role in role_names:
            if not tenant.has_user_with_role(self, role):
                return False
        return True

    def has_all_roles_for_tenant_by_id(self, tenant_id, role_names):
        if not isinstance(role_names, list):
            role_names = [role_names]
        if not (tenant := Tenant.query.get(tenant_id)):
            return False
        return self.has_all_roles_for_tenant(tenant, role_names)

    def is_auditor_for_project(self, project):
        return project.has_member_with_access(self, "auditor")

    def is_privileged_for_tenant(self,tenant):
        if self.super:
            return True
        if self.has_user_with_role(self, "admin"):
            return True
        return False

    def roles_by_tenants(self):
        data = {}
        for tenant in self.tenants():
            roles = tenant.get_roles_for_user(self)
            data[tenant.name] = roles
        return data

    def all_roles_by_tenant(self, tenant):
        data = []
        for role in Role.query.all():
            enabled = True if tenant.has_user_with_role(self, role.name) else False
            data.append({"role_name":role.name,
                "role_id":role.id,
                "enabled":enabled})
        return data

    def roles_for_tenant(self, tenant):
        return tenant.get_roles_for_user(self)

    def roles_for_tenant_by_id(self, tenant_id):
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            return []
        return self.roles_for_tenant(tenant)

    def set_password(self, password):
        self.password = generate_password_hash(password, method='sha256')
        self.last_password_change = str(datetime.utcnow())

    def check_password(self, password):
        return check_password_hash(self.password, password)

class PolicyLabel(LogMixin, db.Model):
    __tablename__ = 'policy_labels'
    id = db.Column(db.Integer(), primary_key=True)
    key = db.Column(db.String(), unique=True, nullable=False)
    value = db.Column(db.String(), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
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

class Tag(LogMixin, db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(), unique=True)
    color = db.Column(db.String(), default="blue")
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @staticmethod
    def find_by_name(name):
        tag_exists = Tag.query.filter(func.lower(Tag.name) == func.lower(name)).first()
        if tag_exists:
            return tag_exists
        return False

    @staticmethod
    def add(user_id, name, tenant):
        if Tag.find_by_name(name):
            return True
        tag = Tag(name=name,tenant_id=tenant.id,owner_id=user_id)
        db.session.add(tag)
        db.session.commit()
        return tag

class QuestionnaireGuest(LogMixin, db.Model):
    __tablename__ = 'questionnaire_guests'
    id = db.Column(db.Integer(), primary_key=True)
    questionnaire_id = db.Column(db.Integer, db.ForeignKey('questionnaires.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

class Questionnaire(LogMixin, db.Model):
    __tablename__ = 'questionnaires'
    id = db.Column(db.Integer(), primary_key=True)
    uuid = db.Column(db.String,  default=lambda: uuid4().hex, unique=True)
    name = db.Column(db.String(), nullable=False)
    vendor = db.Column(db.String())
    description = db.Column(db.String())
    enabled = db.Column(db.Boolean, default=True)
    feedback = db.Column(db.String()) # action required, approved, denied
    submitted = db.Column(db.Boolean, default=False)
    published = db.Column(db.Boolean, default=False)
    form = db.Column(db.JSON(),default={})
    submission = db.Column(db.JSON(),default={})
    guests = db.relationship('QuestionnaireGuest', backref='questionnaire', lazy='dynamic')
    owner_id = db.Column(db.Integer(), db.ForeignKey('users.id'), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    due_before = db.Column(db.DateTime)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["guests"] = self.get_guests()
        data["metrics"] = self.metrics()
        data["status"] = self.status()
        return data

    def status(self):
        if not self.enabled:
            return "disabled"
        if metrics := self.metrics():
            if metrics["percentage_complete"] == 0:
                return "not started"
            elif metrics["percentage_complete"] == 100 and self.submitted:
                return "complete"
            else:
                return "in progress"
        return "not started"

    def get_keys_from_dict(self, d):
        if 'key' in d:
            yield d['key']
        for k in d:
            if isinstance(d[k], list):
                for i in d[k]:
                    for j in self.get_keys_from_dict(i):
                        yield j

    def get_component_list(self):
        '''
        return list of keys from submission.form
        '''
        def flatten(d):
            if 'key' in d and d.get("input", False) == True and d['key'] != "submit":
                yield d['key']
            for k in d:
                if isinstance(d[k], list):
                    for i in d[k]:
                        for j in flatten(i):
                            yield j

        return list(flatten(self.form))

    def get_submission_data(self):
        data = {}
        components = self.get_component_list()
        if submission := self.submission:
            for key,value in submission.items():
                if key in components:
                    data[key] = value
        return data

    def can_render_form(self, user):
        if user.super or user.id == self.owner_id:
            return True
        if user.has_role_for_tenant(self.tenant, "admin"):
            return True
        if self.has_guest(user.email):
            return True
        return False

    def metrics(self):
        list_of_components = self.get_component_list()

        stats = {"total":0, "complete":0, "uncomplete":0, "percentage_complete":0, "percentage_uncomplete":0}
        stats["total"] = len(list_of_components)
        submission = self.get_submission_data()

        for component in list_of_components:
            if submission.get(component):
                stats["complete"] += 1
        stats["uncomplete"] = stats["total"] - stats["complete"]
        if stats["total"]:
            stats["percentage_complete"] = round(stats["complete"]/stats["total"]*100)
            stats["percentage_uncomplete"] = 100 - stats["percentage_complete"]
        return stats

    def send_invite(self, email):
        link = "{}{}".format(current_app.config["HOST_NAME"],"questionnaires")
        title = f"{current_app.config['APP_NAME']}: Vendor Questionnaire"
        content = f"You have been invited to {current_app.config['APP_NAME']} for a questionnaire. Please click the button below to begin."
        send_email(
          title,
          sender=current_app.config['MAIL_USERNAME'],
          recipients=[email],
          text_body=render_template(
            'email/basic_template.txt',
            title=title,
            content=content,
            button_link=link
          ),
          html_body=render_template(
            'email/basic_template.html',
            title=title,
            content=content,
            button_link=link
          )
        )
        return True

    def delete_guests(self):
        self.guests.delete()
        db.session.commit()
        return True

    def get_available_guests(self):
        '''
        returns a list of all users inside the tenant with the
        auditor role. users already added as a vendor for this questionnaire
        will be marked with vendor:True
        '''
        users = []
        for user in self.tenant.users():
            record = {"id":user.id,"email":user.email,"guest":False}
            if self.can_user_be_added_as_a_guest(user):
                if self.has_guest(user.email):
                    record["guest"] = True
                users.append(record)
        return users

    def can_user_be_added_as_a_guest(self, user):
        if self.tenant.has_user_with_role(user, "vendor"):
            return True
        return False

    def has_guest(self, email):
        return email in [x.user.email for x in self.guests.all()]

    def get_guests(self):
        return [{"id":x.user_id,"email":x.user.email} for x in self.guests.all()]

    def set_guests(self, guests, send_notification=False):
        '''
        user must already be a member of the tenant
        expects [1,2, 3]
        '''
        guests_to_notify = []
        current_guests = [x.user_id for x in self.guests.all()]
        self.delete_guests()
        for user_id in guests:
            # check if user id exists and a member of tenant
            if user := User.query.get(user_id):
                if self.can_user_be_added_as_a_guest(user) and not self.has_guest(user.email):
                    self.guests.append(QuestionnaireGuest(user_id=user.id))
                    # check which ones to notify
                    if user.id not in current_guests and send_notification:
                        guests_to_notify.append(user.email)
        db.session.commit()
        for email in guests_to_notify:
            self.send_invite(email)
        return True

class QuestionnaireTemplate(LogMixin, db.Model):
    __tablename__ = 'questionnaire_templates'
    id = db.Column(db.Integer(), primary_key=True)
    uuid = db.Column(db.String,  default=lambda: uuid4().hex, unique=True)
    name = db.Column(db.String(), unique=True)
    description = db.Column(db.String(), unique=True)
    form = db.Column(db.JSON(),default={})
    owner_id = db.Column(db.Integer(), db.ForeignKey('users.id'), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

class ConfigStore(db.Model,LogMixin):
    __tablename__ = 'config_store'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
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
    def upsert(key,value):
        found = ConfigStore.find(key)
        if found:
            found.value = value
            db.session.commit()
        else:
            c=ConfigStore(key=key,value=value)
            db.session.add(c)
            db.session.commit()
        return True

class Logs(db.Model):
    __tablename__ = 'logs'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    namespace = db.Column(db.String(),nullable=False,default="general")
    log_type = db.Column(db.String(),nullable=False,default="info")
    action = db.Column(db.String(),default="unknown")
    message = db.Column(db.String(),nullable=False)
    succeeded = db.Column(db.Boolean(), default=True)
    meta = db.Column(db.JSON(),default="[]")
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id'), nullable=True)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return data

    @staticmethod
    def add(message, user_id=None, action="unknown", level="info",
        namespace="general", succeeded=True, meta={}, stdout=False):
        if level.lower() not in ["debug","info","warning","error","critical"]:
            level = "info"
        msg = Logs(namespace=namespace.lower(),message=message,
            log_type=level.lower(),action=action.lower(),
            succeeded=succeeded,user_id=user_id, meta=meta)
        db.session.add(msg)
        db.session.commit()
        if stdout:
            getattr(logging, level.lower())(message)
        return True

    @staticmethod
    def get_logs(log_type=None,limit=100,as_query=False,span=None,as_count=False,paginate=False,page=1,namespace="general",meta={}):
        '''
        get_logs(log_type='error',namespace="my_namespace",meta={"key":"value":"key2":"value2"})
        '''
        _query = Logs.query.filter(Logs.namespace == namespace.lower()).order_by(Logs.id.desc())
        if log_type:
            if not isinstance(log_type,list):
                log_type = [log_type]
            _query = _query.filter(Logs.log_type.in_(log_type))

        if meta:
            for key,value in meta.items():
                _query = _query.filter(Logs.meta.op('->>')(key) == value)
        if span:
            _query = _query.filter(Logs.date_added >= arrow.utcnow().shift(hours=-span).datetime)
        if as_query:
            return _query
        if as_count:
            return _query.count()
        if paginate:
            return _query.paginate(page=page, per_page=10)
        return _query.limit(limit).all()

@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
