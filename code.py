import os
import json
import traceback
import re
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, Response
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)

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

# ================= GET FILES =================
def get_all_files():
    results = service.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed=false",
        fields="files(id, name)",
        pageSize=1000
    ).execute()

    return results.get('files', [])

# ================= PROCESS =================
def process_files(files, selected_customer=None):

    processed = []
    customers = set()

    for f in files:
        name = extract_name(f['name'])
        dt = extract_datetime(f['name'])

        customers.add(name)

        if selected_customer and name != selected_customer:
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

    return processed, sorted(customers)

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

        selected_customer = request.args.get("customer")

        all_files = get_all_files()
        files, customers = process_files(all_files, selected_customer)

        html = """
        <html>
        <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">

        <style>
        body {background:#0b141a;color:white;font-family:sans-serif;margin:0;}

        .header {background:#202c33;padding:15px;font-size:18px;}

        .customers {
            display:flex;
            overflow-x:auto;
            padding:10px;
            background:#111;
        }

        .cust {
            padding:8px 12px;
            margin-right:8px;
            background:#005c4b;
            border-radius:20px;
            text-decoration:none;
            color:white;
            white-space:nowrap;
        }

        .active {
            background:#ff9800;
        }

        .msg {background:#005c4b;margin:12px;padding:12px;border-radius:10px;}

        .name {font-weight:bold;font-size:18px;}

        .time {font-size:12px;color:#ccc;}

        audio {width:100%;margin-top:5px;}
        </style>
        </head>

        <body>

        <div class="header">📱 TEAM LALA</div>

        <div class="customers">
            <a class="cust" href="/">All</a>
            {% for c in customers %}
                <a class="cust {% if c==selected_customer %}active{% endif %}" href="/?customer={{c}}">
                    {{c}}
                </a>
            {% endfor %}
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

        return render_template_string(html, files=files, customers=customers, selected_customer=selected_customer)

    except Exception:
        return f"<pre>{traceback.format_exc()}</pre>"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
