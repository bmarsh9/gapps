from flask import (
    jsonify,
    request,
    abort,
)
from . import api
from app import models, db
from flask_login import current_user
from app.utils.decorators import login_required
from app.utils.authorizer import Authorizer


@api.route("/forms/<string:id>", methods=["GET"])
@login_required
def get_form_for_edit_mode(id):
    result = Authorizer(current_user).can_user_manage_form(id)
    return jsonify(result["extra"]["form"].get_items(edit_mode=True))


@api.route("/forms/<string:qid>", methods=["DELETE"])
@login_required
def delete_form(qid):
    result = Authorizer(current_user).can_user_manage_form(qid)
    db.session.delete(result["extra"]["form"])
    db.session.commit()
    return jsonify({"message": "ok"})


@api.route("/forms/<string:qid>/sections", methods=["POST"])
@login_required
def form_create_section(qid):
    result = Authorizer(current_user).can_user_manage_form(qid)
    data = request.get_json()
    section = result["extra"]["form"].create_section(title=data["title"])
    return jsonify(section.as_dict())


@api.route("/forms/<string:id>/sections/<string:sid>", methods=["DELETE"])
@login_required
def form_delete_section(id, sid):
    result = Authorizer(current_user).can_user_manage_form(id)
    section = result["extra"]["form"].get_section_by_id(sid)
    db.session.delete(section)
    db.session.commit()
    return jsonify({"message": "ok"})


@api.route("/forms/<string:qid>/items", methods=["POST"])
@login_required
def form_create_item(qid):
    result = Authorizer(current_user).can_user_manage_form(qid)
    data = request.get_json()
    if not (section := result["extra"]["form"].get_section(data["section"])):
        abort(404)
    item = section.create_item(order=data["order"], data_type=data["data_type"])
    return jsonify(item.as_dict())


@api.route("/forms/<string:qid>/sections/<string:id>", methods=["PUT"])
@login_required
def form_update_section(qid, id):
    result = Authorizer(current_user).can_user_manage_form(qid)
    data = request.get_json()
    section = (
        result["extra"]["form"]
        .sections.filter(models.FormSection.id == id)
        .first_or_404()
    )
    section.update(title=data.get("title"))
    return jsonify({"message": "ok"})


@api.route("/forms/<string:qid>/items/<string:id>", methods=["PUT"])
@login_required
def form_update_item(qid, id):
    Authorizer(current_user).can_user_manage_form(qid)
    data = request.get_json()
    # TODO - update
    item = models.FormItem.get_or_404(id)
    item.update(
        section=data.get("section"),
        attributes=data.get("attributes", {}),
        disabled=data.get("disabled"),
        critical=data.get("critical"),
        score=data.get("score"),
    )
    return jsonify(item.as_dict())


@api.route("/forms/<string:qid>/items/<string:id>", methods=["DELETE"])
@login_required
def form_delete_item(qid, id):
    Authorizer(current_user).can_user_manage_form(qid)
    # TODO - update
    item = models.FormItem.query.get(id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "ok"})


@api.route("/forms/<string:qid>/sections/order", methods=["PUT"])
@login_required
def form_update_section_order(qid):
    result = Authorizer(current_user).can_user_manage_form(qid)
    data = request.get_json()
    form = result["extra"]["form"]
    sections = form.sections.all()
    for index, section_id in enumerate(data.get("order", [])):
        section = next((record for record in sections if record.id == section_id), None)
        section.order = index
    db.session.commit()
    return jsonify({"message": "ok"})


@api.route("/forms/<string:qid>/sections/<string:id>/order", methods=["PUT"])
@login_required
def form_update_items_order(qid, id):
    result = Authorizer(current_user).can_user_manage_form(qid)
    data = request.get_json()
    # TODO - update
    section = models.FormSection.query.get(id)
    section_items = section.items.all()
    for index, item_id in enumerate(data.get("order", [])):
        item = next((record for record in section_items if record.id == item_id), None)
        item.order = index
    db.session.commit()
    return jsonify({"message": "ok"})
