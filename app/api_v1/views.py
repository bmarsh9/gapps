from flask import jsonify, request, current_app,abort
from . import api
from app import models, db
from flask_login import login_required,current_user
from app.utils.decorators import roles_required
from app.utils.jquery_filters import Filter
from app.utils.misc import project_creation
from sqlalchemy import func
import arrow

@api.route('/health', methods=['GET'])
def get_health():
    return jsonify({"message":"ok"})

@api.route('/projects/<int:id>', methods=['GET'])
@login_required
def project(id):
    project = models.Project.query.get(id)
    return jsonify(project.as_dict())

@api.route('/policies/<int:id>', methods=['GET'])
@login_required
def policy(id):
    policy = models.Policy.query.get(id)
    return jsonify(policy.as_dict())

@api.route('/policies/<int:id>', methods=['PUT'])
@roles_required("admin")
def update_policy(id):
    data = request.get_json()
    policy = models.Policy.query.get(id)
    policy.name = data["name"]
    policy.description = data["description"]
    policy.template = data["template"]
    policy.content = data["content"]
    db.session.commit()
    return jsonify(policy.as_dict())

@api.route('/frameworks/<int:id>', methods=['GET'])
@login_required
def get_framework(id):
    framework = models.Framework.query.get(id)
    return jsonify(framework.as_dict())

@api.route('/frameworks', methods=['POST'])
@roles_required("admin")
def add_framework():
    payload = request.get_json()
    framework = models.Framework(name=payload["name"],
        description=payload.get("description"),
        reference_link=payload.get("link"))
    db.session.add(framework)
    db.session.commit()
    return jsonify(framework.as_dict())

@api.route('/evidence', methods=['POST'])
@roles_required("admin")
def add_evidence():
    payload = request.get_json()
    evidence = models.Evidence(name=payload["name"],
        description=payload["description"],content=payload["content"])
    db.session.add(evidence)
    db.session.commit()
    return jsonify(evidence.as_dict())

@api.route('/evidence/<int:id>/controls', methods=['PUT'])
@roles_required("admin")
def add_evidence_to_controls(id):
    payload = request.get_json()
    evidence = models.Evidence.query.get(id)
    evidence.associate_with_controls(payload)
    return jsonify({"message":"ok"})

@api.route('/policies', methods=['POST'])
@roles_required("admin")
def add_policy():
    payload = request.get_json()
    policy = models.Policy(name=payload["name"],
        description=payload["description"])
    db.session.add(policy)
    db.session.commit()
    return jsonify(policy.as_dict())

@api.route('/policies/<int:id>', methods=['DELETE'])
@roles_required("admin")
def delete_policy(id):
    policy = models.Policy.query.get(id)
    policy.visible = False
    db.session.commit()
    return jsonify({"message":"ok"})

@api.route('/controls/<int:id>', methods=['DELETE'])
@roles_required("admin")
def delete_control(id):
    control = models.Control.query.get(id)
    control.visible = False
    db.session.commit()
    return jsonify({"message":"ok"})

@api.route('/controls', methods=['POST'])
@roles_required("admin")
def create_control():
    payload = request.get_json()
    control = models.Control.create(payload),
    return jsonify({"message":"ok"})

@api.route('/controls/<int:id>', methods=['GET'])
@login_required
def control(id):
    control = models.Control.query.get(id)
    return jsonify(control.as_dict())

@api.route('/projects', methods=['POST'])
@roles_required("admin")
def create_project():
    payload = request.get_json()
    result = project_creation(payload, current_user)
    if not result:
        return jsonify({"message":"failed to create project"}),400
    return jsonify({"message":"project created"})

@api.route('/projects/subcontrols', methods=['GET'])
@login_required
def get_subcontrols_in_projects():
    data = []
    for subcontrol in models.ProjectSubControl.query.all():
        data.append(subcontrol.as_dict(include_evidence=True))
    return jsonify(data)
#haaaaa
@api.route('/projects/<int:id>/controls', methods=['GET'])
@login_required
def get_controls_for_project(id):
    data = []
    project = models.Project.query.get(id)
    for control in project.controls.all():
        for subcontrol in control.subcontrols.all():
            data.append(subcontrol.as_dict(include_evidence=True))
    return jsonify(data)

