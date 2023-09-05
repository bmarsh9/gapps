from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import func,and_,or_,not_
from sqlalchemy.orm import validates
from app.utils.mixin_models import LogMixin,DateMixin,SubControlMixin,ControlMixin
from flask_login import UserMixin
from flask import current_app, request,render_template
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)
from datetime import datetime, timedelta
from app.login import login
from app.db import db
from uuid import uuid4
from app.utils import misc
import arrow
import json
import os
from string import Formatter
from app.integrations.azure.graph_client import GraphClient
from random import randrange
from app.utils.authorizer import Authorizer
import email_validator
import logging

from app.models.evidence_upload import EvidenceUpload

logger = logging.getLogger(__name__)

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
        # return ["soc2","cmmc","iso27001","hipaa",
        #     "nist_800_53_v4","nist_csf_v1.1","asvs_v4.0.1",
        #     "ssf","cisv8","pci_3.1","cmmc_v2","custom"]
        return [
            "iso27001",
            "iso27001_bos",
            "soc2"
        ]

    def get_valid_framework_languages(self):
        return ["eng", "bos"]

    def check_valid_framework(self, name):
        if name not in self.get_valid_frameworks():
            raise ValueError("framework is not implemented")
        return True

    def create_framework(self, name, add_controls=False):
        print(name)
        self.check_valid_framework(name)
        Framework.create(name, self)
        if add_controls:
            self.create_base_controls(name)
        # if add_policies:
        #     self.create_base_policies()
        return True

    def create_base_controls(self, name):
        self.check_valid_framework(name)
        with open(f"app/files/base_controls/{name}_controls.json") as f:
            controls=json.load(f)
            Control.create({"controls":controls,"framework":name}, self.id)
        return True

    def create_base_policies(self, language):
        for filename in os.listdir(f"app/files/base_policies/{language}/"):
            if filename.endswith(".html"):
                with open(f"app/files/base_policies/{language}/{filename}") as f:
                    name = filename.split(".")[0]
                    content = f.read()
                    p = Policy(name=name,
                        description=f"Content for the {name} policy",
                        # content=f.read(),
                        template=content,
                        tenant_id=self.id,
                        language=language
                    )
                    p_version = PolicyVersion(
                        policy=p,
                        content=content,
                    )
                    db.session.add(p)
                    db.session.add(p_version)
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

    @staticmethod
    def create(user, name, email, approved_domains):
        if exists := Tenant.find_by_name(name):
            return exists
        tenant = Tenant(owner_id=user.id, name=name.lower(),
            contact_email=email, approved_domains=approved_domains)
        evidence = Evidence(name="Evidence N/A",
            description="Built-in evidence that can be used to satisfy evidence collection")
        tenant.evidence.append(evidence)
        db.session.add(tenant)
        db.session.commit()
        # add user as Admin to the tenant
        tenant.add_user(user, roles=["admin"])
        return tenant

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
        for policy in Policy.query.filter(Policy.language == framework.get_language(), Policy.tenant_id == self.id).all():
            project.add_policy(policy)
        db.session.commit()
        return True

class Evidence(LogMixin, db.Model):
    __tablename__ = 'evidence'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    name = db.Column(db.String())
    description = db.Column(db.String())
    content = db.Column(db.String())
    collected_on= db.Column(db.DateTime, default=datetime.utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=True)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    owner = db.relationship("User", lazy='joined')

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["control_count"] = self.control_count()
        data["evidence_uploads"] = [evidence_upload.as_dict() for evidence_upload in self.evidence_uploads]
        data["owner_email"] = self.owner.email if self.owner else "Unknown"
        return data

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

    def get_language(self):
        if self.name in ["soc2", "iso27001"]:
            return "eng"

        if self.name in ["iso27001_bos"]:
            return "bos"

        return "eng"

    @staticmethod
    def create(name, tenant):
        tenant.check_valid_framework(name)
        data = {
            "name":name,
            "description":f"Framework for {name.upper()}",
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
    template = db.Column(db.String())
    visible = db.Column(db.Boolean(), default=True)
    project_policies = db.relationship('ProjectPolicy', backref=db.backref("policy", lazy='joined'), lazy='dynamic', cascade="all, delete")
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=True)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)
    policy_versions = db.relationship('PolicyVersion', lazy='joined', cascade="delete", backref="policy", order_by="PolicyVersion.version")
    owner_id = db.Column(db.Integer(), db.ForeignKey('users.id'))
    owner = db.relationship("User", foreign_keys=[owner_id], lazy='joined')
    reviewer_id = db.Column(db.Integer(), db.ForeignKey('users.id'))
    reviewer = db.relationship("User", foreign_keys=[reviewer_id], lazy='joined')
    public_viewable = db.Column(db.Boolean(), default=False)
    language = db.Column(db.String(3), nullable=False, server_default="eng")

    _policy_version_identifier = None

    @property
    def content(self):
        return policy_version.content if (policy_version:=self.get_policy_version()) else None

    @property
    def version(self):
        return policy_version.version if (policy_version:=self.get_policy_version()) else None

    def as_dict(self, version = None, include=[]):
        data = {}
        for c in self.__table__.columns:
            if c.name in include or not include:
                data[c.name] = getattr(self, c.name)

        policy_version = self.get_policy_version()

        data["content"] = policy_version.content if policy_version else ""
        data["version"] = policy_version.version if policy_version else ""
        data["content_updated_at"] = policy_version.date_added if policy_version else ""
        data["owner"] = self.owner.email if self.owner else None
        data["reviewer"] = self.reviewer.email if self.reviewer else None

        return data

    # @property
    # def policy_version_identifier(self):
    #     return self._policy_version_identifier

    # @policy_version_identifier.setter
    # def policy_version_identifier(self, value):
    #     self._policy_version_identifier = value

    def get_current_version(self):
        if not self.policy_versions:
            return None

        return self.policy_versions[-1]
    

    def get_policy_version(self, version=None):
        if not version:
            return self.get_current_version()

        return self.policy_versions[version-1] if self.policy_versions else None

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


