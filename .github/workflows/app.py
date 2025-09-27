import json
import os
from datetime import datetime
from functools import wraps
from flask import Flask, request, redirect, session, url_for, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash

# -------- Config --------
APP_SECRET = "ersetze_das_mit_einem_starken_secret"
DATA_USERS = "users.json"
DATA_DB = "data.json"
DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASS = "admin"

# -------- App --------
app = Flask(__name__)
app.secret_key = APP_SECRET

# -------- JSON helpers --------
def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
        return default
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# -------- Data stores --------
users = load_json(DATA_USERS, {})
db = load_json(DATA_DB, {"news": [], "polls": [], "events": [], "team": [], "feedback": []})

# --- Alte Strings in Dictionaries konvertieren ---
for key in ["news", "events", "team"]:
    for i, item in enumerate(db[key]):
        if isinstance(item, str):
            db[key][i] = {
                "id": i+1,
                "text": item if key=="news" else "",
                "title": item if key=="events" else "",
                "desc": "" if key=="events" else "",
                "end_iso": "" if key=="events" else "",
                "name": item if key=="team" else "",
                "role": "" if key=="team" else "",
                "author": "admin" if key=="news" else "",
                "timestamp": datetime.utcnow().isoformat()
            }
save_json(DATA_DB, db)

# ensure admin exists
if DEFAULT_ADMIN_USER not in users:
    users[DEFAULT_ADMIN_USER] = {"pw": generate_password_hash(DEFAULT_ADMIN_PASS), "is_admin": True}
    save_json(DATA_USERS, users)
    print(f"[INFO] Default admin created -> username: {DEFAULT_ADMIN_USER} password: {DEFAULT_ADMIN_PASS}")

# -------- Auth decorators --------
def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapped

def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        u = session.get("user")
        if not u or not users.get(u, {}).get("is_admin"):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapped

# -------- Helpers --------
def next_id(collection):
    dict_items = [item for item in collection if isinstance(item, dict)]
    if not dict_items:
        return 1
    return max(item.get("id",0) for item in dict_items) + 1

