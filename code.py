# ================= MAIN =================
@app.route("/")
@login_required
def index():
    if service is None:
        return "Google Drive not connected"

    selected_customer = request.args.get("customer")
    selected_date = request.args.get("date")

    results = service.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed=false",
        fields="files(id, name)",
        pageSize=1000
    ).execute()

    files, customers = process_files(
        results.get('files', []),
        selected_customer,
        selected_date
    )

    return render_template_string("""
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>

body {
    margin:0;
    font-family:sans-serif;
    background:#0f2027;
    color:white;
}

/* HEADER */
.header {
    position: sticky;
    top: 0;
    z-index: 1000;
    padding:15px;
    background:#111;
}

/* CUSTOMER BAR */
.custs {
    position: sticky;
    top: 60px;
    z-index: 999;

    display:flex;
    flex-wrap: nowrap;       /* 🔥 no wrap */
    overflow-x: auto;
    gap:10px;
    padding:10px;

    background:#1a1a1a;
}

/* CHIP */
.cust {
    flex: 0 0 auto;          /* 🔥 force single line */
    padding:10px 15px;
    background:#333;
    border-radius:20px;
    text-decoration:none;
    color:white;
    white-space: nowrap;
}

/* MESSAGE */
.msg {
    margin:15px;
    padding:15px;
    background:#222;
    border-radius:15px;
}

/* AUDIO */
audio {
    width:100%;
    margin-top:10px;
}

</style>
</head>

<body>

<div class="header">
    📞 rahul jnb 1 |
    <a href="/logout" style="color:#00e5c3;">Logout</a>

    <form method="GET" style="display:inline;">
        <input type="hidden" name="customer" value="{{request.args.get('customer','')}}">
        <input type="date" name="date" onchange="this.form.submit()">
    </form>
</div>

<div class="custs">
    <a class="cust" href="/">All</a>
    {% for c in customers %}
        <a class="cust" href="/?customer={{c}}">{{c}}</a>
    {% endfor %}
</div>

{% for f in files %}
<div class="msg">
    <b>{{f.clean_name}}</b><br>
    {{f.dt}}

    <audio controls preload="none">
        <source src="/stream/{{f.id}}" type="audio/mp4">
    </audio>
</div>
{% endfor %}

<script>
document.body.addEventListener("play", function(e) {
    if (e.target.tagName === "AUDIO") {
        document.querySelectorAll("audio").forEach(a => {
            if (a !== e.target) {
                a.pause();
                a.currentTime = 0;
            }
        });
    }
}, true);
</script>

</body>
</html>
""", files=files, customers=customers)
