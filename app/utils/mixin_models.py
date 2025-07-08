from app import db
from flask import current_app
from sqlalchemy.ext.declarative import declared_attr
from functools import partial
from app.utils.authorizer import Authorizer
from sqlalchemy import func
import arrow


class ControlMixin(object):
    __table_args__ = {"extend_existing": True}
    """
    mixin model should only be attached to
    class ProjectControl
    """

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    def as_dict(self):
        parent_fields = [
            "name",
            "ref_code",
            "system_level",
            "category",
            "subcategory",
            "is_custom",
        ]
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for field in parent_fields:
            data[field] = getattr(self.control, field)

        return {**self.generate_stats(), **data}

    def review_complete(self):
        if self.review_status in ["complete"]:
            return True
        return False

    def action_required_from_auditor(self):
        if self.review_status in ["ready for auditor"]:
            return True
        return False

    def action_required_from_infosec(self):
        if self.review_status in ["infosec action"]:
            return True
        return False

    def get_feedback(self, as_dict=False):
        query = self.feedback.all()
        if as_dict:
            return [feedback.as_dict() for feedback in query]
        return query

    def complete_feedback(self):
        data = []
        for feedback in self.get_feedback():
            if feedback.is_complete:
                data.append(feedback)
        return data

    def generate_stats(self, subcontrols=None):
        if not subcontrols:
            subcontrols = self.subcontrols.order_by(
                current_app.models["ProjectSubControl"].date_added.desc()
            ).all()
        feedback = self.get_feedback()
        data = {
            "description": self.control.description,
            "guidance": self.control.guidance,
            "status": "not started",
            "is_applicable": True,
            "is_complete": False,
            "review_complete": self.review_complete(),
            "progress_completed": 0,
            "progress_implemented": 0,
            "progress_evidence": 0,
            "feedback": self.get_feedback(as_dict=True),
            "subcontrols": [],
            "owners": [],
            "tags": [{"id": tag.id, "name": tag.name} for tag in self.tags.all()],
            "comments": self.get_comments(),
            "stats": {
                "feedback": len(feedback),
                "complete_feedback": sum(1 for task in feedback if task.is_complete),
                "evidence": 0,
                "subcontrols": len(subcontrols),
                "subcontrols_complete": 0,
                "applicable_subcontrols": 0,
                "inapplicable_subcontrols": 0,
                "infosec_status": 0,
                "auditor_status": 0,
                "owners": 0,
            },
        }

        implemented = 0
        completed = 0
        evidence = 0
        for subcontrol in subcontrols:
            sub = subcontrol.as_dict()
            if subcontrol.owner_id:
                data["owners"].append(sub["owner"])
                data["stats"]["owners"] += 1

            data["subcontrols"].append(sub)

            if not sub["is_applicable"]:
                data["stats"]["inapplicable_subcontrols"] += 1
                continue
            data["stats"]["applicable_subcontrols"] += 1
            implemented += sub["implemented"]
            completed += sub["progress_completed"]
            if sub["has_evidence"]:
                evidence += 1

            if sub["is_complete"]:
                data["stats"]["subcontrols_complete"] += 1

            data["stats"]["evidence"] += len(sub.get("evidence", []))
            data["stats"]["infosec_status"] += sub.get("infosec_status", 0)
            data["stats"]["auditor_status"] += sub.get("auditor_status", 0)

        if completed:
            data["progress_completed"] = round(
                (completed / data["stats"]["applicable_subcontrols"]), 0
            )
        if implemented:
            data["progress_implemented"] = round(
                (implemented / data["stats"]["applicable_subcontrols"]), 0
            )
        if evidence:
            data["progress_evidence"] = round(
                (evidence / data["stats"]["applicable_subcontrols"]) * 100, 0
            )

        if not data["stats"]["applicable_subcontrols"]:
            data["is_applicable"] = False

        if (
            data["stats"]["subcontrols_complete"]
            == data["stats"]["applicable_subcontrols"]
        ):
            data["is_complete"] = True

        if not data["is_applicable"]:
            data["status"] = "not applicable"
        elif data["is_complete"]:
            data["status"] = "complete"
        elif data["progress_implemented"] or data["progress_evidence"]:
            data["status"] = "in progress"

        data["implemented_status"] = "partially implemented"
        if data["progress_completed"] == 100:
            data["implemented_status"] = "fully implemented"
        elif data["progress_completed"] == 0:
            data["implemented_status"] = "not implemented"

        return data

    def get_comments(self):
        return [comment.as_dict() for comment in self.comments.all()]

    def get_subcontrols(self, only_applicable=False, as_query=False):
        _query = self.subcontrols
        if only_applicable:
            _query = _query.filter(
                current_app.models["ProjectSubControl"].is_applicable == True
            )
        if as_query:
            return _query
        return _query.all()

    def framework(self):
        return self.control.framework

    def set_applicability(self, applicable):
        for subcontrol in self.subcontrols.all():
            subcontrol.is_applicable = applicable
        db.session.commit()
        return True

    def status(self):
        """
        If an auditor is added to the project, then the auditor must set the review_status to complete
        for the control to be complete

        If there is not an auditor in the project, then the team must 100% implement and add evidence
        for the control to the complete
        """
        if not self.is_applicable():
            return "not applicable"

        # TODO - do we want to change the status to the review_status
        # if there is an auditor in the project?
        # if self.project.has_auditor():
        #     return self.review_status

        if self.is_complete():
            return "complete"
        if self.implemented_progress():  # TODO > 0 or self.has_evidence():
            return "in progress"
        return "not started"

    def is_complete(self):
        if self.query_subcontrols(filter="uncomplete"):
            return False
        return True

    def is_applicable(self):
        if self.query_subcontrols():
            return True
        return False

    def progress(self, filter):
        count = self.query_subcontrols(filter=filter)
        if not count:
            return 0
        return round((len(count) / len(self.query_subcontrols())) * 100, 0)

    def completed_progress(self, subcontrols=None, default=0):
        total_progress = 0
        applicable_subcontrols = 0
        if not subcontrols:
            subcontrols = self.get_subcontrols()

        # If there are no applicable subcontrols, we will return 100% completion
        if not subcontrols:
            return default

        for subcontrol in subcontrols:
            if not subcontrol.is_applicable:
                continue
            applicable_subcontrols += 1
            total_progress += subcontrol.get_completion_progress()
        if not applicable_subcontrols:
            return default
        return round(total_progress / applicable_subcontrols, 0)

    def implemented_progress(self):
        total = 0
        subcontrols = self.query_subcontrols()
        if not subcontrols:
            return total
        for control in subcontrols:
            total += control.implemented or 0
        return round((total / len(subcontrols)), 0)

    def query_subcontrols(self, filter=None, only_applicable=True):
        """
        helper method to query sub controls
        by default, will return applicable controls only
        """
        subcontrols = []
        ProjectSubControl = current_app.models["ProjectSubControl"]
        _query = self.subcontrols
        if only_applicable:
            _query = _query.filter(ProjectSubControl.is_applicable == True)
        if filter == "not_applicable":
            _query = self.filter(ProjectSubControl.is_applicable == False)
        for subcontrol in _query.all():
            if filter == "not_implemented":
                if not subcontrol.is_implemented():
                    subcontrols.append(subcontrol)
            elif filter == "implemented":
                if subcontrol.is_implemented():
                    subcontrols.append(subcontrol)
            elif filter == "missing_evidence":
                if not subcontrol.has_evidence():
                    subcontrols.append(subcontrol)
            elif filter == "with_evidence":
                if subcontrol.has_evidence():
                    subcontrols.append(subcontrol)
            elif filter == "complete":
                if subcontrol.is_complete():
                    subcontrols.append(subcontrol)
            elif filter == "uncomplete":
                if not subcontrol.is_complete():
                    subcontrols.append(subcontrol)
            else:
                subcontrols.append(subcontrol)
        return subcontrols


