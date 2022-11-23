from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import func,and_,or_,not_
from sqlalchemy.orm import validates
from app.utils.mixin_models import LogMixin,DateMixin
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
    """framework specific controls"""
    category = db.Column(db.String())
    subcategory = db.Column(db.String())
    dti = db.Column(db.String(), default="easy")
    dtc = db.Column(db.String(), default="easy")
    meta = db.Column(db.JSON(),default="{}")
    focus_areas = db.relationship('ControlListFocusArea', backref='control', lazy='dynamic', cascade="all, delete")
    framework_id = db.Column(db.Integer, db.ForeignKey('frameworks.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self, include=[], meta=True):
        data = {}
        if meta:
            data["focus_areas"] = []
            data["framework"] = self.framework.name
            focus_areas = self.focus_areas.all()
            data["focus_area_count"] = len(focus_areas)
            for area in focus_areas:
                data["focus_areas"].append(area.as_dict())
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
        # create controls and focus areas
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
            if there are no focus_areas for the control, we are going to add the
            top-level control itself as the first focus area.
            """
            focus_areas = control.get("focus_areas",[])
            if not focus_areas:
                focus_areas = [{"name":c.name,"description":c.description,"ref_code":c.ref_code}]
            for area in focus_areas:
                fa = ControlListFocusArea(
                    name=area.get("name"),
                    description=area.get("description"),
                    ref_code=area.get("ref_code",c.ref_code),
                    mitigation=area.get("mitigation","Mitigation has not been documented"),
                    meta=area.get("meta",{})
                )
                c.focus_areas.append(fa)
            f.controls.append(c)
        db.session.commit()
        return True

class ControlListFocusArea(LogMixin, db.Model):
    __tablename__ = 'control_focus_areas'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    uuid = db.Column(db.String,  default=lambda: uuid4().hex, unique=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    ref_code = db.Column(db.String())
    mitigation = db.Column(db.String())
    meta = db.Column(db.JSON(),default="{}")
    control_id = db.Column(db.Integer, db.ForeignKey('controls.id'), nullable=False)
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
        data["completion_progress"] = self.completion_progress()
        data["completed"] = self.progress("complete")
        data["implemented_progress"] = self.progress("implemented")
        data["evidence_progress"] = self.progress("with_evidence")
        data["total_controls"] = self.controls.count()
        data["total_policies"] = self.policies.count()
        data["total_applicable_controls"] = len(self.applicable_controls())
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
        control_dict = control.as_dict(meta=False, include=["name",
            "description","ref_code","system_level","category",
            "subcategory","dti","dtc","meta"])
        control_dict["control_id"] = control.id
        project_control = ProjectControl(**control_dict)

        for area in control.focus_areas.all():
            area_dict = area.as_dict(include=["name","description",
                "ref_code","mitigation","meta"
            ])
            area_dict["project_id"] = self.id
            if not area.ref_code:
                area_dict["ref_code"] = f"{control.ref_code}-{area.id}"
            control_area = ProjectControlFocusArea(**area_dict)
            project_control.focus_areas.append(control_area)
        self.controls.append(project_control)
        if commit:
            db.session.commit()
        return True

    def add_policy(self, policy, commit=True):
        if not policy:
            return False
        if self.has_policy(policy.id):
            return True
        policy_dict = policy.as_dict(include=["name",
            "description","ref_code","content","template"])
        policy_dict["policy_id"] = policy.id
        project_policy = ProjectPolicy(**policy_dict)
        self.policies.append(project_policy)
        if commit:
            db.session.commit()
        return True

    def delete_policy(self, id):
        if policy := self.policies.filter(ProjectPolicy.id == id).first():
            db.session.delete(policy)
            db.session.commit()
        return True

    def applicable_controls(self, include_inapplicable=False):
        controls = []
        for control in self.controls.all():
            if include_inapplicable:
                controls.append(control)
            else:
                if control.is_applicable():
                    controls.append(control)
        return controls

    def completion_progress(self):
        count = len(self.query_fa("implemented"))+len(self.query_fa("with_evidence"))
        if not count:
            return 0
        return round((count / len(self.query_fa()))*100,2)

    def progress(self, filter):
        count = self.query_fa(filter=filter)
        if not count:
            return 0
        return round((len(count) / len(self.query_fa()))*100,2)

    def query_fa(self, filter=None, include_inapplicable=False):
        """
        helper method to query focus areas
        """
        _query = ProjectControlFocusArea.query.filter(ProjectControlFocusArea.project_id == self.id)
        if not include_inapplicable:
            _query = _query.filter(ProjectControlFocusArea.status != "not applicable")
        if filter == "not_applicable":
            _query = self.focus_areas.filter(ProjectControlFocusArea.status == "not applicable")
        if filter == "not_implemented":
            _query = _query.filter(or_(ProjectControlFocusArea.status == "not implemented", ProjectControlFocusArea.status == None))
        elif filter == "implemented":
            _query = _query.filter(ProjectControlFocusArea.status == "implemented")
        elif filter == "missing_evidence":
            _query = _query.filter(or_(ProjectControlFocusArea.evidence == "",ProjectControlFocusArea.evidence == None))
        elif filter == "with_evidence":
            _query = _query.filter(and_(ProjectControlFocusArea.evidence != "",ProjectControlFocusArea.evidence != None))
        elif filter == "complete":
            _query = _query.filter(and_(ProjectControlFocusArea.status == "implemented",ProjectControlFocusArea.evidence != "",ProjectControlFocusArea.evidence != None))
        elif filter == "uncomplete":
             _query = _query.filter(or_(ProjectControlFocusArea.status!="implemented",ProjectControlFocusArea.evidence=="",ProjectControlFocusArea.evidence==None))
        return _query.all()

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

    def parent_object(self):
        return True

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

class ProjectControl(LogMixin, db.Model):
    __tablename__ = 'project_controls'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    uuid = db.Column(db.String,  default=lambda: uuid4().hex, unique=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    ref_code = db.Column(db.String())
    system_level = db.Column(db.Boolean(), default=True)
    category = db.Column(db.String())
    subcategory = db.Column(db.String())
    dti = db.Column(db.String(), default="easy")
    dtc = db.Column(db.String(), default="easy")
    meta = db.Column(db.JSON(),default="{}")
    tags = db.relationship('Tag', secondary='control_tags', lazy='dynamic',
        backref=db.backref('project_controls', lazy='dynamic'))
    focus_areas = db.relationship('ProjectControlFocusArea', backref='control', lazy='dynamic')
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    owner_id = db.Column(db.Integer(), db.ForeignKey('users.id'))
    control_id = db.Column(db.Integer, db.ForeignKey('controls.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self, with_areas=False):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["status"] = self.status()
        data["progress"] = self.progress("implemented")
        data["is_complete"] = self.is_complete()
        data["is_applicable"] = self.is_applicable()
        if with_areas:
            data["focus_areas"] = [x.as_dict() for x in self.query_fa(include_inapplicable=True)]
        return data

    def parent_object(self):
        return Control.query.get(self.control_id)

    def set_applicability(self, applicable):
        for focus in self.focus_areas.all():
            if applicable:
                focus.status = "not implemented"
            else:
                focus.status = "not applicable"
        db.session.commit()
        return True

    def status(self):
        if not self.is_applicable():
            return "not applicable"
        if self.is_complete():
            return "complete"
        if self.progress(filter="implemented") > 0:
            return "in progress"
        return "not started"

    def is_complete(self):
        if self.query_fa(filter="uncomplete"):
            return False
        return True

    def is_applicable(self):
        if self.query_fa():
            return True
        return False

    def progress(self, filter):
        count = self.query_fa(filter=filter)
        if not count:
            return 0
        return round((len(count) / len(self.query_fa()))*100,2)

    def query_fa(self, filter=None, include_inapplicable=False):
        """
        helper method to query focus areas
        """
        _query = self.focus_areas
        if not include_inapplicable:
            _query = _query.filter(ProjectControlFocusArea.status != "not applicable")
        if filter == "not_applicable":
            _query = self.focus_areas.filter(ProjectControlFocusArea.status == "not applicable")
        if filter == "not_implemented":
            _query = _query.filter(or_(ProjectControlFocusArea.status == "not implemented", ProjectControlFocusArea.status == None))
        elif filter == "implemented":
            _query = _query.filter(ProjectControlFocusArea.status == "implemented")
        elif filter == "missing_evidence":
            _query = _query.filter(or_(ProjectControlFocusArea.evidence == "",ProjectControlFocusArea.evidence == None))
        elif filter == "with_evidence":
            _query = _query.filter(and_(ProjectControlFocusArea.evidence != "",ProjectControlFocusArea.evidence != None))
        elif filter == "complete":
            _query = _query.filter(and_(ProjectControlFocusArea.status == "implemented",ProjectControlFocusArea.evidence != "",ProjectControlFocusArea.evidence != None))
        elif filter == "uncomplete":
             _query = _query.filter(or_(ProjectControlFocusArea.status!="implemented",ProjectControlFocusArea.evidence=="",ProjectControlFocusArea.evidence==None))
        return _query.all()

class ProjectControlFocusArea(LogMixin, db.Model):
    __tablename__ = 'project_control_focus_areas'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    uuid = db.Column(db.String,  default=lambda: uuid4().hex, unique=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    ref_code = db.Column(db.String())
    mitigation = db.Column(db.String())
    evidence = db.Column(db.String())
    notes = db.Column(db.String())
    feedback = db.Column(db.String())
    binary_status = db.Column(db.Boolean(), default=True)
    status = db.Column(db.String(), default="not implemented")
    meta = db.Column(db.JSON(),default="{}")
    tags = db.relationship('Tag', secondary='focus_tags', lazy='dynamic',
        backref=db.backref('project_control_focus_areas', lazy='dynamic'))
    control_id = db.Column(db.Integer, db.ForeignKey('project_controls.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["is_complete"] = self.is_complete()
        data["has_evidence"] = self.has_evidence()
        data["is_applicable"] = self.is_applicable()
        return data

    @validates("binary_status")
    def validate_key(self, key, value):
        if self.binary_status:
            value_list = ["not implemented","implemented", "not applicable"]
        else:
            value_list = ["implemented", "mostly","partially","not implemented","not applicable"]
        if value not in value_list:
            raise ValueError(f"value must be in {value_list}")
        return key

    def is_complete(self):
        if self.status == "implemented":
            return True
        return False

    def has_evidence(self):
        if self.evidence:
            return True
        return False

    def is_applicable(self):
        if self.status == "not applicable":
            return False
        return True

    def progress(self):
        progress_dict = {
            "implemented": 100,
            "mostly": 75,
            "partially": 50,
            "not implemented": 0,
            "not applicable": 0
        }
        if self.binary_status:
            if self.status in ["not implemented","not applicable"]:
                return 0
            return 100
        return progress_dict.get(self.status)

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

class FocusTags(db.Model):
    __tablename__ = 'focus_tags'
    id = db.Column(db.Integer(), primary_key=True)
    focus_id = db.Column(db.Integer(), db.ForeignKey('project_control_focus_areas.id', ondelete='CASCADE'))
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
