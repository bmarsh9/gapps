"""
MCP (Model Context Protocol) Server for the Masri Digital Compliance Platform.

Provides structured tool access for LLM integrations to query compliance data,
frameworks, controls, and policies.

Run standalone: python mcp_server.py
Or integrate with the main Flask application.
"""

import json
import os
import sys
from flask import Flask, jsonify, request

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def create_mcp_app():
    """Create a minimal Flask MCP server."""
    mcp_app = Flask(__name__)
    mcp_app.config["SECRET_KEY"] = os.environ.get("MCP_SERVER_TOKEN", "mcp-secret")

    @mcp_app.route("/mcp/v1/tools/list", methods=["POST"])
    def list_tools():
        """List available MCP tools."""
        tools = [
            {
                "name": "list_frameworks",
                "description": "List all available compliance frameworks (SOC2, HIPAA, FTC Safeguards, NIST, etc.)",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "get_framework_controls",
                "description": "Get all controls for a specific compliance framework",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "framework": {
                            "type": "string",
                            "description": "Framework name (e.g., 'ftc_safeguards', 'soc2', 'hipaa_v2')",
                        }
                    },
                    "required": ["framework"],
                },
            },
            {
                "name": "search_controls",
                "description": "Search controls across frameworks by keyword",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search keyword (e.g., 'encryption', 'access control', 'risk assessment')",
                        },
                        "framework": {
                            "type": "string",
                            "description": "Optional: limit search to a specific framework",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "get_industry_controls",
                "description": "Get FTC Safeguards controls for a specific industry",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "industry": {
                            "type": "string",
                            "description": "Industry type (e.g., 'mortgage_lenders', 'cpas', 'tax_preparers', 'auto_dealers')",
                        }
                    },
                    "required": ["industry"],
                },
            },
        ]
        return jsonify({"tools": tools})

    @mcp_app.route("/mcp/v1/tools/call", methods=["POST"])
    def call_tool():
        """Execute an MCP tool."""
        data = request.get_json()
        tool_name = data.get("name")
        arguments = data.get("arguments", {})

        framework_folder = os.environ.get(
            "FRAMEWORK_FOLDER",
            os.path.join(os.path.dirname(__file__), "app/files/base_controls"),
        )

        if tool_name == "list_frameworks":
            frameworks = []
            for f in os.listdir(framework_folder):
                if f.endswith(".json"):
                    name = f.replace(".json", "")
                    frameworks.append(name)
            return jsonify({"content": [{"type": "text", "text": json.dumps(frameworks)}]})

        elif tool_name == "get_framework_controls":
            fw_name = arguments.get("framework", "").lower()
            fw_path = os.path.join(framework_folder, f"{fw_name}.json")
            if not os.path.exists(fw_path):
                return jsonify({"content": [{"type": "text", "text": f"Framework '{fw_name}' not found"}]})
            with open(fw_path) as f:
                controls = json.load(f)
            summary = []
            for c in controls:
                summary.append({
                    "ref_code": c.get("ref_code"),
                    "name": c.get("name"),
                    "category": c.get("category"),
                    "subcontrol_count": len(c.get("subcontrols", [])),
                })
            return jsonify({"content": [{"type": "text", "text": json.dumps(summary, indent=2)}]})

        elif tool_name == "search_controls":
            query = arguments.get("query", "").lower()
            fw_filter = arguments.get("framework", "").lower()
            results = []

            for f in os.listdir(framework_folder):
                if not f.endswith(".json"):
                    continue
                fw_name = f.replace(".json", "")
                if fw_filter and fw_name != fw_filter:
                    continue
                with open(os.path.join(framework_folder, f)) as fp:
                    controls = json.load(fp)
                for c in controls:
                    text = f"{c.get('name', '')} {c.get('description', '')} {c.get('guidance', '')}".lower()
                    if query in text:
                        results.append({
                            "framework": fw_name,
                            "ref_code": c.get("ref_code"),
                            "name": c.get("name"),
                            "description": c.get("description", "")[:200],
                        })
            return jsonify({"content": [{"type": "text", "text": json.dumps(results[:20], indent=2)}]})

        elif tool_name == "get_industry_controls":
            industry = arguments.get("industry", "").lower()
            fw_path = os.path.join(framework_folder, "ftc_safeguards.json")
            if not os.path.exists(fw_path):
                return jsonify({"content": [{"type": "text", "text": "FTC Safeguards framework not found"}]})
            with open(fw_path) as f:
                controls = json.load(f)
            results = []
            for c in controls:
                meta = c.get("meta", {})
                industries = meta.get("industries", [])
                if not industries or industry in industries:
                    results.append({
                        "ref_code": c.get("ref_code"),
                        "name": c.get("name"),
                        "category": c.get("category"),
                        "industry_specific": bool(industries),
                    })
            return jsonify({"content": [{"type": "text", "text": json.dumps(results, indent=2)}]})

        return jsonify({"error": f"Unknown tool: {tool_name}"})

    @mcp_app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "server": "mcp"})

    return mcp_app


if __name__ == "__main__":
    app = create_mcp_app()
    port = int(os.environ.get("MCP_PORT", 3001))
    app.run(host="0.0.0.0", port=port, debug=True)
