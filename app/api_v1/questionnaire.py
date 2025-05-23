from flask import (
    jsonify,
    request,
    abort,
    send_file,
)
from . import api
from app import models, db
from flask_login import current_user
from app.utils.authorizer import Authorizer
from app.utils.decorators import login_required
from app.utils.gcs_helper import GCS
from werkzeug.utils import secure_filename
from io import BytesIO


@api.route("/assessments/<string:id>/manage", methods=["GET"])
@login_required
def get_assessment_for_edit_mode(id):
    result = Authorizer(current_user).can_user_manage_assessment(id)
    return jsonify(result["extra"]["assessment"].get_items(edit_mode=True))


@api.route("/assessments/<string:id>/questions", methods=["GET"])
@login_required
def get_assessment_questions(id):
    result = Authorizer(current_user).can_user_read_assessment(id)
    return jsonify(result["extra"]["assessment"].get_items(edit_mode=False))


@api.route("/assessments/<string:qid>", methods=["DELETE"])
@login_required
def delete_assessment(qid):
    result = Authorizer(current_user).can_user_manage_assessment(qid)
    db.session.delete(result["extra"]["assessment"])
    db.session.commit()
    return jsonify({"message": "ok"})


@api.route("/assessments/<string:qid>/sections", methods=["POST"])
@login_required
def create_section(qid):
    result = Authorizer(current_user).can_user_manage_assessment(qid)
    data = request.get_json()
    section = result["extra"]["assessment"].create_section(title=data["title"])
    return jsonify(section.as_dict())


@api.route("/assessments/<string:qid>/items", methods=["POST"])
@login_required
def create_item(qid):
    result = Authorizer(current_user).can_user_manage_assessment(qid)
    data = request.get_json()
    if not (section := result["extra"]["assessment"].get_section(data["section"])):
        abort(404)
    item = section.create_item(order=data["order"], data_type=data["data_type"])
    return jsonify(item.as_dict())


@api.route("/assessments/<string:qid>/notes", methods=["PUT"])
@login_required
def update_assessment_notes(qid):
    result = Authorizer(current_user).can_user_manage_assessment(qid)
    data = request.get_json()
    result["extra"]["assessment"].notes = data.get("data")
    db.session.commit()
    return jsonify({"message": "ok"})


@api.route("/assessments/<string:qid>/sections/<string:id>", methods=["PUT"])
@login_required
def update_section(qid, id):
    result = Authorizer(current_user).can_user_manage_assessment(qid)
    data = request.get_json()
    section = (
        result["extra"]["assessment"]
        .sections.filter(models.FormSection.id == id)
        .first_or_404()
    )
    section.update(title=data.get("title"))
    return jsonify({"message": "ok"})


@api.route("/assessments/<string:qid>/items/<string:id>", methods=["PUT"])
@login_required
def update_item(qid, id):
    Authorizer(current_user).can_user_manage_assessment(qid)
    data = request.get_json()
    item = models.FormItem.get_or_404(id)
    item.update(
        section=data.get("section"),
        attributes=data.get("attributes", {}),
        disabled=data.get("disabled"),
        critical=data.get("critical"),
        score=data.get("score"),
    )
    return jsonify(item.as_dict())


@api.route("/assessments/<string:qid>/items/<string:id>", methods=["DELETE"])
@login_required
def delete_item(qid, id):
    Authorizer(current_user).can_user_manage_assessment(qid)
    item = models.FormItem.query.get(id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "ok"})


@api.route("/assessments/<string:qid>/sections/order", methods=["PUT"])
@login_required
def update_section_order(qid):
    result = Authorizer(current_user).can_user_manage_assessment(qid)

    data = request.get_json()
    assessment = result["extra"]["assessment"]
    sections = assessment.sections.all()
    for index, section_id in enumerate(data.get("order", [])):
        section = next((record for record in sections if record.id == section_id), None)
        section.order = index
    db.session.commit()
    return jsonify({"message": "ok"})


@api.route("/assessments/<string:qid>/sections/<string:id>/order", methods=["PUT"])
@login_required
def update_items_order(qid, id):
    result = Authorizer(current_user).can_user_manage_assessment(qid)

    data = request.get_json()
    section = models.FormSection.query.get(id)
    section_items = section.items.all()
    for index, item_id in enumerate(data.get("order", [])):
        item = next((record for record in section_items if record.id == item_id), None)
        item.order = index
    db.session.commit()
    return jsonify({"message": "ok"})


@api.route("/assessments/<string:qid>/items/<string:id>/response", methods=["PUT"])
@login_required
def update_item_response(qid, id):
    result = Authorizer(current_user).can_user_respond_to_assessment(qid)
    item = models.FormItem.get_or_404(id)
    assessment = result["extra"]["assessment"]
    if item.data_type == "file_input" and "file" in request.files:
        file = request.files["file"]
        filename = secure_filename(file.filename)
        assessment.vendor.create_file(filename, file, owner_id=current_user.id)
        item.response = filename
    else:
        data = request.get_json()
        item.response = data.get("response")
    db.session.commit()
    return jsonify(item.as_dict())


