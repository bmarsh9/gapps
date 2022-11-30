from app import db
from flask import current_app
from sqlalchemy.ext.declarative import declared_attr
from app.utils.misc import get_class_by_tablename
import arrow

class ControlMixin(object):
    __table_args__ = {'extend_existing': True}
    """
    mixin model should only be attached to
    class ProjectControl
    """
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    def as_dict(self, include_subcontrols=False):
        parent_fields = ["name","ref_code","system_level",
            "category","subcategory","dtc","dti"]
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for field in parent_fields:
            data[field] = getattr(self.control, field)
        data["status"] = self.status()
        data["progress"] = self.progress("implemented")
        data["is_complete"] = self.is_complete()
        data["is_applicable"] = self.is_applicable()
        if include_subcontrols:
            data["subcontrols"] = [x.as_dict() for x in self.query_subcontrols(only_applicable=False)]
        return data

    def framework(self):
        return self.control.framework

    def set_applicability(self, applicable):
        for control in self.subcontrols.all():
            control.is_applicable = applicable
        db.session.commit()
        return True

    def status(self):
        if not self.is_applicable():
            return "not applicable"
        if self.is_complete():
            return "complete"
        if self.implemented_progress() > 0:
            return "in progress"
        return "not started"

    def get_color_from_int(self, number, alternate=False):
        if number >= 90:
            return "success" if alternate else "green"
        if number >= 75:
            return "warning" if alternate else "orange"
        if number >= 25:
            return "warning" if alternate else "yellow"
        return "error" if alternate else "red"

    def status_color(self):
        color = {
            "not applicable":"slate",
            "complete":"green",
            "in progress":"orange",
            "not started":"gray"
        }
        status = self.status()
        return color.get(status,"slate")

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
        return round((len(count) / len(self.query_subcontrols()))*100,2)

    def implemented_progress(self):
        total = 0
        subcontrols = self.query_subcontrols()
        if not subcontrols:
            return total
        for control in subcontrols:
            total += control.implemented
        return round((total/len(subcontrols)),2)

    def query_subcontrols(self, filter=None, only_applicable=True):
        """
        helper method to query sub controls
        by default, will return applicable controls only
        """
        subcontrols = []
        ProjectSubControl = get_class_by_tablename("ProjectSubControl")
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
    __table_args__ = {'extend_existing': True}
    """
    mixin model should only be attached to
    class ProjectSubControl
    """
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    def as_dict(self, include_evidence=False):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["implementation_status"] = self.implementation_status()
        data["has_evidence"] = self.has_evidence()
        data["is_complete"] = self.is_complete()
        data["framework"] = self.framework().name
        data["project"] = self.p_control.project.name
        data["parent_control"] = self.p_control.control.name
        data["name"] = self.subcontrol.name
        data["ref_code"] = self.subcontrol.ref_code
        if include_evidence:
            data["evidence"] = [x.as_dict() for x in self.evidence.all()]
        return data

    def framework(self):
        return self.p_control.control.framework

    def has_feature(self, name):
        """
        wrapper for Feature.has_feature
        """
        framework = self.framework()
        return framework.has_feature(name)

    def get_color_from_int(self, number, alternate=False):
        if number >= 90:
            return "success" if alternate else "green"
        if number >= 75:
            return "warning" if alternate else "orange"
        if number >= 25:
            return "warning" if alternate else "yellow"
        return "error" if alternate else "red"

    def status_color(self):
        color = {
            "not applicable":"slate",
            "not implemented":"gray",
            "fully implemented":"green",
            "mostly implemented":"orange",
            "partially implemented":"yellow"
        }
        status = self.implementation_status()
        return color.get(status,"slate")

    def implementation_status(self):
        if not self.is_applicable:
            return "not applicable"
        if self.implemented == 100:
            return "fully implemented"
        if self.implemented == 0:
            return "not implemented"
        if self.implemented >= 50:
            return "mostly implemented"
        return "partially implemented"

    def is_complete(self):
        framework = self.framework()
        """
        every framework will require that the control
        is 100% implemented
        """
        if self.implemented != 100:
            return False

        """
        if the framework requires evidence collection,
        we will check if the control has evidence attached
        """
        if self.has_feature("feature_evidence"):
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

    def get_evidence(self):
        return self.evidence.all()

    def remove_evidence(self):
        EvidenceAssociation = get_class_by_tablename("EvidenceAssociation")
        EvidenceAssociation.query.filter(EvidenceAssociation.control_id == self.id).delete()
        db.session.commit()
        return True

    def set_evidence(self, evidence_id_list):
        Evidence = get_class_by_tablename("Evidence")
        self.remove_evidence()
        if not isinstance(evidence_id_list, list):
            evidence_id_list = [evidence_id_list]
        for id in evidence_id_list:
            if evidence := Evidence.query.get(id):
                self.evidence.append(evidence)
        db.session.commit()
        return True

class LogMixin(object):
    __table_args__ = {'extend_existing': True}

    def add_log(self,message,log_type="info",meta={},namespace=None):
        logTable = current_app.models["logs"]
        if not namespace:
            namespace = self.__table__.name
        return logTable().add_log(namespace=namespace,message=message,
            log_type=log_type.lower(),meta=meta)

    def get_logs(self,log_type=None,
        limit=100,as_query=False,span=None,as_count=False,
        paginate=False,page=1,meta={},namespace=None):
        logTable = current_app.models["logs"]
        if not namespace:
            namespace = self.__table__.name
        return logTable().get_logs(log_type=log_type,namespace=namespace,
            limit=limit,as_query=as_query,span=span,as_count=as_count,
            paginate=paginate,page=page,meta=meta)

class DateMixin(object):
    __table_args__ = {'extend_existing': True}

    def humanize_date(self,date):
        return arrow.get(date).humanize()
