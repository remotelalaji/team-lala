import os
import json
import traceback
import io

from flask import Flask, render_template_string, send_file
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

app = Flask(__name__)

# ================== CONFIG ==================
FOLDER_ID = "1WQ0ZftxRFmJ6eJ0Q6UAaLeMeVnUiemDb"

# ================== AUTH ==================
service = None
auth_error = None

try:
    raw_json = os.environ.get("SERVICE_ACCOUNT_JSON")

    if not raw_json:
        raise Exception("SERVICE_ACCOUNT_JSON missing")

    SERVICE_ACCOUNT_INFO = json.loads(raw_json)

    creds = service_account.Credentials.from_service_account_info(
        SERVICE_ACCOUNT_INFO,
        scopes=['https://www.googleapis.com/auth/drive']
    )

    service = build('drive', 'v3', credentials=creds)

except Exception:
    auth_error = traceback.format_exc()


# ================== GET FILES ==================
def get_files():
    try:
        results = service.files().list(
            q=f"'{FOLDER_ID}' in parents and trashed=false",
            fields="files(id, name)",
            pageSize=100
        ).execute()

        return results.get('files', [])

    except Exception:
        return traceback.format_exc()


# ================== PLAY AUDIO ==================
@app.route("/play/<file_id>")
def play(file_id):
    try:
        request_drive = service.files().get_media(fileId=file_id)

        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request_drive)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        fh.seek(0)
        return send_file(fh, mimetype="audio/mpeg")

    except Exception:
        return f"<pre>{traceback.format_exc()}</pre>"


# ================== MAIN ==================
@app.route("/")
def index():
    try:
        if auth_error:
            return f"<pre>{auth_error}</pre>"

        files = get_files()

        if isinstance(files, str):
            return f"<pre>{files}</pre>"

        html = """
        <html>
        <head>
            <title>TEAM LALA</title>
            <style>
                body {background:#0b1f2a;color:white;font-family:sans-serif;}
                .card {background:#123544;padding:15px;margin:10px;border-radius:10px;}
                audio {width:100%;}
            </style>
        </head>
        <body>

        <h2>🎧 Call Recordings</h2>

        {% for f in files %}
        <div class="card">
            <b>{{f.name}}</b><br><br>

            <audio controls>
                <source src="/play/{{f.id}}">
            </audio>
        </div>
        {% endfor %}

        </body>
        </html>
        """

        return render_template_string(html, files=files)

    except Exception:
        return f"<pre>{traceback.format_exc()}</pre>"


# ================== RUN ==================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
