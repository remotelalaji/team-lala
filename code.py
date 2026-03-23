import os
import json
import traceback

from flask import Flask, render_template_string, Response
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)

FOLDER_ID = "1WQ0ZftxRFmJ6eJ0Q6UAaLeMeVnUiemDb"

# ================= AUTH =================
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


# ================= GET FILES =================
def get_files():
    results = service.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed=false",
        fields="files(id, name)",
        pageSize=100
    ).execute()

    return results.get('files', [])


# ================= STREAM AUDIO =================
@app.route("/stream/<file_id>")
def stream(file_id):
    try:
        request = service.files().get_media(fileId=file_id)

        def generate():
            fh = request.execute()
            yield fh  # direct stream

        return Response(generate(), mimetype="audio/mp4")

    except Exception:
        return f"<pre>{traceback.format_exc()}</pre>"


# ================= MAIN =================
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

            <audio controls onplay="pauseOthers(this)">
                <source src="/stream/{{f.id}}" type="audio/mp4">
            </audio>
        </div>
        {% endfor %}

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


# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