def format_datetime_iso(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%d.%m.%Y %H:%M")
    except:
        return "ungültiges Datum"

def parse_iso_safe(iso_str):
    """Versucht ISO-Datum zu parsen, korrigiert automatisch fehlendes T."""
    if not iso_str:
        return None
    iso_str = iso_str.replace(" ", "T")
    try:
        return datetime.fromisoformat(iso_str)
    except:
        return None

def event_countdown(end_iso):
    end = parse_iso_safe(end_iso)
    if not end:
        return "fehlerhaft"
    now = datetime.utcnow()
    diff = end - now
    if diff.total_seconds() <= 0:
        return "läuft / vorbei"
    days = diff.days
    hours = diff.seconds // 3600
    minutes = (diff.seconds // 60) % 60
    return f"{days}T {hours}Std {minutes}Min"

# -------- Modern CSS --------
@app.route("/style.css")
def style_css():
    css = """
    body { font-family: 'Segoe UI', Roboto, Arial, sans-serif; margin:0; background: linear-gradient(135deg,#2e003e,#0f2459); color: #fff; }
    header { display: flex; align-items: center; justify-content: space-between; padding: 20px 50px; background-color: rgba(21,16,51,0.95); box-shadow: 0 4px 20px rgba(0,0,0,0.5); position: sticky; top:0; z-index:1000; height: 100px; }
    header .logo { font-weight: 700; font-size: 2rem; color: #fff; }
    header nav { display: flex; gap: 30px; margin: 0 auto; position: absolute; left: 50%; transform: translateX(-50%); }
    header nav a { color:#cdb7ff; text-decoration:none; font-weight:600; font-size: 1.1rem; transition:0.3s; }
    header nav a:hover { color:#fff; }
    header .user-area { display:flex; align-items:center; gap:10px; }
    .container { max-width:1100px; margin:auto; padding:40px 20px; }
    .card { background: rgba(255,255,255,0.05); padding:30px 25px; margin:25px 0; border-radius:12px; box-shadow: 0 8px 25px rgba(0,0,0,0.5); transition:0.3s; }
    .card:hover { transform: translateY(-3px); }
    input, textarea { width:100%; padding:12px; margin:10px 0; border-radius:8px; border:1px solid rgba(255,255,255,0.2); background: rgba(255,255,255,0.05); color:#fff; font-size:1rem; }
    button { width:100%; background: linear-gradient(135deg, #6a0dad, #9f4dff); border: none; padding:12px; border-radius:10px; color:#fff; cursor:pointer; font-weight:600; font-size:1rem; transition:0.3s; margin-top:10px; }
    button:hover { background: linear-gradient(135deg, #9f4dff, #6a0dad); transform: translateY(-2px); }
    .small { font-size:0.95rem; color:#ddd; }
    .form-wrapper { max-width:400px; margin: 60px auto; }
    .card h3 { font-size: 1.6rem; }
    .card p, .card ul li { font-size: 1.2rem; }
    .card ul li strong { font-size: 1.3rem; }
    """
    return css, 200, {"Content-Type": "text/css"}

# -------- Base Template --------
BASE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>EchoRP</title>
  <link rel="stylesheet" href="/style.css">
</head>
<body>
<header>
  <div class="logo">EchoRP</div>
  <nav>
    <a href="{{ url_for('index') }}">Start</a>
    <a href="{{ url_for('umfrage') }}">Umfrage</a>
    <a href="{{ url_for('events_page') }}">Events</a>
    <a href="{{ url_for('feedback_page') }}">Feedback</a>
  </nav>
  <div class="user-area">
    {% if session.get('user') %}
      <span class="small">eingeloggt als <strong>{{ session['user'] }}</strong></span>
      <a href="{{ url_for('logout') }}">Logout</a>
      {% if users.get(session['user']) and users[session['user']].get('is_admin') %}
        <a href="{{ url_for('admin') }}">Admin</a>
      {% endif %}
    {% else %}
      <a href="{{ url_for('login') }}">Login</a>
      <a href="{{ url_for('register') }}">Sign Up</a>
    {% endif %}
  </div>
</header>
<div class="container">
  {{ content|safe }}
</div>
</body>
</html>
"""

# -------- Startseite --------
@app.route("/")
def index():
    news_html = "<ul>"
    for n in reversed(db["news"][-5:]):
        text = n.get("text","") if isinstance(n, dict) else n
        author = n.get("author","admin") if isinstance(n, dict) else "admin"
        ts = n.get("timestamp", datetime.utcnow().isoformat(timespec='minutes')) if isinstance(n, dict) else datetime.utcnow().isoformat(timespec='minutes')
        news_html += f"<li style='font-size:1.4rem; margin-bottom:10px;'>{text} — <span class='small'>{format_datetime_iso(ts)}</span> von {author}</li>"
    news_html += "</ul>" if db["news"] else "<p>Keine News bisher.</p>"

    content = f"""
    <h1>Willkommen auf EchoRP</h1>
    <p style='font-size:1.3rem;'>Der beste Roleplay-Server auf Emergency Hamburg.</p>
    <div class='card'>
        <h3>Server Code</h3>
        <p>Verbindet euch mit diesem Code im Roblox Spiel: <strong>12345-ABCDE</strong></p>
    </div>
    <div class='card'>
        <h3>Letzte Ankündigungen</h3>
        {news_html}
    </div>
    """
    return render_template_string(BASE, content=content, users=users)

# -------- Events --------
@app.route("/events")
def events_page():
    html="<h2 style='font-size:2rem; margin-bottom:20px;'>Events</h2>"
    if not db["events"]:
        html+="<p style='font-size:1.4rem;'>Keine Events geplant.</p>"
    else:
        now = datetime.utcnow()
        def sort_key(e):
            dt = parse_iso_safe(e.get("end_iso","9999-12-31T23:59:59"))
            return dt if dt else datetime.max
        events_sorted = sorted(db["events"], key=sort_key)
        for e in events_sorted:
            cd = event_countdown(e.get("end_iso",""))
            html+=f"<div class='card'><h3>{e.get('title','')}</h3><p>{e.get('desc','')}</p><p style='font-weight:bold;'>Countdown: {cd}</p></div>"
    return render_template_string(BASE, content=html, users=users)

# -------- Feedback/Chat --------
@app.route("/feedback", methods=["GET","POST"])
@login_required
def feedback_page():
    if "feedback" not in db:
        db["feedback"] = []
    msg=""
    if request.method=="POST":
        text = request.form.get("feedback_text","").strip()
        if text:
            fb = {
                "id": next_id(db.get("feedback", [])),
                "user": session["user"],
                "text": text,
                "timestamp": datetime.utcnow().isoformat()
            }
            db["feedback"].append(fb)
            save_json(DATA_DB, db)
            msg="Feedback hinzugefügt."

    html="<h2 style='font-size:2rem; margin-bottom:20px;'>Feedback / Chat</h2>"
    html+=f"<p style='font-size:1.2rem;'>{msg}</p>"
    html+="<div class='card'><form method='post'><textarea name='feedback_text' placeholder='Schreibe hier dein Feedback...' required></textarea><button type='submit'>Absenden</button></form></div>"
    
    if db["feedback"]:
        html+="<h3>Letzte Einträge</h3>"
        for f in reversed(db["feedback"][-20:]):
            ts = format_datetime_iso(f.get("timestamp",""))
            html+=f"<div class='card'><p>{f.get('text','')}</p><p class='small'>Von {f.get('user','')} am {ts}</p></div>"
    else:
        html+="<p>Keine Einträge bisher.</p>"

    return render_template_string(BASE, content=html, users=users)

# -------- Umfrage --------
@app.route("/umfrage")
def umfrage():
    html="<h2 style='font-size:2rem;'>Umfragen</h2>"
    if not db["polls"]:
        html+="<p style='font-size:1.3rem;'>Keine Umfragen vorhanden.</p>"
    else:
        for p in db["polls"]:
            html+=f"<div class='card'><h3>{p.get('question','')}</h3><ul>"
            for opt, votes in p.get("options", {}).items():
                html+=f"<li>{opt}: {votes} Stimmen</li>"
            html+="</ul></div>"
    return render_template_string(BASE, content=html, users=users)

# -------- Login / Logout / Register --------
@app.route("/login", methods=["GET","POST"])
def login():
    msg=""
    if request.method=="POST":
        u=request.form.get("username")
        p=request.form.get("password")
        if u in users and check_password_hash(users[u]["pw"], p):
            session["user"]=u
            return redirect(url_for("index"))
        msg="Ungültige Zugangsdaten."
    html=f"""
    <div class="form-wrapper">
        <h2>Login</h2>
        <form method="post">
            <input name="username" placeholder="Username">
            <input name="password" placeholder="Password" type="password">
            <button type="submit">Login</button>
        </form>
        <p>{msg}</p>
    </div>
    """
    return render_template_string(BASE, content=html, users=users)

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("index"))

@app.route("/register", methods=["GET","POST"])
def register():
    msg=""
    if request.method=="POST":
        u=request.form.get("username")
        p=request.form.get("password")
        if u in users:
            msg="Username existiert bereits."
        else:
            users[u]={"pw": generate_password_hash(p), "is_admin": False}
            save_json(DATA_USERS, users)
            msg="Registrierung erfolgreich. Du kannst dich jetzt einloggen."
    html=f"""
    <div class="form-wrapper">
        <h2>Sign Up</h2>
        <form method="post">
            <input name="username" placeholder="Username">
            <input name="password" placeholder="Password" type="password">
            <button type="submit">Sign Up</button>
        </form>
        <p>{msg}</p>
    </div>
    """
    return render_template_string(BASE, content=html, users=users)

# -------- Admin Panel --------
@app.route("/admin", methods=["GET","POST"])
@admin_required
def admin():
    msg=""
    if request.method=="POST":
        # News hinzufügen
        if "news_text" in request.form:
            n={"id": next_id(db["news"]), "text": request.form["news_text"], "author": session["user"], "timestamp": datetime.utcnow().isoformat()}
            db["news"].append(n)
            save_json(DATA_DB, db)
            msg="News hinzugefügt."
        # Event hinzufügen
        if "event_title" in request.form:
            e={"id": next_id(db["events"]), "title": request.form["event_title"], "desc": request.form.get("event_desc",""), "end_iso": request.form.get("event_end","")}
            db["events"].append(e)
            save_json(DATA_DB, db)
            msg="Event hinzugefügt."
        # Teammitglied hinzufügen (optional, falls noch gebraucht)
        if "team_name" in request.form:
            t={"id": next_id(db["team"]), "name": request.form["team_name"], "role": request.form.get("team_role","")}
            db["team"].append(t)
            save_json(DATA_DB, db)
            msg="Teammitglied hinzugefügt."

    html=f"""
    <h2 style='font-size:2rem;'>Admin Panel</h2>
    <p style='font-size:1.2rem;'>{msg}</p>

    <div class='card'>
        <h3>News hinzufügen</h3>
        <form method="post">
            <input name="news_text" placeholder="Text">
            <button type="submit">Hinzufügen</button>
        </form>
    </div>

    <div class='card'>
        <h3>Event hinzufügen</h3>
        <form method="post">
            <input name="event_title" placeholder="Titel">
            <input name="event_desc" placeholder="Beschreibung">
            <input name="event_end" placeholder="Endzeit ISO z.B. 2025-09-27T15:30:00">
            <button type="submit">Hinzufügen</button>
        </form>
    </div>

    <div class='card'>
        <h3>Teammitglied hinzufügen</h3>
        <form method="post">
            <input name="team_name" placeholder="Name">
            <input name="team_role" placeholder="Rolle">
            <button type="submit">Hinzufügen</button>
        </form>
    </div>
    """
    return render_template_string(BASE, content=html, users=users)

# -------- Run --------
if __name__ == "__main__":
    app.run(debug=True)
