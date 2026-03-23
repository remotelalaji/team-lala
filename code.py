import os
import json
import traceback
import re
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, Response
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)

# ================= CONFIG =================
FOLDER_ID = "1WQ0ZftxRFmJ6eJ0Q6UAaLeMeVnUiemDb"

# ================= AUTH =================
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


# ================= NAME CLEAN =================
def extract_name(filename):
    try:
        name = filename.replace("Call recording ", "", 1)
        name = name.split("_")[0]
        name = name.replace("#", "")
        name = " ".join(name.split())
        return name.strip()
    except:
        return filename


# ================= DATE PARSE =================
def extract_datetime(filename):
    try:
        match = re.search(r"_(\d{6})_(\d{6})", filename)
        if match:
            return datetime.strptime(match.group(1)+match.group(2), "%y%m%d%H%M%S")
    except:
        pass
    return None


# ================= GET FILES =================
def get_files(page_token=None, search="", start=None, end=None):

    results = service.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed=false",
        fields="nextPageToken, files(id, name)",
        pageSize=50,
        orderBy="createdTime desc",
        pageToken=page_token
    ).execute()

    files = results.get('files', [])
    next_token = results.get('nextPageToken')

    processed = []

    for f in files:
        name = extract_name(f['name'])
        dt = extract_datetime(f['name'])

        # 🔍 search filter
        if search and search.lower() not in name.lower():
            continue

        # 📅 date filter
        if start and dt and dt < start:
            continue
        if end and dt and dt > end:
            continue

        f['clean_name'] = name
        f['dt_obj'] = dt

        # 📅 WhatsApp style date
        if dt:
            today = datetime.now().date()
            if dt.date() == today:
                label = "Today"
            elif dt.date() == today - timedelta(days=1):
                label = "Yesterday"
            else:
                label = dt.strftime("%d %b %Y")

            f['dt'] = f"{label} | {dt.strftime('%I:%M %p')}"
        else:
            f['dt'] = ""

        processed.append(f)

    # 🔥 latest first
    processed.sort(key=lambda x: x['dt_obj'] or datetime.min, reverse=True)

    return processed, next_token


# ================= STREAM =================
@app.route("/stream/<file_id>")
def stream(file_id):
    try:
        request_drive = service.files().get_media(fileId=file_id)
        return Response(request_drive.execute(), mimetype="audio/mp4")
    except Exception:
        return f"<pre>{traceback.format_exc()}</pre>"


# ================= MAIN =================
@app.route("/")
def index():
    try:
        if auth_error:
            return f"<pre>{auth_error}</pre>"

        token = request.args.get("pageToken")
        search = request.args.get("search", "")

        today = request.args.get("today")
        yesterday = request.args.get("yesterday")
        single = request.args.get("single")

        start_dt = None
        end_dt = None

        if today:
            now = datetime.now()
            start_dt = datetime(now.year, now.month, now.day)
            end_dt = start_dt + timedelta(days=1)

        elif yesterday:
            now = datetime.now()
            start_dt = datetime(now.year, now.month, now.day) - timedelta(days=1)
            end_dt = start_dt + timedelta(days=1)

        elif single:
            start_dt = datetime.strptime(single, "%Y-%m-%d")
            end_dt = start_dt + timedelta(days=1)

        files, next_token = get_files(token, search, start_dt, end_dt)

        html = """
        <html>
        <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">

        <style>
        body {
            background:#0b141a;
            color:white;
            font-family:sans-serif;
            margin:0;
            font-size:16px;
        }

        .header {
            background:#202c33;
            padding:18px;
            font-size:20px;
            font-weight:bold;
        }

        .filter {
            padding:10px;
            background:#111;
        }

        input {
            padding:10px;
            margin:5px;
            border-radius:8px;
            border:none;
            font-size:14px;
        }

        button {
            padding:10px;
            border:none;
            border-radius:8px;
            background:#00a884;
            color:white;
            font-size:14px;
        }

        .msg {
            background:#005c4b;
            margin:12px;
            padding:14px;
            border-radius:12px;
        }

        .name {
            font-family: Calibri, "Segoe UI", Arial, sans-serif;
            font-weight:bold;
            font-size:18px;
        }

        .time {
            font-size:13px;
            color:#ccc;
            margin-top:3px;
        }

        audio {
            width:100%;
            margin-top:8px;
        }

        .btn {
            display:inline-block;
            padding:14px 22px;
            background:#00a884;
            color:white;
            border-radius:10px;
            text-decoration:none;
            font-size:16px;
        }
        </style>
        </head>

        <body>

        <div class="header">📱 TEAM LALA</div>

        <div class="filter">
            <form>
                🔍 <input type="text" name="search" placeholder="Search name">

                📅 <input type="date" name="single">

                <button name="today" value="1">Today</button>
                <button name="yesterday" value="1">Yesterday</button>

                <button>Apply</button>
            </form>
        </div>

        {% for f in files %}
        <div class="msg">
            <div class="name">{{f.clean_name}}</div>
            <div class="time">{{f.dt}}</div>

            <audio controls preload="none" onplay="pauseOthers(this)">
                <source src="/stream/{{f.id}}" type="audio/mp4">
            </audio>
        </div>
        {% endfor %}

        {% if next_token %}
        <div style="text-align:center;margin:20px;">
            <a class="btn" href="/?pageToken={{next_token}}">
                ➡ Next Page
            </a>
        </div>
        {% endif %}

        <script>
        function pauseOthers(current){
            document.querySelectorAll("audio").forEach(a=>{
                if(a!==current){a.pause();}
            });
        }
        </script>

        </body>
        </html>
        """

        return render_template_string(html, files=files, next_token=next_token)

    except Exception:
        return f"<pre>{traceback.format_exc()}</pre>"


# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
