import os
import json
import re
from datetime import datetime
import pytz
from flask import Flask, render_template_string, request, Response, redirect, session
from google.oauth2 import service_account
from googleapiclient.discovery import build
from functools import wraps

app = Flask(__name__)
app.secret_key = "secretkey"

FOLDER_ID = "1WQ0ZftxRFmJ6eJ0Q6UAaLeMeVnUiemDb"
APP_PASSWORD = "669900"

# ================= LOGIN =================
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/login")
        return f(*args, **kwargs)
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
    <body style="display:flex;justify-content:center;align-items:center;height:100vh;
    background:#0f2027;color:white;font-family:sans-serif;">
        <form method="POST">
            <h2>Enter Password</h2>
            <input type="password" name="password" required>
            <br><br>
            <button>Login</button>
            <p style="color:red;">{{error}}</p>
        </form>
    </body>
    </html>
    """, error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ================= GOOGLE =================
service = None
try:
    raw_json = os.environ.get("SERVICE_ACCOUNT_JSON")
    creds = service_account.Credentials.from_service_account_info(
        json.loads(raw_json),
        scopes=['https://www.googleapis.com/auth/drive']
    )
    service = build('drive', 'v3', credentials=creds)
except:
    service = None

# ================= HELPERS =================
def extract_name(filename):
    try:
        name = filename.replace("Call recording ", "", 1)
        name = name.split("_")[0]
        name = name.replace("#", "")
        return " ".join(name.split()).strip()
    except:
        return filename

def extract_datetime(filename):
    try:
        match = re.search(r"_(\d{6})_(\d{6})", filename)
        if match:
            return datetime.strptime(match.group(1)+match.group(2), "%y%m%d%H%M%S")
    except:
        return None

# ================= PROCESS =================
def process_files(files, selected_customer=None, selected_date=None):
    processed = []
    customers = set()
    ist = pytz.timezone("Asia/Kolkata")

    for f in files:
        name = extract_name(f['name'])
        dt = extract_datetime(f['name'])

        if selected_customer and name != selected_customer:
            continue

        if dt:
            dt = pytz.utc.localize(dt).astimezone(ist)

            if selected_date:
                if dt.strftime("%Y-%m-%d") != selected_date:
                    continue

            f['dt'] = dt.strftime("%d %b %Y • %I:%M %p")
        else:
            f['dt'] = ""

        f['clean_name'] = name
        f['dt_obj'] = dt

        customers.add(name)
        processed.append(f)

    processed.sort(key=lambda x: x['dt_obj'] or datetime.min, reverse=True)
    customers = sorted(customers, key=lambda x: x.lower())

    return processed, customers

# ================= STREAM =================
@app.route("/stream/<file_id>")
@login_required
def stream(file_id):
    return Response(
        service.files().get_media(fileId=file_id).execute(),
        mimetype="audio/mp4"
    )

# ================= MAIN =================
@app.route("/")
@login_required
def index():
    if service is None:
        return "Google Drive not connected"

    selected_customer = request.args.get("customer")
    selected_date = request.args.get("date")

    results = service.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed=false",
        fields="files(id, name)",
        pageSize=1000
    ).execute()

    files, customers = process_files(
        results.get('files', []),
        selected_customer,
        selected_date
    )

    return render_template_string("""
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>

    body {
        margin:0;
        font-family:sans-serif;
        background:#0f2027;
        color:white;
    }

    .header {
        position: sticky;
        top: 0;
        z-index: 1000;
        padding:15px;
        background:#111; /* 🔥 solid */
    }

    .custs {
        position: sticky;
        top: 55px;
        z-index: 999;
        display:flex;
        overflow-x:auto;
        gap:10px;
        padding:10px;
        background:#1a1a1a; /* 🔥 solid */
    }

    .cust {
        padding:10px 15px;
        background:#333;
        border-radius:20px;
        text-decoration:none;
        color:white;
        white-space: nowrap;
    }

    .msg {
        margin:15px;
        padding:15px;
        background:#222;
        border-radius:15px;
    }

    audio {
        width:100%;
        margin-top:10px;
    }

    </style>
    </head>

    <body>

    <div class="header">
        📞 rahul jnb 1 |
        <a href="/logout" style="color:#00e5c3;">Logout</a>

        <form method="GET" style="display:inline;">
            <input type="hidden" name="customer" value="{{request.args.get('customer','')}}">
            <input type="date" name="date" onchange="this.form.submit()">
        </form>
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

        <audio controls preload="none">
            <source src="/stream/{{f.id}}" type="audio/mp4">
        </audio>
    </div>
    {% endfor %}

    <!-- AUDIO FIX -->
    <script>
    document.addEventListener("DOMContentLoaded", function () {
        document.body.addEventListener("play", function(e) {
            if (e.target.tagName === "AUDIO") {
                const audios = document.querySelectorAll("audio");
                audios.forEach(audio => {
                    if (audio !== e.target) {
                        audio.pause();
                        audio.currentTime = 0;
                    }
                });
            }
        }, true);
    });
    </script>

    </body>
    </html>
    """, files=files, customers=customers)

# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
