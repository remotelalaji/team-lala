# (Python part same as before — only HTML/CSS updated)

return render_template_string("""
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>

/* ===== BACKGROUND ===== */
body {
    margin:0;
    font-family:sans-serif;
    color:white;
    background: linear-gradient(135deg,#0f2027,#203a43,#2c5364);
}

/* ===== HEADER ===== */
.header {
    position: sticky;
    top: 0;
    z-index:1000;
    padding:12px;
    backdrop-filter: blur(15px);
    background: rgba(255,255,255,0.05);
    border-bottom:1px solid rgba(255,255,255,0.1);
}

/* ===== CUSTOMER BAR ===== */
.custs {
    position: sticky;
    top: 55px;
    z-index:999;
    display:flex;
    overflow-x:auto;
    gap:8px;
    padding:10px;
}

/* ===== GLASS CHIP ===== */
.cust {
    flex:0 0 auto;
    padding:8px 14px;
    border-radius:20px;
    text-decoration:none;
    color:white;
    font-size:13px;

    background: rgba(255,255,255,0.1);
    backdrop-filter: blur(10px);
    border:1px solid rgba(255,255,255,0.2);
}

/* ===== GLASS CARD ===== */
.msg {
    margin:12px;
    padding:12px;
    border-radius:15px;

    background: rgba(255,255,255,0.08);
    backdrop-filter: blur(15px);
    border:1px solid rgba(255,255,255,0.15);
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}

/* TEXT */
.msg b {
    font-size:15px;
    font-weight:600;
}

.msg small {
    color:#ccc;
}

/* AUDIO */
audio {
    width:100%;
    margin-top:8px;
    height:34px;
}

/* DATE INPUT */
input[type="date"] {
    background:rgba(255,255,255,0.1);
    border:none;
    color:white;
    padding:6px;
    border-radius:6px;
}

/* SCROLL BAR (optional nice look) */
::-webkit-scrollbar {
    height:5px;
}
::-webkit-scrollbar-thumb {
    background:#888;
    border-radius:10px;
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
        <a class="cust" href="/?customer={{c | urlencode}}">{{c}}</a>
    {% endfor %}
</div>

{% for f in files %}
<div class="msg">
    <b>{{f.clean_name}}</b><br>
    <small>{{f.dt}}</small>

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
