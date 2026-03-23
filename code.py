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

            f['dt'] = f"{label} • {dt.strftime('%I:%M %p')}"
        else:
            f['dt'] = ""

        processed.append(f)

    processed.sort(key=lambda x: x['dt_obj'] or datetime.min, reverse=True)

    # ✅ Proper alphabetical sorting
    customers = sorted(customers, key=lambda x: x.strip().lower())

    return processed, customers

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
            margin:0;
            font-family: "Segoe UI", sans-serif;
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            color: white;
            display:flex;
        }

        /* ===== SIDEBAR ===== */
        .sidebar {
            width:260px;
            height:100vh;
            overflow-y:auto;
            background: rgba(0,0,0,0.5);
            backdrop-filter: blur(12px);
            padding:15px;
        }

        .cust {
            display:block;
            padding:12px 14px;
            margin-bottom:8px;
            border-radius:10px;
            text-decoration:none;
            color:white;
            font-weight:700;
            font-size:15px;
            background: rgba(255,255,255,0.08);
        }

        .cust:hover {
            background:#00a884;
        }

        .active {
            background:#00e5c3;
            color:black;
        }

        /* ===== MAIN ===== */
        .main {
            flex:1;
            overflow-y:auto;
            padding-bottom:50px;
        }

        .header {
            padding:18px;
            font-size:22px;
            font-weight:bold;
            background: rgba(0,0,0,0.3);
            backdrop-filter: blur(12px);
            position: sticky;
            top: 0;
        }

        .msg {
            margin:15px;
            padding:18px;
            border-radius:20px;
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(12px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        }

        .name {
            font-size:20px;
            font-weight:800;
        }

        .time {
            font-size:14px;
            font-weight:600;
            color:#d4f5ee;
            margin-top:5px;
        }

        audio {
            width:100%;
            margin-top:12px;
        }

        /* ===== MOBILE FIX ===== */
        @media (max-width: 768px) {

            body {
                display:block;
            }

            .sidebar {
                width:100%;
                height:auto;
                display:flex;
                overflow-x:auto;
                gap:10px;
            }

            .cust {
                white-space:nowrap;
                flex-shrink:0;
            }

            .main {
                width:100%;
            }
        }
        </style>
        </head>

        <body>

        <!-- SIDEBAR -->
        <div class="sidebar">
            <a class="cust" href="/">All</a>

            {% for c in customers %}
                <a class="cust {% if c==selected_customer %}active{% endif %}" href="/?customer={{c}}">
                    {{c}}
                </a>
            {% endfor %}
        </div>

        <!-- MAIN -->
        <div class="main">

        <div class="header">📞 TEAM LALA CALLS</div>

        {% for f in files %}
        <div class="msg">
            <div class="name">{{f.clean_name}}</div>
            <div class="time">{{f.dt}}</div>

            <audio controls preload="none" onplay="pauseOthers(this)">
                <source src="/stream/{{f.id}}" type="audio/mp4">
            </audio>
        </div>
        {% endfor %}

        </div>

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

# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
