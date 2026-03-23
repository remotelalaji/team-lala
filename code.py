import os
import json
import traceback
import re
import tempfile
import subprocess
from datetime import datetime
from flask import Flask, render_template_string, request, Response, send_file
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


# ================= DATE PARSE =================
def extract_datetime(filename):
    try:
        match = re.search(r"_(\d{6})_(\d{6})", filename)
        if match:
            dt = datetime.strptime(match.group(1) + match.group(2), "%d%m%y%H%M%S")
            return dt
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


# ================= DOWNLOAD MP3 =================
@app.route("/download/<file_id>")
def download(file_id):
    try:
        request_drive = service.files().get_media(fileId=file_id)

        # temp m4a
        m4a = tempfile.NamedTemporaryFile(delete=False, suffix=".m4a")
        m4a.write(request_drive.execute())
        m4a.close()

        # convert to mp3
        mp3_path = m4a.name.replace(".m4a", ".mp3")

        subprocess.run([
            "ffmpeg", "-i", m4a.name,
            "-q:a", "0", "-map", "a",
            mp3_path
        ])

        return send_file(mp3_path, as_attachment=True)

    except Exception as e:
        return str(e)


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

        <style>
        body {
            background:#0b141a;
            color:white;
            font-family:sans-serif;
            margin:0;
        }

        .header {
            background:#202c33;
            padding:15px;
            font-size:18px;
            font-weight:bold;
        }

        .chat {
            padding:10px;
            max-height:90vh;
            overflow-y:auto;
        }

        .msg {
            background:#005c4b;
            margin:10px 0;
            padding:10px 12px;
            border-radius:10px;
        }

        .name {
            font-size:14px;
            margin-bottom:5px;
        }

        .time {
            font-size:12px;
            color:#ccc;
            margin-bottom:5px;
        }

        audio {
            width:100%;
        }

        .btn {
            display:inline-block;
            padding:8px 12px;
            background:#00a884;
            color:white;
            border-radius:6px;
            text-decoration:none;
            margin-top:5px;
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

            <br>
            <a class="btn" href="/download/{{f.id}}">⬇ Download MP3</a>
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
