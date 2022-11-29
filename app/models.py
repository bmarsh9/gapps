from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import func,and_,or_,not_
from sqlalchemy.orm import validates
from app.utils.mixin_models import LogMixin,DateMixin,SubControlMixin,ControlMixin
from flask_login import UserMixin
from flask import current_app
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


class Tenant(LogMixin, db.Model):
    __tablename__ = 'tenants'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    name = db.Column(db.String(64), unique=True)
    logo_ref = db.Column(db.String())
    contact_email = db.Column(db.String())
    license = db.Column(db.String())
    users = db.relationship('User', backref='tenant', lazy='dynamic')
    projects = db.relationship('Project', backref='tenant', lazy='dynamic')
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def generate_token(self, agent_id):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({ 'agent_id': agent_id, 'tenant': self.token}).decode('utf-8')

    def verify_token(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except SignatureExpired:
            current_app.logger.warning("SignatureExpired for token")
            return None
        except BadSignature:
            current_app.logger.warning("BadSignature for token")
            return None
        return True

class Evidence(LogMixin, db.Model):
    __tablename__ = 'evidence'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    name = db.Column(db.String(), unique=True)
    description = db.Column(db.String())
    content = db.Column(db.String())
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
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
    """framework specific features"""
    feature_evidence = db.Column(db.Boolean(), default=False)

    controls = db.relationship('Control', backref='framework', lazy='dynamic')
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return data

    @staticmethod
    def find_by_name(name):
        framework_exists = Framework.query.filter(func.lower(Framework.name) == func.lower(name)).first()
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
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self, include=[]):
        data = {}
        for c in self.__table__.columns:
            if c.name in include or not include:
                data[c.name] = getattr(self, c.name)
        return data

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
        template = {}
        for label in PolicyLabel.query.all():
            template[label.key] = label.value
        tenant = Tenant.query.first()
        template["organization"] = tenant.name
        return template

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
    dti = db.Column(db.String(), default="easy")
    dtc = db.Column(db.String(), default="easy")
    meta = db.Column(db.JSON(),default="{}")
    subcontrols = db.relationship('SubControl', backref='control', lazy='dynamic', cascade="all, delete")
    framework_id = db.Column(db.Integer, db.ForeignKey('frameworks.id'), nullable=False)
    project_controls = db.relationship('ProjectControl', backref='control', lazy='dynamic', cascade="all, delete")
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
    def create(data):
        # create or get framework
        if framework := data.get("framework"):
            if not (f := Framework.find_by_name(framework)):
                f = Framework(name=framework,
                    description=data.get("framework_description",f"Framework for {framework}"))
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
                dti=control.get("dti"),
                dtc=control.get("dtc"),
                meta=control.get("meta",{})
            )
            """
            if there are no subcontrols for the control, we are going to add the
            top-level control itself as the first subcontrol
            """
            subcontrols = control.get("subcontrols",[])
            if not subcontrols:
                subcontrols = [{"name":c.name,"description":c.description,"ref_code":c.ref_code}]
            for sub in subcontrols:
                fa = SubControl(
                    name=sub.get("name"),
                    description=sub.get("description","The description has not been documented"),
                    ref_code=sub.get("ref_code",c.ref_code),
                    mitigation=sub.get("mitigation","The mitigation has not been documented"),
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
    meta = db.Column(db.JSON(),default="{}")
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

class Project(LogMixin, db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    uuid = db.Column(db.String,  default=lambda: uuid4().hex, unique=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    controls = db.relationship('ProjectControl', backref='project', lazy='dynamic')
    policies = db.relationship('ProjectPolicy', backref='project', lazy='dynamic')
    tags = db.relationship('Tag', secondary='project_tags', lazy='dynamic',
        backref=db.backref('projects', lazy='dynamic'))
    owner_id = db.Column(db.Integer(), db.ForeignKey('users.id'), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self, with_controls=False):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["completion_progress"] = self.progress("complete")
        data["implemented_progress"] = self.progress("implemented")
        data["evidence_progress"] = self.progress("with_evidence")
        data["total_controls"] = self.controls.count()
        data["total_policies"] = self.policies.count()
#        data["total_applicable_controls"] = len(self.applicable_controls())
#        data["completed_controls"] = 0
#        data["uncompleted_controls"] = 0

        if with_controls:
            data["controls"] = [x.as_dict() for x in self.controls.all()]
        return data

    @staticmethod
    def create(name,owner_id,tenant_id,description=None,controls=[]):
        if not description:
            description = name
        project = Project(name=name,description=description,
            owner_id=owner_id,tenant_id=tenant_id)
        db.session.add(project)
        for control in controls:
            project.add_control(control, commit=False)
        db.session.commit()
        return True

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
            control_sub = ProjectSubControl(subcontrol_id=sub.id, owner_id=self.owner_id)
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

    def completion_progress(self, filter):
        total = 0
        controls = self.controls.all()
        for control in controls:
            result = control.is_complete()
            #haaaaaa

    def progress(self, filter):
        total = 0
        controls = self.controls.all()
        if not controls:
            return total
        for control in controls:
            result = control.progress(filter)
            total+=result
        return round((total/len(controls))*100,2)

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
    name = db.Column(db.String(), nullable=False)
    public_viewable = db.Column(db.Boolean(), default=False)
    ref_code = db.Column(db.String())
    description = db.Column(db.String())
    template = db.Column(db.String())
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
        return data

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
    tags = db.relationship('Tag', secondary='control_tags', lazy='dynamic',
        backref=db.backref('project_controls', lazy='dynamic'))
    subcontrols = db.relationship('ProjectSubControl', backref='p_control', lazy='dynamic')
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    control_id = db.Column(db.Integer, db.ForeignKey('controls.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

class ProjectSubControl(LogMixin, db.Model, SubControlMixin):
    __tablename__ = 'project_subcontrols'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    uuid = db.Column(db.String,  default=lambda: uuid4().hex, unique=True)
    implemented = db.Column(db.Integer(),default=0)
    is_applicable = db.Column(db.Boolean(), default=True)
    notes = db.Column(db.String())
    """
    framework specific fields
    """
    # SOC2
    auditor_feedback = db.Column(db.String())
    """
    may have multiple evidence items for each control
    """
    evidence = db.relationship('Evidence', secondary='evidence_association', lazy='dynamic',
        backref=db.backref('project_subcontrols', lazy='dynamic'))
    owner_id = db.Column(db.Integer(), db.ForeignKey('users.id'), nullable=False)
    subcontrol_id = db.Column(db.Integer, db.ForeignKey('subcontrols.id'), nullable=False)
    project_control_id = db.Column(db.Integer, db.ForeignKey('project_controls.id'), nullable=False)
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
    roles = db.relationship('Role', secondary='user_roles')
    projects = db.relationship('Project', backref='user', lazy='dynamic')
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    @staticmethod
    def add(email, password=None, username=None, confirmed=None, tenant_id=None, roles=[], create_role=False):
        email_confirmed_at = None
        if not password:
            password = uuid4().hex
        if not tenant_id:
            tenant_id = Tenant.query.first().id
        if confirmed:
            email_confirmed_at = datetime.utcnow()
        if not username:
            username = email
        new_user = User(
            email=email,
            username=username,
            email_confirmed_at=email_confirmed_at,
            tenant_id=tenant_id
        )
        for role in roles:
            if existing_role := Role.find_by_name(role):
                new_user.roles.append(existing_role)
            else:
                if create_role:
                    new_user.roles.append(Role(name=role))
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        return new_user

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
    def generate_invite_token(email, expiration=600):
        data = {'email': email}
        return misc.generate_jwt(data, expiration)

    def pretty_roles(self):
        data = []
        for role in self.roles:
            data.append(role.name.lower())
        return data

    def can_edit_roles(self):
        return "admin" in self.pretty_roles()

    def has_role(self,roles):
        '''checks if user has any of the listed roles'''
        if not roles:
            return False
        if not isinstance(roles,list) and not isinstance(roles,tuple):
            roles = [roles]
        my_roles = self.pretty_roles()
        for role in roles:
            if role.lower() in my_roles:
                return True
        return False

    def has_roles(self,roles):
        '''checks if user has all of the listed roles'''
        if not roles:
            return False
        if not isinstance(roles,list) and not isinstance(roles,tuple):
            roles = [roles]
        my_roles = self.pretty_roles()
        for role in roles:
            if role.lower() not in my_roles:
                return False
        return True

    def set_roles_by_name(self,roles):
        #roles = ["Admin","Another Role"]
        if not isinstance(roles,list):
            roles = [roles]
        new_roles = []
        for role in roles:
            found = Role.find_by_name(role)
            if found:
                new_roles.append(found)
        self.roles[:] = new_roles
        db.session.commit()
        return True

    def get_roles_for_form(self):
        roles = {}
        for role in Role.query.all():
            if role in self.roles:
                roles[role] = True
            else:
                roles[role] = False
        return roles

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
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

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
    def add(tenant_id, name):
        if Tag.find_by_name(name):
            return True
        tag = Tag(name=name,tenant_id=tenant_id)
        db.session.add(tag)
        db.session.commit()
        return tag

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(50), unique=True)

    @staticmethod
    def find_by_name(name):
        return Role.query.filter(func.lower(Role.name) == func.lower(name)).first()

class UserRoles(db.Model):
    __tablename__ = 'user_roles'
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
    role_id = db.Column(db.Integer(), db.ForeignKey('roles.id', ondelete='CASCADE'))

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
    message = db.Column(db.String(),nullable=False)
    meta = db.Column(db.JSON(),default="[]")
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    @staticmethod
    def add_log(message,log_type="info",namespace="general",meta={}):
        if log_type.lower() not in ["info","warning","error","critical"]:
            return False
        msg = Logs(namespace=namespace.lower(),message=message,
            log_type=log_type.lower(),meta=meta)
        db.session.add(msg)
        db.session.commit()
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
