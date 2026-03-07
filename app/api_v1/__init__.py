from flask import Blueprint, current_app, send_from_directory, abort

api = Blueprint("api", __name__)


@api.route("/swagger.json", methods=["GET"])
def swagger_spec():
	"""Dynamically generate a minimal OpenAPI 3.0 spec from the app's url_map.

	This inspects all rules under the /api/v1 prefix and creates a simple
	path/method listing with summaries extracted from view docstrings.
	"""
	prefix = "/api/v1"
	paths = {}

	for rule in current_app.url_map.iter_rules():
		# only include API v1 endpoints
		if not rule.rule.startswith(prefix):
			continue

		# skip static and swagger-ui assets
		if "static" in rule.endpoint or rule.rule.startswith("/static"):
			continue

		# normalized path for OpenAPI (strip prefix)
		path = rule.rule[len(prefix) :]
		if not path:
			path = "/"

		# initialize path entry
		paths.setdefault(path, {})

		methods = [m for m in rule.methods if m not in ("HEAD", "OPTIONS")]
		view_fn = current_app.view_functions.get(rule.endpoint)
		doc = (view_fn.__doc__ or "").strip() if view_fn else ""
		summary = doc.splitlines()[0].strip() if doc else ""

		for method in methods:
			# create a minimal operation object
			op = {"responses": {"200": {"description": "OK"}}}
			if summary:
				op["summary"] = summary
			else:
				op["summary"] = f"{method} {path}"

			# add parameters for path variables
			params = []
			for part in path.split("/"):
				if part.startswith("<") and part.endswith(">"):
					# convert Flask variable like <string:id> or <id>
					inner = part[1:-1]
					if ":" in inner:
						_type, name = inner.split(":", 1)
					else:
						name = inner
					params.append(
						{
							"name": name,
							"in": "path",
							"required": True,
							"schema": {"type": "string"},
						}
					)
			if params:
				op["parameters"] = params

			paths[path][method.lower()] = op

	spec = {
		"openapi": "3.0.0",
		"info": {"title": "Gapps API", "version": "1.0.0"},
		"servers": [{"url": prefix}],
		"components": {
			"securitySchemes": {
				"tokenAuth": {
					"type": "apiKey",
					"in": "header",
					"name": "token",
					"description": "Provide API token returned from /api/v1/token as header 'token: <TOKEN>'",
				}
			}
		},
		# Global security requirement; operations may still be public if desired
		"security": [{"tokenAuth": []}],
		"paths": paths,
	}
	return current_app.response_class(
		response=current_app.json.dumps(spec), status=200, mimetype="application/json"
	)

from . import base, views, vendors, integrations
