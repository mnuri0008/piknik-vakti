
import os, json, threading
from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv

load_dotenv()

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'picnic_data.json')
_lock = threading.Lock()

def read_data():
    if not os.path.exists(DATA_PATH):
        return {"users": [], "items": [], "seq": 1, "categories": ["Yiyecek","İçecek","Baharat","Tatlı","Araç-gereç"]}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def write_data(d):
    tmp = DATA_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_PATH)

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')
    app.config['MAX_USERS'] = int(os.getenv('MAX_USERS', '10'))
    return app

app = create_app()
socketio = SocketIO(app, cors_allowed_origins="*")

# ---- Helpers ----
def broadcast_state():
    with _lock:
        data = read_data()
    socketio.emit("state", data)

# ---- Routes ----
@app.get('/')
def home():
    return render_template('index.html')

@app.get('/api/items')
def api_items():
    with _lock:
        data = read_data()
    return jsonify(items=data["items"])

@app.get('/api/categories')
def api_categories():
    with _lock:
        data = read_data()
    return jsonify(categories=data.get("categories", []))

@app.post('/api/items')
def api_add_item():
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    category = (body.get("category") or "Diğer").strip()
    unit = (body.get("unit") or "kg").strip()
    who = (body.get("who") or "").strip()
    try:
        amount = float(body.get("amount", 0) or 0)
    except Exception:
        return jsonify(error="bad_amount"), 400
    if not title:
        return jsonify(error="title_required"), 400
    with _lock:
        data = read_data()
        iid = data["seq"]; data["seq"] += 1
        item = {"id": iid, "title": title, "category": category, "amount": amount, "unit": unit, "who": who, "status": "needed"}
        data["items"].append(item)
        write_data(data)
    broadcast_state()
    return jsonify(item), 201

@app.patch('/api/items/<int:iid>')
def api_patch_item(iid: int):
    body = request.get_json(silent=True) or {}
    allowed = {"needed","claimed","brought"}
    patch = {}
    if "title" in body: patch["title"] = (body["title"] or "").strip()
    if "category" in body: patch["category"] = (body["category"] or "").strip()
    if "unit" in body: patch["unit"] = (body["unit"] or "").strip()
    if "who" in body: patch["who"] = (body["who"] or "").strip()
    if "amount" in body:
        try: patch["amount"] = float(body["amount"])
        except Exception: return jsonify(error="bad_amount"), 400
    if "status" in body:
        st = (body["status"] or "").strip()
        if st not in allowed: return jsonify(error="bad_status", allowed=list(allowed)), 400
        patch["status"] = st
    with _lock:
        data = read_data()
        found = None
        for it in data["items"]:
            if it["id"] == iid:
                it.update({k:v for k,v in patch.items() if v is not None})
                found = it; break
        if not found: return jsonify(error="not_found"), 404
        write_data(data)
    broadcast_state()
    return jsonify(found)

@app.delete('/api/items/<int:iid>')
def api_delete_item(iid: int):
    with _lock:
        data = read_data()
        n = len(data["items"])
        data["items"] = [x for x in data["items"] if x["id"] != iid]
        if len(data["items"]) == n:
            return jsonify(error="not_found"), 404
        write_data(data)
    broadcast_state()
    return ("", 204)

@app.get('/api/users')
def api_users():
    with _lock:
        data = read_data()
    return jsonify(users=data["users"], max=app.config['MAX_USERS'])

@app.post('/api/users')
def api_add_user():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    if not name: return jsonify(error="name_required"), 400
    with _lock:
        data = read_data()
        users = set(data["users"])
        if name not in users:
            if len(users) >= app.config['MAX_USERS']:
                return jsonify(error="room_full"), 403
            users.add(name)
            data["users"] = sorted(users)
            write_data(data)
    socketio.emit("presence", {"event":"join", "name": name})
    broadcast_state()
    return jsonify(ok=True)

# ---- SocketIO ----
@socketio.on('connect')
def on_connect():
    emit("hello", {"msg": "connected"})

@socketio.on('join')
def on_join(data):
    name = (data.get("name") or "").strip()
    if not name: return
    with _lock:
        store = read_data()
        users = set(store["users"])
        if name not in users:
            if len(users) >= app.config['MAX_USERS']:
                emit("error", {"error":"room_full"})
                return
            users.add(name)
            store["users"] = sorted(users)
            write_data(store)
    emit("presence", {"event":"join", "name": name}, broadcast=True)
    broadcast_state()

@socketio.on('leave')
def on_leave(data):
    name = (data.get("name") or "").strip()
    with _lock:
        store = read_data()
        if name in store["users"]:
            store["users"] = [u for u in store["users"] if u != name]
            write_data(store)
    emit("presence", {"event":"leave", "name": name}, broadcast=True)
    broadcast_state()

# Expose for gunicorn
# Note: gunicorn -k eventlet -w 1 app.server:app
