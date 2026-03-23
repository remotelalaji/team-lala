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

        results = service.files().list(
            q=f"'{FOLDER_ID}' in parents and trashed=false",
            fields="files(id, name)",
            pageSize=1000
        ).execute()

        files, customers = process_files(results.get('files', []), selected_customer)

        html = """
        <html>
        <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">

        <style>
        body {
            background: linear-gradient(135deg, #0b141a, #111b21);
            color: white;
            font-family: "Segoe UI", sans-serif;
            margin: 0;
        }

        .header {
            background: rgba(32,44,51,0.9);
            backdrop-filter: blur(10px);
            padding: 18px;
            font-size: 20px;
            font-weight: bold;
            position: sticky;
            top: 0;
        }

        .customers {
            display:flex;
            overflow-x:auto;
            padding:10px;
            background: rgba(0,0,0,0.4);
            backdrop-filter: blur(8px);
        }

        .cust {
            padding:8px 14px;
            margin-right:8px;
            background:#1f2c33;
            border-radius:20px;
            text-decoration:none;
            color:white;
            font-size:14px;
        }

        .active {
            background:#00a884;
        }

        .msg {
            background: linear-gradient(145deg, #075e54, #0b8f75);
            margin:14px;
            padding:16px;
            border-radius:16px;
            box-shadow: 0 6px 18px rgba(0,0,0,0.3);
        }

        .name {
            font-size:18px;
            font-weight:700;
        }

        .time {
            font-size:12px;
            color:#d1d1d1;
        }

        audio {
            width:100%;
            margin-top:10px;
        }
        </style>
        </head>

        <body>

        <div class="header">📞 TEAM LALA CALLS</div>

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