class SubControlMixin(object):
    __table_args__ = {"extend_existing": True}
    """
    mixin model should only be attached to
    class ProjectSubControl
    """

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    def as_dict(self, include_evidence=False):
        User = current_app.models["User"]
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["implementation_status"] = self.implementation_status()
        data["completion_status"] = self.completion_description()
        data["progress_completed"] = self.get_completion_progress()
        data["is_complete"] = self.is_complete()
        data["framework"] = self.framework().name
        data["project"] = self.p_control.project.name
        data["parent_control"] = self.p_control.control.name
        data["name"] = self.subcontrol.name
        data["description"] = self.subcontrol.description
        data["mitigation"] = self.subcontrol.mitigation
        data["ref_code"] = self.subcontrol.ref_code
        data["guidance"] = self.subcontrol.guidance
        data["evidence"] = self.evidence.count()

        data["owner"] = (
            User.query.get(self.owner_id).email if self.owner_id else "Missing Owner"
        )
        data["operator"] = (
            User.query.get(self.operator_id).email
            if self.operator_id
            else "Missing Operator"
        )
        data["evidence"] = self.get_evidence(as_dict=True)
        data["has_evidence"] = False
        if data["evidence"]:
            data["has_evidence"] = True
        return data

    def get_evidence(self, as_dict=False):
        query = self.evidence.all()
        if as_dict:
            return [evidence.as_dict() for evidence in query]
        return query

    def get_completion_progress(self):
        if not self.is_applicable:
            return 0

        has_evidence = 100 if self.has_evidence() else 0

        # Base progress is the implementation percentage
        implemented_adjusted = self.implemented

        # If no evidence, reduce implemented progress by 25%
        if not self.has_evidence():
            implemented_adjusted *= 0.75

        # Ensure that having evidence alone contributes some progress
        return max(implemented_adjusted, has_evidence * 0.25)

    def completion_description(self):
        text = ""
        if not self.is_applicable:
            return "Control is not applicable."
        implemented_status = str(self.implementation_status())
        text += f"Control is {implemented_status}"
        if self.has_evidence():
            text += " and has evidence attached."
        else:
            text += " but is missing evidence."
        return text

    def framework(self):
        return self.p_control.control.framework

    def has_feature(self, name):
        """
        wrapper for Feature.has_feature
        """
        framework = self.framework()
        return framework.has_feature(name)

    def implementation_status(self):
        if not self.is_applicable:
            return "not applicable"
        if not self.implemented or self.implemented == 0:
            return "not implemented"
        if self.implemented == 100:
            return "fully implemented"
        return "partially implemented"

    def is_complete(self):
        if self.implemented != 100:
            return False
        if not self.has_evidence():
            return False
        return True

    def has_evidence(self, id=None):
        if not id:
            if self.evidence.first():
                return True
            return False
        return int(id) in [i.id for i in self.get_evidence()]

    def is_implemented(self):
        if self.implemented == 100:
            return True
        return False

    def remove_evidence(self):
        EvidenceAssociation = current_app.models["EvidenceAssociation"]
        EvidenceAssociation.query.filter(
            EvidenceAssociation.control_id == self.id
        ).delete()
        db.session.commit()
        return True

    def set_evidence(self, evidence_id_list):
        Evidence = current_app.models["ProjectEvidence"]
        self.remove_evidence()
        if not isinstance(evidence_id_list, list):
            evidence_id_list = [evidence_id_list]

        for id in evidence_id_list:
            if evidence := Evidence.query.get(id):
                self.evidence.append(evidence)
        db.session.commit()
        return True


