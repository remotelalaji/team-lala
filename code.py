import os
import json
import traceback
from flask import Flask, render_template_string

from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)

FOLDER_ID = "1n78FKBkQHvdqcTjOap9yUB1f_G0JsjrR"

# ================= SAFE INIT =================
service = None
auth_error = None

try:
    raw_json = os.environ.get("SERVICE_ACCOUNT_JSON")

    if not raw_json:
        raise Exception("SERVICE_ACCOUNT_JSON missing")

    SERVICE_ACCOUNT_INFO = json.loads(raw_json)

    creds = service_account.Credentials.from_service_account_info(
        SERVICE_ACCOUNT_INFO,
        scopes=['https://www.googleapis.com/auth/drive.readonly']
    )

    service = build('drive', 'v3', credentials=creds)

except Exception:
    auth_error = traceback.format_exc()


# ================= ROUTE =================
@app.route("/")
def index():
    try:
        if auth_error:
            return f"<pre>AUTH ERROR:\n{auth_error}</pre>"

        results = service.files().list(
            q=f"'{FOLDER_ID}' in parents",
            fields="files(name)",
            pageSize=20,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives"
        ).execute()

        files = results.get('files', [])

        return "<br>".join([f['name'] for f in files]) or "No files found"

    except Exception:
        return f"<pre>{traceback.format_exc()}</pre>"


# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
