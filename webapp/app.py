import json
import os
import sys

from flask import Flask, jsonify, render_template, request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from toonlib import compare, dumps, loads  # noqa: E402

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/to-toon", methods=["POST"])
def to_toon():
    body = request.get_json(silent=True) or {}
    text = body.get("input", "")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Invalid JSON: {e}"}), 400
    try:
        toon_text = dumps(data)
        json_minified = json.dumps(data, separators=(",", ":"))
        return jsonify({"output": toon_text, "stats": compare(json_minified, toon_text)})
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"Conversion failed: {e}"}), 400


@app.route("/api/to-json", methods=["POST"])
def to_json_route():
    body = request.get_json(silent=True) or {}
    text = body.get("input", "")
    try:
        data = loads(text)
        json_text = json.dumps(data, indent=2)
        json_minified = json.dumps(data, separators=(",", ":"))
        return jsonify({"output": json_text, "stats": compare(json_minified, text)})
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"Conversion failed: {e}"}), 400


# --- Raw-body endpoints, meant for direct testing (Postman, curl, etc). ---
# Unlike the /api/to-toon and /api/to-json routes above (used by the web UI,
# which always sends a string under an "input" key since a textarea's
# contents are always a string), these take the JSON/TOON payload as the
# request body itself, since that's what a tool like Postman naturally does.

@app.route("/api/convert/to-toon", methods=["POST"])
def convert_to_toon():
    try:
        data = json.loads(request.get_data(as_text=True))
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Invalid JSON: {e}"}), 400
    try:
        toon_text = dumps(data)
        json_minified = json.dumps(data, separators=(",", ":"))
        return jsonify({"output": toon_text, "stats": compare(json_minified, toon_text)})
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"Conversion failed: {e}"}), 400


@app.route("/api/convert/to-json", methods=["POST"])
def convert_to_json():
    text = request.get_data(as_text=True)
    try:
        data = loads(text)
        json_minified = json.dumps(data, separators=(",", ":"))
        return jsonify({"output": data, "stats": compare(json_minified, text)})
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"Conversion failed: {e}"}), 400


if __name__ == "__main__":
    app.run(debug=True, port=5050)