@api.route('/projects/<int:id>/policies/<int:pid>', methods=['GET'])
@login_required
def get_policy_for_project(id, pid):
    policy = models.ProjectPolicy.query.get(pid)
    return jsonify(policy.as_dict())

@api.route('/projects/<int:id>/policies/<int:pid>', methods=['PUT'])
@roles_required("admin")
def update_policy_for_project(id, pid):
    data = request.get_json()
    policy = models.ProjectPolicy.query.get(pid)
    policy.name = data["name"]
    policy.description = data["description"]
    policy.template = data["template"]
    policy.content = data["content"]
    policy.public_viewable = data["public"]
    db.session.commit()
    return jsonify(policy.as_dict())

@api.route('/projects/<int:id>/policies/<int:pid>', methods=['DELETE'])
@roles_required("admin")
def delete_policy_for_project(id, pid):
    project = models.Project.query.get(id)
    project.delete_policy(pid)
    return jsonify({"message":"policy removed"})

@api.route('/policies/<int:id>/controls/<int:cid>', methods=['PUT'])
@roles_required("admin")
def update_controls_for_policy(id, cid):
    policy = models.Policy.query.get(id)
    policy.add_control(cid)
    return jsonify({"message":"ok"})

@api.route('/policies/<int:id>/controls/<int:cid>', methods=['DELETE'])
@roles_required("admin")
def delete_controls_for_policy(id, cid):
    policy = models.Policy.query.get(id)
    if control := policy.has_control(cid):
        db.session.delete(control)
        db.session.commit()
    return jsonify({"message":"ok"})

@api.route('/projects/<int:id>/policies/<int:pid>/controls/<int:cid>', methods=['PUT'])
@roles_required("admin")
def update_policy_controls_for_project(id, pid, cid):
    policy = models.ProjectPolicy.query.get(pid)
    policy.add_control(cid)
    return jsonify({"message":"ok"})

@api.route('/projects/<int:id>/policies/<int:pid>/controls/<int:cid>', methods=['DELETE'])
@roles_required("admin")
def delete_policy_controls_for_project(id, pid, cid):
    policy = models.ProjectPolicy.query.get(pid)
    if control := policy.has_control(cid):
        db.session.delete(control)
        db.session.commit()
    return jsonify({"message":"ok"})

@api.route('/projects/<int:id>/controls/<int:cid>', methods=['GET'])
@login_required
def get_control_for_project(id, cid):
    control = models.ProjectControl.query.get(cid)
    return jsonify(control.as_dict(with_areas=True))

@api.route('/policies/<int:pid>/projects/<int:id>', methods=['PUT'])
@roles_required("admin")
def add_policy_to_project(pid, id):
    policy = models.Policy.query.get(pid)
    project = models.Project.query.get(id)
    project.add_policy(policy)
    return jsonify(policy.as_dict())

@api.route('/controls/<int:cid>/projects/<int:id>', methods=['PUT'])
@roles_required("admin")
def add_control_to_project(cid, id):
    control = models.Control.query.get(cid)
    project = models.Project.query.get(id)
    project.add_control(control)
    return jsonify(control.as_dict())

@api.route('/query/controls', methods=['GET','POST'])
@login_required
def query_controls():
    """
    return query results for dt table
    """
    payload = request.get_json()
    include_cols = request.args.get("columns", "no")
    _filter = Filter(models, current_app.db.session.query(),tables=["controls"])
    data = _filter.handle_request(
        payload,
        default_filter={"condition":"OR","rules":[{"field":"controls.id","operator":"is_not_null"}]},
        default_fields=["id", "criteria", "control_ref"]
    )
    if include_cols == "no":
        data.pop("columns", None)
    return jsonify(data)

@api.route('/query/focus-areas', methods=['GET','POST'])
@login_required
def focus_areas():
    """
    return query results for dt table
    """
    payload = request.get_json()
    include_cols = request.args.get("columns", "no")
    _filter = Filter(models, current_app.db.session.query(),tables=["control_focus_areas"])
    data = _filter.handle_request(
        payload,
        default_filter={"condition":"OR","rules":[{"field":"control_focus_areas.id","operator":"is_not_null"}]},
        default_fields=["id", "criteria", "control_ref"]
    )
    if include_cols == "no":
        data.pop("columns", None)
    return jsonify(data)