class DateMixin(object):
    __table_args__ = {"extend_existing": True}

    def humanize_date(self, date):
        return arrow.get(date).humanize()

    def simple_date(self, date):
        return arrow.get(date).format("MM/DD/YYYY")


class QueryMixin(object):
    __table_args__ = {"extend_existing": True}

    @classmethod
    def get_or_404(cls, id):
        return cls.query.filter(cls.id == str(id)).first_or_404()

    @classmethod
    def find_by(cls, field, value, tenant_id=None, not_found=False):
        """
        Usage:
            User.find_by("email", "test@example.com")
        """
        _query = cls.query.filter(func.lower(getattr(cls, field)) == func.lower(value))
        if tenant_id:
            _query.filter(getattr(cls, "tenant_id") == tenant_id)

        if not_found:
            return _query.first_or_404()

        return _query.first()


class AuthorizerMixin(object):
    __table_args__ = {"extend_existing": True}

    """
    Define authorizer on fields in the SQLAlchemy models:
        # info={"authorizer": {"update": Authorizer.can_user_manage_platform}}
    
    Run Authorizer
        # tenant = Tenant.query.first()
        # user = User.query.first()
        # response = tenant.get_authorizer_decision(user=user, field="id", action="update")
        # print(response)        
    """

    def get_authorize_fields(self, field=None):
        data = {}
        for col in self.__table__.c:
            if not (authorize_data := col.info.get("authorizer")):
                continue
            data[col.key] = authorize_data
        if field:
            return data.get(field)
        return data

    def get_authorizer_decision(self, user, field, action):
        response = self.get_authorize_fields(field=field)

        # The field in the SQL model does not have an 'authorizer' annotation
        if not response:
            return {
                "ok": False,
                "message": f"Authorizer undefined for:{field}",
                "code": 401,
            }

        base_authorizer_action = response.get(action)

        # The field does not have the specific action defined
        if not base_authorizer_action:
            return {
                "ok": False,
                "message": f"Authorizer action:{action} undefined for:{field}",
                "code": 401,
            }

        base_authorizer = Authorizer(user)
        return partial(base_authorizer_action, base_authorizer)()
