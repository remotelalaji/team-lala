import os
import json
import traceback
from flask import Flask, render_template_string

from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)

FOLDER_ID = "1WQ0ZftxRFmJ6eJ0Q6UAaLeMeVnUiemDb"

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


def get_files():
    try:
        results = service.files().list(
            q=f"'{FOLDER_ID}' in parents and trashed=false",
            fields="files(id, name)",
            pageSize=100
        ).execute()

        return [f['name'] for f in results.get('files', [])]

    except Exception:
        return traceback.format_exc()


@app.route("/")
def index():
    try:
        if auth_error:
            return f"<pre>{auth_error}</pre>"

        files = get_files()

        if isinstance(files, str):
            return f"<pre>{files}</pre>"

        return "<br>".join(files) if files else "No files found"

    except Exception:
        return f"<pre>{traceback.format_exc()}</pre>"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
