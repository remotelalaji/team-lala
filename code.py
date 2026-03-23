import os
import json
import traceback
import re
import math
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, Response
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)

FOLDER_ID = "1WQ0ZftxRFmJ6eJ0Q6UAaLeMeVnUiemDb"
PER_PAGE = 50

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
        pass
    return None

# ================= GET ALL FILES =================
def get_all_files():
    results = service.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed=false",
        fields="files(id, name)",
        pageSize=1000
    ).execute()

    return results.get('files', [])

# ================= PROCESS =================
def process_files(files, search, start, end):
    processed = []

    for f in files:
        name = extract_name(f['name'])
        dt = extract_datetime(f['name'])

        if search and search.lower() not in name.lower():
            continue

        if start and dt and dt < start:
            continue
        if end and dt and dt > end:
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

            f['dt'] = f"{label} | {dt.strftime('%I:%M %p')}"
        else:
            f['dt'] = ""

        processed.append(f)

    processed.sort(key=lambda x: x['dt_obj'] or datetime.min, reverse=True)

    return processed

# ================= STREAM =================
@app.route("/stream/<file_id>")
def stream(file_id):
    request_drive = service.files().get_media(fileId=file_id)
    return Response(request_drive.execute(), mimetype="audio/mp4")

# ================= MAIN =================
@app.route("/")
def index():
    try:
        if auth_error:
            return f"<pre>{auth_error}</pre>"

        page = int(request.args.get("page", 1))
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

        all_files = get_all_files()
        processed = process_files(all_files, search, start_dt, end_dt)

        total_pages = math.ceil(len(processed) / PER_PAGE)

        start = (page - 1) * PER_PAGE
        end = start + PER_PAGE
        current_files = processed[start:end]

        html = """
        <html>
        <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">

        <style>
        body {background:#0b141a;color:white;font-family:sans-serif;margin:0;}

        .header {background:#202c33;padding:18px;font-size:20px;font-weight:bold;}

        .filter {padding:10px;background:#111;}

        input,button {
            padding:10px;margin:5px;border-radius:8px;border:none;
        }

        button {background:#00a884;color:white;}

        .msg {background:#005c4b;margin:12px;padding:14px;border-radius:12px;}

        .name {font-weight:bold;font-size:18px;}

        .time {font-size:13px;color:#ccc;}

        audio {width:100%;margin-top:8px;}

        .pagination {text-align:center;margin:20px;}

        .page {
            padding:8px 12px;
            margin:2px;
            background:#00a884;
            border-radius:6px;
            text-decoration:none;
            color:white;
        }

        .active {
            background:#ff9800;
        }
        </style>
        </head>

        <body>

        <div class="header">📱 TEAM LALA</div>

        <div class="filter">
            <form>
                🔍 <input type="text" name="search">

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

        <div class="pagination">
        {% for p in range(1, total_pages+1) %}
            <a class="page {% if p==page %}active{% endif %}" href="/?page={{p}}">
                {{p}}
            </a>
        {% endfor %}
        </div>

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

        return render_template_string(html, files=current_files, page=page, total_pages=total_pages)

    except Exception:
        return f"<pre>{traceback.format_exc()}</pre>"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