@api.route("/assessments/<string:qid>/items/<string:id>/response", methods=["DELETE"])
@login_required
def delete_item_response(qid, id):
    # TODO - check if user can delete parts of item
    Authorizer(current_user).can_user_respond_to_assessment(qid)
    item = models.FormItem.get_or_404(id)
    item.response = None
    db.session.commit()
    return jsonify(item.as_dict())


@api.route("/assessments/<string:qid>/items/<string:id>/file", methods=["GET"])
@login_required
def get_file_for_assessment_item(qid, id):
    result = Authorizer(current_user).can_user_manage_assessment(qid)
    item = models.FormItem.get_or_404(id)
    if item.data_type != "file_input":
        abort(422, "Item is not data_type: file_input")
    if not item.response:
        abort(422, "Item does not have a file")

    # TODO - update to file_handler.py
    gcs = GCS(root_path=result["extra"]["assessment"].tenant_id)
    blob = gcs.get_file(item.response)
    content_type = blob.content_type

    return send_file(
        BytesIO(blob.download_as_bytes()),
        download_name=item.response,
        mimetype=content_type,
        as_attachment=True,
    )


@api.route("/vendors/<string:id>/files", methods=["GET"])
@login_required
def get_files_for_vendor(id):
    # result = Authorizer(current_user).can_user_manage_tenant(id)
    # item = models.FormItem.get_or_404(id)
    vendor = models.Vendor.get_or_404(id)
    data = [file.as_dict() for file in vendor.files.all()]
    return jsonify(data)


@api.route("/vendors/<string:id>/files", methods=["POST"])
@login_required
def upload_file_for_vendor(id):
    # result = Authorizer(current_user).can_user_manage_tenant(id)
    # item = models.FormItem.get_or_404(id)
    vendor = models.Vendor.get_or_404(id)
    if "file" not in request.files:
        abort(422, "File not found")
    file = request.files["file"]
    filename = secure_filename(file.filename)
    vendor_file = vendor.create_file(filename, file)
    return jsonify(vendor_file.as_dict())


@api.route("/items/<string:id>/messages", methods=["POST"])
@login_required
def create_message_for_item(id):
    # result = Authorizer(current_user).can_user_manage_tenant(id)
    item = models.FormItem.get_or_404(id)
    data = request.get_json()
    message = item.create_message(text=data.get("text"), owner=current_user)
    return jsonify(message.as_dict())


@api.route("/items/<string:id>/messages/<string:mid>", methods=["DELETE"])
@login_required
def delete_message_for_item(id, mid):
    # result = Authorizer(current_user).can_user_manage_tenant(id)
    message = models.FormItemMessage.get_or_404(mid)
    db.session.delete(message)
    db.session.commit()
    return jsonify({"message": "ok"})


@api.route("/assessments/<string:id>", methods=["PUT"])
@login_required
def update_assessment(id):
    result = Authorizer(current_user).can_user_manage_assessment(id)
    data = request.get_json()
    assessment = result["extra"]["assessment"]
    for field in ["description", "due_before", "notes"]:
        if data.get(field):
            setattr(assessment, field, data.get(field))

    if data.get("guests"):
        assessment.set_guests(data.get("guests"), send_notification=True)

    if data.get("status") and data.get("status") != assessment.status:
        assessment.status = data.get("status")
        assessment.send_status_update_to_vendor(status=data.get("status"))

    db.session.commit()
    return jsonify(assessment.as_dict())


@api.route("/assessments/<string:id>/review-status", methods=["PUT"])
@login_required
def update_assessment_review_status(id):
    result = Authorizer(current_user).can_user_respond_to_assessment(id)
    data = request.get_json()
    if not data.get("status"):
        abort(422, "Missing required key: status")
    assessment = result["extra"]["assessment"]
    assessment.update_review_status(
        status=data.get("status"),
        send_notification=data.get("notification"),
        override=True,
    )
    return jsonify(assessment.as_dict())


@api.route("/assessments/<string:qid>/items/<string:id>/review-status", methods=["PUT"])
@login_required
def update_assessment_item_status(qid, id):
    result = Authorizer(current_user).can_user_manage_assessment(qid)
    data = request.get_json()
    item = models.FormItem.get_or_404(id)
    for field in [
        "review_status",
        "remediation_risk",
        "remediation_gap",
        "remediation_due_date",
        "remediation_plan_required",
        "complete_notes",
    ]:
        if data.get(field):
            setattr(item, field, data.get(field))
    db.session.commit()
    return jsonify(item.as_dict())


@api.route("/assessments/<string:qid>/items/<string:id>/remediation", methods=["PUT"])
@login_required
def update_remediation_plan(qid, id):
    result = Authorizer(current_user).can_user_manage_question(id)
    data = request.get_json()
    item = result["extra"]["question"]

    for key in [
        "remediation_plan_required",
        "remediation_vendor_agreed",
        "remediation_vendor_plan",
    ]:
        if key in data:
            setattr(item, key, data.get(key))
    db.session.commit()
    return jsonify(item.as_dict())


@api.route("/assessments/<string:id>/review-summary", methods=["GET"])
@login_required
def get_assessment_review_summary(id):
    result = Authorizer(current_user).can_user_read_assessment(id)
    assessment = result["extra"]["assessment"]
    return jsonify(assessment.get_grouping_for_question_review_status())
