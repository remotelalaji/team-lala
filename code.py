import os
import json
import traceback
import re

from flask import Flask, render_template_string, Response
from google.oauth2 import service_account
from googleapiclient.discovery import build

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

    creds = service_account.Credentials.from_service_account_info(
        json.loads(raw_json),
        scopes=['https://www.googleapis.com/auth/drive']
    )

    service = build('drive', 'v3', credentials=creds)

except Exception:
    auth_error = traceback.format_exc()


# ================== NAME CLEAN ==================
def extract_name(filename):
    try:
        name_part = filename.replace("Call recording ", "", 1)
        return name_part.split("_")[0].strip()
    except:
        return filename


# ================== GET FILES ==================
def get_files():
    results = service.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed=false",
        fields="files(id, name)",
        pageSize=100
    ).execute()

    files = results.get('files', [])

    for f in files:
        f['clean_name'] = extract_name(f['name'])

    return files


# ================== STREAM ==================
@app.route("/stream/<file_id>")
def stream(file_id):
    try:
        request = service.files().get_media(fileId=file_id)

        def generate():
            yield request.execute()

        return Response(generate(), mimetype="audio/mp4")

    except Exception:
        return f"<pre>{traceback.format_exc()}</pre>"


# ================== MAIN ==================
@app.route("/")
def index():
    try:
        if auth_error:
            return f"<pre>{auth_error}</pre>"

        files = get_files()

        html = """
        <html>
        <head>
            <title>TEAM LALA</title>

            <style>
                body {
                    background:#0b141a;
                    color:white;
                    font-family:Arial;
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
                }

                .msg {
                    background:#005c4b;
                    margin:10px 0;
                    padding:10px 12px;
                    border-radius:10px;
                    max-width:80%;
                    position:relative;
                }

                .name {
                    font-size:14px;
                    margin-bottom:5px;
                }

                audio {
                    width:100%;
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

                <audio controls onplay="pauseOthers(this)">
                    <source src="/stream/{{f.id}}" type="audio/mp4">
                </audio>
            </div>
        {% endfor %}

        </div>

        <script>
        function pauseOthers(current) {
            document.querySelectorAll("audio").forEach(a => {
                if (a !== current) {
                    a.pause();
                }
            });
        }
        </script>

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
