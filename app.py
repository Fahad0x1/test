from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import requests

app = Flask(__name__)
app.secret_key = "CHANGE_THIS_TO_SOMETHING_SECURE"

# أقسام النظام ومطابقتها مع entity_id prefix
SECTIONS = {
    "Lights": "light.",
    "Curtains": "cover.",
    "Doors":  "script.",  # سكربتات الأبواب
    "ACs": "climate.",
    "TV": "media_player.",
    "Cameras": "camera."
}

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        ha_url = request.form["ha_url"]
        ha_token = request.form["ha_token"]
        session["ha_url"] = ha_url
        session["ha_token"] = ha_token
        # تحقق من صحة التوكن فورًا
        try:
            resp = requests.get(f"{ha_url}/api/states", headers={"Authorization": f"Bearer {ha_token}"})
            if resp.status_code != 200:
                return render_template("login.html", error="URL أو التوكن غير صحيح")
        except:
            return render_template("login.html", error="تعذر الاتصال بالهوم أسيستانت")
        return redirect(url_for("dashboard"))
    return render_template("login.html", error=None)

def get_headers():
    return {
        "Authorization": f"Bearer {session.get('ha_token')}",
        "Content-Type": "application/json",
    }

def get_entities_by_prefix(prefix):
    ha_url = session["ha_url"]
    headers = get_headers()
    try:
        resp = requests.get(f"{ha_url}/api/states", headers=headers)
        entities = resp.json() if resp.status_code == 200 else []
    except:
        entities = []

    data = []
    for entity in entities:
        if entity["entity_id"].startswith(prefix):
            data.append({
                "name": entity["attributes"].get("friendly_name", entity["entity_id"]),
                "entity_id": entity["entity_id"],
                "state": entity["state"]
            })
    return data

@app.route("/dashboard")
def dashboard():
    if "ha_token" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", sections=SECTIONS.keys())

@app.route("/section/<section_name>")
def section(section_name):
    if "ha_token" not in session:
        return redirect(url_for("login"))
    prefix = SECTIONS.get(section_name)
    if not prefix:
        return f"Section {section_name} not found"
    entities = get_entities_by_prefix(prefix)
    return render_template("section.html", section_name=section_name, entities=entities)

@app.route("/toggle/<entity_id>")
def toggle(entity_id):
    ha_url = session["ha_url"]
    headers = get_headers()
    try:
        resp = requests.get(f"{ha_url}/api/states/{entity_id}", headers=headers)
        if resp.status_code == 200:
            current_state = resp.json()["state"] in ["on","open","unlocked"]
            if entity_id.startswith("light."):
                service = "turn_off" if current_state else "turn_on"
                requests.post(f"{ha_url}/api/services/light/{service}", headers=headers, json={"entity_id": entity_id})
            elif entity_id.startswith("cover."):
                service = "close_cover" if current_state else "open_cover"
                requests.post(f"{ha_url}/api/services/cover/{service}", headers=headers, json={"entity_id": entity_id})
            elif entity_id.startswith("lock.") or entity_id.startswith("script."):
                service = "lock" if current_state else "unlock"
                requests.post(f"{ha_url}/api/services/lock/{service}", headers=headers, json={"entity_id": entity_id})
            elif entity_id.startswith("climate."):
                service = "turn_off" if current_state else "turn_on"
                requests.post(f"{ha_url}/api/services/climate/{service}", headers=headers, json={"entity_id": entity_id})
            elif entity_id.startswith("media_player."):
                service = "turn_off" if current_state else "turn_on"
                requests.post(f"{ha_url}/api/services/media_player/{service}", headers=headers, json={"entity_id": entity_id})
    except:
        pass
    return jsonify({"success": True})

@app.route("/entities_status/<section_name>")
def entities_status(section_name):
    prefix = SECTIONS.get(section_name)
    if not prefix:
        return jsonify([])
    return jsonify(get_entities_by_prefix(prefix))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
