import os
import json
import traceback
import re
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, Response, redirect, session, url_for
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)
app.secret_key = "supersecretkey"  # change in production

FOLDER_ID = "1WQ0ZftxRFmJ6eJ0Q6UAaLeMeVnUiemDb"

APP_PASSWORD = "669900"

# ================= AUTH (LOGIN) =================
def login_required(f):
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/login")
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        if request.form.get("password") == APP_PASSWORD:
            session["logged_in"] = True
            return redirect("/")
        else:
            error = "Wrong Password"

    return render_template_string("""
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
    body {
        display:flex;
        justify-content:center;
        align-items:center;
        height:100vh;
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        font-family:Segoe UI;
        color:white;
    }
    .box {
        background:rgba(255,255,255,0.1);
        padding:30px;
        border-radius:20px;
        text-align:center;
    }
    input {
        padding:10px;
        width:200px;
        border-radius:10px;
        border:none;
        margin-top:10px;
    }
    button {
        margin-top:15px;
        padding:10px 20px;
        border:none;
        border-radius:10px;
        background:#00e5c3;
        font-weight:bold;
    }
    </style>
    </head>
    <body>

    <form method="POST" class="box">
        <h2>Enter Password</h2>
        <input type="password" name="password" placeholder="Password" required>
        <br>
        <button type="submit">Login</button>
        <p style="color:red;">{{error}}</p>
    </form>

    </body>
    </html>
    """, error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ================= GOOGLE DRIVE =================
service = None
auth_error = None

try:
    raw_json = os.environ.get("SERVICE_ACCOUNT_JSON")

    creds = service_account.Credentials.from_service_account_info(
        json.loads(raw_json),
        scopes=['https://www.googleapis.com/auth/drive']
    )

    service = build('drive', 'v3', credentials=creds)

except Exception:
    auth_error = traceback.format_exc()

# ================= NAME =================
def extract_name(filename):
    try:
        name = filename.replace("Call recording ", "", 1)
        name = name.split("_")[0]
        name = name.replace("#", "")
        name = " ".join(name.split())
        return name.strip()
    except:
        return filename

# ================= DATE =================
def extract_datetime(filename):
    try:
        match = re.search(r"_(\d{6})_(\d{6})", filename)
        if match:
            return datetime.strptime(match.group(1)+match.group(2), "%y%m%d%H%M%S")
    except:
        return None

# ================= PROCESS =================
def process_files(files, selected_customer=None):
    processed = []
    customers = set()

    for f in files:
        name = extract_name(f['name'])
        dt = extract_datetime(f['name'])

        customers.add(name)

        if selected_customer and name != selected_customer:
            continue

        f['clean_name'] = name
        f['dt_obj'] = dt

        if dt:
            today = datetime.now().date()
            if dt.date() == today:
                label = "Today"
            elif dt.date() == today - timedelta(days=1):
                label = "Yesterday"
            else:
                label = dt.strftime("%d %b %Y")

            f['dt'] = f"{label} • {dt.strftime('%I:%M %p')}"
        else:
            f['dt'] = ""

        processed.append(f)

    processed.sort(key=lambda x: x['dt_obj'] or datetime.min, reverse=True)
    customers = sorted(customers, key=lambda x: x.strip().lower())

    return processed, customers

# ================= STREAM =================
@app.route("/stream/<file_id>")
@login_required
def stream(file_id):
    request_drive = service.files().get_media(fileId=file_id)
    return Response(request_drive.execute(), mimetype="audio/mp4")

# ================= MAIN =================
@app.route("/")
@login_required
def index():
    if auth_error:
        return "<pre>Auth Error</pre>"

    selected_customer = request.args.get("customer")

    results = service.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed=false",
        fields="files(id, name)",
        pageSize=1000
    ).execute()

    files, customers = process_files(results.get('files', []), selected_customer)

    return render_template_string("""
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
    body {
        margin:0;
        font-family:Segoe UI;
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        color:white;
    }
    .header {
        padding:15px;
        font-weight:bold;
    }
    .custs {
        display:flex;
        overflow-x:auto;
        gap:10px;
        padding:10px;
    }
    .cust {
        padding:10px 15px;
        background:rgba(255,255,255,0.1);
        border-radius:20px;
        text-decoration:none;
        color:white;
        font-weight:bold;
    }
    .msg {
        margin:15px;
        padding:15px;
        background:rgba(255,255,255,0.1);
        border-radius:15px;
    }
    </style>
    </head>
    <body>

    <div class="header">
        📞 TEAM LALA CALLS |
        <a href="/logout" style="color:#00e5c3;">Logout</a>
    </div>

    <div class="custs">
        <a class="cust" href="/">All</a>
        {% for c in customers %}
        <a class="cust" href="/?customer={{c}}">{{c}}</a>
        {% endfor %}
    </div>

    {% for f in files %}
    <div class="msg">
        <b>{{f.clean_name}}</b><br>
        {{f.dt}}
        <audio controls style="width:100%;">
            <source src="/stream/{{f.id}}" type="audio/mp4">
        </audio>
    </div>
    {% endfor %}

    </body>
    </html>
    """, files=files, customers=customers)
    
# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
