import os
import json
import traceback
import re
from datetime import datetime
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
        return filename.replace("Call recording ", "", 1).split("_")[0].strip()
    except:
        return filename


# ================= DATE FIX (CORRECT) =================
def extract_datetime(filename):
    try:
        match = re.search(r"_(\d{6})_(\d{6})", filename)
        if match:
            date_raw = match.group(1)
            time_raw = match.group(2)

            # 🔥 FIXED FORMAT (YYMMDD)
            return datetime.strptime(date_raw + time_raw, "%y%m%d%H%M%S")
    except:
        pass
    return None


# ================= GET FILES =================
def get_files(page_token=None):

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
        dt = extract_datetime(f['name'])

        f['clean_name'] = extract_name(f['name'])
        f['dt_obj'] = dt
        f['dt'] = dt.strftime("%d %b %Y | %I:%M %p") if dt else ""

        processed.append(f)

    # latest first
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

        files, next_token = get_files(token)

        html = """
        <html>
        <head>
        <title>TEAM LALA</title>

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

        .chat {
            padding:12px;
        }

        .msg {
            background:#005c4b;
            margin:12px 0;
            padding:14px;
            border-radius:12px;
        }

        .name {
            font-size:16px;
            font-weight:bold;
        }

        .time {
            font-size:13px;
            color:#ccc;
        }

        audio {
            width:100%;
            margin-top:8px;
        }

        .btn {
            display:inline-block;
            padding:14px 22px;
            font-size:16px;
            background:#00a884;
            color:white;
            border-radius:10px;
            text-decoration:none;
        }
        </style>
        </head>

        <body>

        <div class="header">📱 TEAM LALA - Recordings</div>

        <div class="chat">

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

        </div>

        <script>
        function pauseOthers(current){
            document.querySelectorAll("audio").forEach(a=>{
                if(a!==current){
                    a.pause();
                }
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