class PolicyVersion(db.Model):
    __tablename__= "policy_version"
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    content = db.Column(db.String())
    version = db.Column(db.Integer(), default=1)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    policy_id = db.Column(db.Integer, db.ForeignKey("policies.id"))


class Control(LogMixin, db.Model):
    __tablename__ = 'controls'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    uuid = db.Column(db.String,  default=lambda: uuid4().hex, unique=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    ref_code = db.Column(db.String())
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
                subcontrols = [{"name":c.name,
                    "description":c.description, "ref_code":c.ref_code,
                    "mitigation":control.get("mitigation","The mitigation has not been documented"),
                    "guidance":control.get("guidance")
                }]
            for sub in subcontrols:
                fa = SubControl(
                    name=sub.get("name"),
                    description=sub.get("description","The description has not been documented"),
                    ref_code=sub.get("ref_code",c.ref_code),
                    mitigation=sub.get("mitigation"),
                    guidance=sub.get("guidance"),
                    implementation_group=sub.get("implementation_group"),
                    meta=sub.get("meta",{})
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
    meta = db.Column(db.JSON(),default="{}")
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

    user = db.relationship("User")

    # def user(self):
    #     return User.query.get(self.user_id)

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
            auditors.append(member.user)
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
        return member

    def set_auditors_by_id(self, user_ids):
        for auditor in self.auditors.all():
            self.remove_auditor(auditor.user)
        for user_id in user_ids:
            if user := User.query.get(user_id):
                self.add_auditor(user)
        return True

    def set_members_by_id(self, user_ids):
        for member in self.members.all():
            self.remove_member(member.user)
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
    # public_viewable = db.Column(db.Boolean(), default=False)
    content = db.Column(db.String())
    version = db.Column(db.Integer(), default=1)
    tags = db.relationship('Tag', secondary='policy_tags', lazy='dynamic',
        backref=db.backref('project_policies', lazy='dynamic'))
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    # owner_id = db.Column(db.Integer(), db.ForeignKey('users.id'))
    # reviewer_id = db.Column(db.Integer(), db.ForeignKey('users.id'))
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
        data["public_viewable"] = self.public_viewable
        # data["owner"] = self.owner()
        # data["reviewer"] = self.reviewer()
        return data

    @property
    def public_viewable(self):
        return self.policy.public_viewable

    # def owner(self):
    #     if self.owner_id:
    #         if user := User.query.get(self.owner_id):
    #             return user.email
    #     return None

    # def reviewer(self):
    #     if self.reviewer_id:
    #         if user := User.query.get(self.reviewer_id):
    #             return user.email
    #     return None

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
        if user := Policy.query.get(self.policy_id).owner:
            return user.email
        return None

    def reviewer_email(self):
        if user := Policy.query.get(self.policy_id).reviewer:
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

    def translate_to_html(self, policy_version=None):
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
        return fmt.format(self.policy.get_policy_version(policy_version).content, **self.get_template_variables())

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

    project = db.relationship("Project", lazy="select")

    owner = db.relationship("User", foreign_keys=owner_id, lazy='joined')
    operator = db.relationship("User", foreign_keys=operator_id, lazy='joined')

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

    def tenants(self):
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
        link = "{}{}".format(request.host_url,"questionnaires")
        title = f"{current_app.config['APP_NAME']}: Vendor Questionnaire"
        content = f"You have been invited to {current_app.config['APP_NAME']} for a questionnaire. Please click the button below to begin."
        GraphClient().send_email(
          title,
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
        expects [1,2,3]
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