@api.route('/controls/<int:cid>/focus-areas/<int:fid>', methods=['PUT'])
@roles_required("admin")
def update_focus_area_in_control(cid, fid):
    payload = request.get_json()
    focus = models.ProjectControlFocusArea.query.get(fid)
    focus.status = payload["status"]
    focus.evidence = payload["evidence"]
    focus.notes = payload["notes"]
    focus.feedback = payload["feedback"]
    db.session.commit()
    return jsonify({"message":"ok"})

@api.route('/controls/<int:cid>/applicability', methods=['PUT'])
@roles_required("admin")
def set_applicability_of_control(cid):
    payload = request.get_json()
    control = models.ProjectControl.query.get(cid)
    control.set_applicability(payload["applicable"])
    return jsonify({"message":"ok"})

@api.route('/tags/<int:id>', methods=['DELETE'])
@roles_required("admin")
def delete_tag(id):
    tag = models.Tag.query.get(id)
    if not tag:
        return jsonify({"message": "not found"}), 404
    db.session.delete(tag)
    db.session.commit()
    return jsonify({"message": "ok"})

@api.route('/labels/<int:id>', methods=['DELETE'])
@roles_required("admin")
def delete_label(id):
    label = models.PolicyLabel.query.get(id)
    if not label:
        return jsonify({"message": "not found"}), 404
    db.session.delete(label)
    db.session.commit()
    return jsonify({"message": "ok"})

@api.route('/charts/project-summaries', methods=['GET'])
@login_required
def charts_get_project_summaries():
    data = {
        "categories":[],
        "controls":[],
        "policies":[],
        "complete":[],
        "not_implemented":[],
        "missing_evidence":[],
    }
    for project in models.Project.query.order_by(models.Project.id.desc()).limit(5).all():
        data["categories"].append(project.name)
        data["controls"].append(project.controls.count())
        data["policies"].append(project.policies.count())
        data["complete"].append(len(project.query_fa("complete")))
        data["not_implemented"].append(len(project.query_fa("not_implemented")))
        data["missing_evidence"].append(len(project.query_fa("missing_evidence")))
    return jsonify(data)

@api.route('/charts/tenant-summary', methods=['GET'])
@login_required
def charts_get_tenant_summary():
    data = {
        "categories":["Projects","Controls","Policies","Focus Areas", "Users"],
        "data":[]
    }
    data["data"].append(models.Project.query.count())
    data["data"].append(models.Control.query.count())
    data["data"].append(models.Policy.query.count())
    data["data"].append(models.ControlListFocusArea.query.count())
    data["data"].append(models.User.query.count())
    return jsonify(data)

@api.route('/charts/controls-by-framework', methods=['GET'])
@login_required
def charts_get_controls_by_framework():
    data = {
        "categories":[],
        "data":[]
    }
    for control in models.Framework.query.with_entities(models.Framework.name,func.count(models.Framework.name)).group_by(models.Framework.name).all():
        data["categories"].append(control[0])
        data["data"].append(control[1])
    return jsonify(data)

@api.route('/charts/controls-by-category', methods=['GET'])
@login_required
def charts_get_control_by_category():
    data = {
        "categories":[],
        "data":[]
    }
    for control in models.Control.query.with_entities(models.Control.category,func.count(models.Control.category)).group_by(models.Control.category).all():
        data["categories"].append(control[0])
        data["data"].append(control[1])
    return jsonify(data)

@api.route('/charts/controls-by-subcategory', methods=['GET'])
@login_required
def charts_get_control_by_subcategory():
    data = {
        "categories":[],
        "data":[]
    }
    for control in models.Control.query.with_entities(models.Control.subcategory,func.count(models.Control.subcategory)).group_by(models.Control.subcategory).all():
        data["categories"].append(control[0])
        data["data"].append(control[1])
    return jsonify(data)
