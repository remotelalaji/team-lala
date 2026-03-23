import os
import json
import traceback
from flask import Flask, render_template_string

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

app = Flask(__name__)

# ================== CONFIG ==================
FOLDER_ID = "1n78FKBkQHvdqcTjOap9yUB1f_G0JsjrR"

# ================== GOOGLE DRIVE AUTH ==================
try:
    raw_json = os.environ.get("SERVICE_ACCOUNT_JSON")

    if not raw_json:
        raise Exception("SERVICE_ACCOUNT_JSON not found")

    SERVICE_ACCOUNT_INFO = json.loads(raw_json)

    creds = service_account.Credentials.from_service_account_info(
        SERVICE_ACCOUNT_INFO,
        scopes=['https://www.googleapis.com/auth/drive.readonly']
    )

    service = build('drive', 'v3', credentials=creds)

except Exception:
    service = None
    auth_error = traceback.format_exc()

# ================== GET FILES ==================
def get_files():
    try:
        results = service.files().list(
            q=f"'{FOLDER_ID}' in parents",
            fields="files(id, name)",
            pageSize=100,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives"
        ).execute()

        files = results.get('files', [])
        return [f['name'] for f in files]

    except HttpError as e:
        return f"""
GOOGLE DRIVE ERROR

Status Code: {e.resp.status}

Details:
{e.content.decode() if hasattr(e.content, 'decode') else str(e)}
"""

    except Exception:
        return traceback.format_exc()

# ================== MAIN ==================
@app.route("/")
def index():
    try:
        if service is None:
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
                .card {background:#123544;padding:10px;margin:10px;border-radius:8px;}
            </style>
        </head>
        <body>

        <h2>📂 Files List</h2>

        {% for f in files %}
            <div class="card">{{f}}</div>
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
