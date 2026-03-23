import io
import re
from flask import Flask, request, render_template_string, send_file
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

app = Flask(__name__)

# ================== CONFIG ==================
SERVICE_ACCOUNT_FILE = "service_account.json"  # JSON file name
FOLDER_ID = "1n78FKBkQHvdqcTjOap9yUB1f_G0JsjrR"  # tumhara folder id
PER_PAGE = 100

# ================== GOOGLE DRIVE AUTH ==================
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=['https://www.googleapis.com/auth/drive.readonly']
)

service = build('drive', 'v3', credentials=creds)

# ================== PARSE ==================
def parse_filename(name):
    match = re.search(r"Call recording (.+?)_(\d{6})_(\d{6})", name)

    if match:
        raw_name = match.group(1)
        date_raw = match.group(2)
        time_raw = match.group(3)

        # DATE FIX (IMPORTANT 🔥)
        day = date_raw[:2]
        month = date_raw[2:4]
        year = "20" + date_raw[4:]

        date = f"{day}-{month}-{year}"
        time = f"{time_raw[:2]}:{time_raw[2:4]}:{time_raw[4:]}"

        return raw_name.strip(), date, time

    return name, "", ""

# ================== GET FILES ==================
def get_files():
    results = service.files().list(
        q=f"'{FOLDER_ID}' in parents and mimeType contains 'audio/'",
        fields="files(id, name)",
        pageSize=1000
    ).execute()

    files = results.get('files', [])

    parsed = []
    for f in files:
        name, date, time = parse_filename(f['name'])
        parsed.append({
            "id": f['id'],
            "name": name,
            "date": date,
            "time": time,
            "filename": f['name']
        })

    return sorted(parsed, key=lambda x: x["time"], reverse=True)

# ================== STREAM AUDIO ==================
@app.route("/play/<file_id>")
def play(file_id):
    request_drive = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request_drive)

    done = False
    while not done:
        status, done = downloader.next_chunk()

    fh.seek(0)
    return send_file(fh, mimetype="audio/mpeg")

# ================== MAIN ==================
@app.route("/")
def index():
    page = int(request.args.get("page", 1))
    files = get_files()

    start = (page - 1) * PER_PAGE
    end = start + PER_PAGE

    total_pages = (len(files) // PER_PAGE) + 1
    current_files = files[start:end]

    html = """
    <html>
    <head>
        <title>TEAM LALA</title>
        <style>
            body {background:#0b1f2a;color:white;font-family:sans-serif;}
            .card {background:#123544;padding:15px;margin:10px;border-radius:10px;}
            audio {width:100%;}
            .header {display:flex;justify-content:space-between;}
            .btn {color:#00ffaa;margin:10px;}
        </style>
    </head>
    <body>

    <div class="header">
        <h2>🎧 Recordings</h2>
        <h2>TEAM LALA</h2>
    </div>

    {% for f in files %}
    <div class="card">
        <b>{{f.name}}</b><br>
        📅 {{f.date}} ⏰ {{f.time}}
        <audio controls>
            <source src="/play/{{f.id}}">
        </audio>
    </div>
    {% endfor %}

    <div style="text-align:center">
        {% if page > 1 %}
            <a class="btn" href="/?page={{page-1}}">⬅ Prev</a>
        {% endif %}
        Page {{page}}
        {% if page < total %}
            <a class="btn" href="/?page={{page+1}}">Next ➡</a>
        {% endif %}
    </div>

    </body>
    </html>
    """

    return render_template_string(html, files=current_files, page=page, total=total_pages)

# ================== RUN ==================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)