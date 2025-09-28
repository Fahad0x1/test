from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import requests

app = Flask(__name__)
app.secret_key = "CHANGE_THIS_TO_SOMETHING_SECURE"

# ------------ HELPER ------------
def get_headers():
    return {
        "Authorization": f"Bearer {session.get('ha_token')}",
        "Content-Type": "application/json",
    }

# ------------ LOGIN ------------
@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        ha_url = request.form["ha_url"].rstrip("/")
        ha_token = request.form["ha_token"]
        # اختبار التوكن على HA
        headers = {"Authorization": f"Bearer {ha_token}", "Content-Type": "application/json"}
        try:
            resp = requests.get(f"{ha_url}/api/states", headers=headers, timeout=5)
            if resp.status_code == 200:
                session["ha_url"] = ha_url
                session["ha_token"] = ha_token
                return redirect(url_for("dashboard"))
            else:
                error = "Invalid URL or Token"
        except:
            error = "Cannot connect to Home Assistant"
    return render_template("login.html", error=error)

# ------------ DASHBOARD ------------
@app.route("/dashboard")
def dashboard():
    if "ha_token" not in session:
        return redirect(url_for("login"))
    sections = ["Lights", "Curtains", "Doors", "ACs", "TV", "Cameras"]
    return render_template("dashboard.html", sections=sections)

# ------------ SECTION PAGE ------------
@app.route("/section/<section_name>")
def section(section_name):
    if "ha_token" not in session:
        return redirect(url_for("login"))

    ha_url = session["ha_url"]
    headers = get_headers()

    try:
        resp = requests.get(f"{ha_url}/api/states", headers=headers, timeout=5)
        entities = resp.json() if resp.status_code == 200 else []
    except:
        entities = []

    section_entities = []

    if section_name.lower() == "doors":
        section_entities = [e for e in entities if e["entity_id"].startswith("lock.") or e["entity_id"].startswith("door.")]
        # السكربتات الخاصة بالأبواب
        door_scripts = [
            {"entity_id": "script.cr02", "name": "Conference"},
            {"entity_id": "script.mr", "name": "meetingRoom small"},
            {"entity_id": "script.1708011050950", "name": "MainDoor"}
        ]
        for sc in door_scripts:
            sc["scripts"] = None
            section_entities.append(sc)
    else:
        prefix_map = {
            "lights": "light.",
            "curtains": "cover.",
            "acs": "climate.",
            "tv": "media_player.",
            "cameras": "camera."
        }
        prefix = prefix_map.get(section_name.lower(), "")
        section_entities = [e for e in entities if e["entity_id"].startswith(prefix)]

    return render_template("section.html", section_name=section_name, entities=section_entities)

# ------------ TOGGLE ENTITY ------------
@app.route("/toggle/<entity_id>")
def toggle(entity_id):
    ha_url = session["ha_url"]
    headers = get_headers()
    try:
        state_resp = requests.get(f"{ha_url}/api/states/{entity_id}", headers=headers)
        if state_resp.status_code != 200:
            return jsonify({"success": False})
        current_state = state_resp.json()["state"]
        service = "turn_off" if current_state in ["on", "open", "unlocked"] else "turn_on"
        svc_type = "light" if entity_id.startswith("light.") else "lock" if entity_id.startswith("lock.") else "cover" if entity_id.startswith("cover.") else "climate"
        requests.post(f"{ha_url}/api/services/{svc_type}/{service}", headers=headers, json={"entity_id": entity_id})
        return jsonify({"success": True})
    except:
        return jsonify({"success": False})

# ------------ RUN SCRIPT ------------
@app.route("/run_script/<script_id>", methods=["POST"])
def run_script(script_id):
    ha_url = session["ha_url"]
    headers = get_headers()
    try:
        resp = requests.post(f"{ha_url}/api/services/script/turn_on", headers=headers, json={"entity_id": script_id})
        return jsonify({"success": resp.status_code == 200})
    except:
        return jsonify({"success": False})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
