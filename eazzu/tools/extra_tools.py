"""Additional utility tools for the Eazzu platform.

Pure-Python implementations using only the standard library. Each tool is
exposed via the ``TOOLS`` list at the bottom of the module.
"""
import base64, csv, hashlib, io, json, random, re, string, urllib.parse, uuid
from datetime import datetime, timezone, timedelta

def _ok(**kw):
    kw["status"] = "ok"; return kw

def _qr_matrix(text):
    rng = random.Random(sum(ord(c) for c in text) or 1)
    size = 21
    m = [[rng.randint(0, 1) for _ in range(size)] for _ in range(size)]
    for r in range(7):
        for c in range(7):
            on = r in (0, 6) or c in (0, 6) or (2 <= r <= 4 and 2 <= c <= 4)
            m[r][c] = m[r][size-1-c] = m[size-1-r][c] = 1 if on else 0
    return m

def _barcode(text):
    out = []
    for ch in text:
        for shift in (7, 5, 3, 1):
            out.append("█" if (ord(ch) >> shift) & 1 else " ")
        out.append(" ")
    return "".join(out)

def _password(length, upper, lower, nums, syms):
    pools = ([string.ascii_uppercase] if upper else []) + ([string.ascii_lowercase] if lower else []) + ([string.digits] if nums else []) + (["!@#$%^&*()-_=+[]{};:,.<>?/"] if syms else [])
    if not pools: pools = [string.ascii_letters]
    rng = random.SystemRandom()
    all_chars = "".join(pools)
    chars = [rng.choice(p) for p in pools] + [rng.choice(all_chars) for _ in range(max(0, length - len(pools)))]
    rng.shuffle(chars); return "".join(chars[:length])

def _hash(text, algo):
    data = text.encode("utf-8")
    return {"md5": hashlib.md5, "sha256": hashlib.sha256, "sha512": hashlib.sha512}[algo](data).hexdigest()

def _b64(text, mode):
    return base64.b64encode(text.encode()) if mode == "encode" else base64.b64decode(text.encode()).decode()

def _url_codec(text, mode):
    return urllib.parse.quote(text) if mode == "encode" else urllib.parse.unquote(text)

def _csv_to_json(csv_str):
    return json.dumps([row for row in csv.DictReader(io.StringIO(csv_str))])

def _json_to_csv(json_str):
    data = json.loads(json_str)
    if not isinstance(data, list) or not data: return ""
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=list(data[0].keys())); w.writeheader(); w.writerows(data)
    return out.getvalue().strip()

def _md_to_html(md):
    lines, html, in_list = md.splitlines(), [], False
    for line in lines:
        if re.match(r"^#{1,6} ", line):
            lvl = len(line.split(" ", 1)[0]); html.append(f"<h{lvl}>{line[lvl+1:]}</h{lvl}>")
        elif re.match(r"^[-*] ", line):
            if not in_list: html.append("<ul>"); in_list = True
            html.append(f"<li>{line[2:]}</li>")
        else:
            if in_list: html.append("</ul>"); in_list = False
            if line.strip(): html.append(f"<p>{line}</p>")
    if in_list: html.append("</ul>")
    return "\n".join(html)

def _html_to_md(html):
    html = re.sub(r"<h1>(.*?)</h1>", r"# \1", html)
    html = re.sub(r"<h2>(.*?)</h2>", r"## \1", html)
    html = re.sub(r"<h3>(.*?)</h3>", r"### \1", html)
    html = re.sub(r"<li>(.*?)</li>", r"- \1", html)
    html = re.sub(r"<p>(.*?)</p>", r"\1\n", html)
    return re.sub(r"<[^>]+>", "", html).strip()

def _color_picker(color):
    color = color.strip()
    if color.startswith("#"):
        h = color[1:]
        if len(h) == 3: h = "".join(c*2 for c in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    elif color.lower().startswith("rgb"):
        r, g, b = (int(n) for n in re.findall(r"\d+", color)[:3])
    else:
        names = {"red": (255,0,0), "green": (0,128,0), "blue": (0,0,255), "white": (255,255,255), "black": (0,0,0)}
        r, g, b = names[color.lower()]
    return {"r": r, "g": g, "b": b, "hex": f"#{r:02x}{g:02x}{b:02x}"}

LOREM = ("lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod "
         "tempor incididunt ut labore et dolore magna aliqua ut enim ad minim veniam "
         "quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo")

def _lorem(paragraphs):
    words = LOREM.split(); out = []
    for _ in range(paragraphs):
        out.append(" ".join(random.sample(words, min(20, len(words)))).capitalize() + ".")
    return " ".join(out)

def _world_clock(tz_name):
    offsets = {"UTC": 0, "EST": -5, "PST": -8, "IST": 5.5, "CET": 1, "JST": 9}
    now = datetime.now(timezone.utc) + timedelta(hours=offsets.get(tz_name.upper(), 0))
    return now.strftime("%Y-%m-%d %H:%M:%S")

def _unit_convert(value, from_u, to_u):
    length = {"m":1,"km":1000,"cm":0.01,"mm":0.001,"ft":0.3048,"in":0.0254,"mi":1609.34}
    weight = {"g":1,"kg":1000,"mg":0.001,"lb":453.592,"oz":28.3495}
    if from_u in length and to_u in length: return value * length[from_u] / length[to_u]
    if from_u in weight and to_u in weight: return value * weight[from_u] / weight[to_u]
    if from_u in "cfk" and to_u in "cfk":
        c = value if from_u == "c" else (value - 32) * 5/9 if from_u == "f" else value - 273.15
        return c if to_u == "c" else c * 9/5 + 32 if to_u == "f" else c + 273.15
    raise ValueError("unsupported units")

def _mortgage(principal, rate, years):
    r = rate / 100 / 12; n = years * 12
    return principal / n if r == 0 else principal * r * (1+r)**n / ((1+r)**n - 1)

def _bmi(weight, height): return round(weight / (height ** 2), 2)

def _tip(bill, percent, split):
    tip = bill * percent / 100; total = bill + tip
    return {"tip": round(tip, 2), "total": round(total, 2), "per_person": round(total / (split or 1), 2)}

def _text_diff(t1, t2):
    a, b, out = t1.splitlines(), t2.splitlines(), []
    for i in range(max(len(a), len(b))):
        la = a[i] if i < len(a) else "<none>"; lb = b[i] if i < len(b) else "<none>"
        if la != lb: out.append(f"- {la}"); out.append(f"+ {lb}")
    return "\n".join(out) or "identical"

def _text_stats(text):
    return {"words": len(text.split()), "chars": len(text), "sentences": max(1, len(re.findall(r"[.!?]+", text)))}

def _slug(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-"); return s or "n-a"

def _cron_desc(cron):
    p = cron.split()
    if len(p) != 5: return "invalid cron"
    return f"Minute {p[0]}, Hour {p[1]}, Day-of-month {p[2]}, Month {p[3]}, Day-of-week {p[4]}"

_MORSE = {"A":".-","B":"-...","C":"-.-.","D":"-..","E":".","F":"..-.","G":"--.","H":"....","I":"..","J":".---","K":"-.-","L":".-..","M":"--","N":"-.","O":"---","P":".--.","Q":"--.-","R":".-.","S":"...","T":"-","U":"..-","V":"...-","W":".--","X":"-..-","Y":"-.--","Z":"--..","0":"-----","1":".----","2":"..---","3":"...--","4":"....-","5":".....","6":"-....","7":"--...","8":"---..","9":"----."}

def _morse(text, mode):
    if mode == "encode":
        return " ".join(_MORSE.get(c.upper(), "") for c in text if c.upper() in _MORSE)
    rev = {v: k for k, v in _MORSE.items()}; return "".join(rev.get(w, "") for w in text.split())

_FONT = {"A":[" ### ","#   #","#####","#   #","#   #"],"B":["#### ","#   #","#### ","#   #","#### "],"C":[" ### ","#    ","#    ","#    "," ### "],"D":["#### ","#   #","#   #","#   #","#### "],"E":["#####","#    ","#### ","#    ","#####"],"F":["#####","#    ","#### ","#    ","#    "],"G":[" ### ","#    ","#  ##","#   #"," ### "],"H":["#   #","#   #","#####","#   #","#   #"],"I":["#####","  #  ","  #  ","  #  ","#####"],"L":["#    ","#    ","#    ","#    ","#####"],"N":["#   #","##  #","# # #","#  ##","#   #"],"O":[" ### ","#   #","#   #","#   #"," ### "],"R":["#### ","#   #","#### ","# #  ","#  ##"],"S":[" ####","#    "," ### ","    #","#### "],"T":["#####","  #  ","  #  ","  #  ","  #  "],"U":["#   #","#   #","#   #","#   #"," ### "]}

def _ascii_art(text):
    rows = [""] * 5
    for ch in text.upper():
        g = _FONT.get(ch, ["  ?  "] * 5)
        for i in range(5): rows[i] += g[i] + " "
    return "\n".join(rows)

def _binary(text, mode):
    return " ".join(f"{ord(c):08b}" for c in text) if mode == "encode" else "".join(chr(int(b, 2)) for b in text.split())

def _rot13(text):
    t = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm")
    return text.translate(t)

TOOLS: list[dict] = [
    {"name": "extra_qr_generator", "description": "Generate a QR-like ASCII matrix from text", "params": {"text": "str"}, "run": lambda a: _ok(matrix=_qr_matrix(a["text"]))},
    {"name": "extra_barcode_gen", "description": "Generate a simple barcode pattern from text", "params": {"text": "str"}, "run": lambda a: _ok(barcode=_barcode(a["text"]))},
    {"name": "extra_password_gen", "description": "Generate a random password", "params": {"length": "int", "uppercase": "bool", "lowercase": "bool", "numbers": "bool", "symbols": "bool"}, "run": lambda a: _ok(password=_password(int(a.get("length", 12)), a.get("uppercase", True), a.get("lowercase", True), a.get("numbers", True), a.get("symbols", False)))},
    {"name": "extra_uuid_gen", "description": "Generate a UUID (version 1 or 4)", "params": {"version": "int"}, "run": lambda a: _ok(uuid=str(uuid.uuid1() if int(a.get("version", 4)) == 1 else uuid.uuid4()))},
    {"name": "extra_hash_compute", "description": "Compute hash of text", "params": {"text": "str", "algorithm": "str"}, "run": lambda a: _ok(hash=_hash(a["text"], a.get("algorithm", "sha256")))},
    {"name": "extra_base64_codec", "description": "Encode/decode base64", "params": {"text": "str", "mode": "str"}, "run": lambda a: _ok(result=_b64(a["text"], a.get("mode", "encode")))},
    {"name": "extra_url_codec", "description": "Encode/decode URL", "params": {"text": "str", "mode": "str"}, "run": lambda a: _ok(result=_url_codec(a["text"], a.get("mode", "encode")))},
    {"name": "extra_json_formatter", "description": "Format/pretty-print JSON", "params": {"json_str": "str", "indent": "int"}, "run": lambda a: _ok(result=json.dumps(json.loads(a["json_str"]), indent=int(a.get("indent", 2))))},
    {"name": "extra_csv_to_json", "description": "Convert CSV string to JSON", "params": {"csv_str": "str"}, "run": lambda a: _ok(result=_csv_to_json(a["csv_str"]))},
    {"name": "extra_json_to_csv", "description": "Convert JSON to CSV", "params": {"json_str": "str"}, "run": lambda a: _ok(result=_json_to_csv(a["json_str"]))},
    {"name": "extra_markdown_to_html", "description": "Basic markdown to HTML", "params": {"markdown": "str"}, "run": lambda a: _ok(html=_md_to_html(a["markdown"]))},
    {"name": "extra_html_to_markdown", "description": "Basic HTML to markdown", "params": {"html": "str"}, "run": lambda a: _ok(markdown=_html_to_md(a["html"]))},
    {"name": "extra_color_picker", "description": "Parse/validate a color, return RGB+HEX", "params": {"color": "str"}, "run": lambda a: _ok(**_color_picker(a["color"]))},
    {"name": "extra_lorem_ipsum", "description": "Generate lorem ipsum text", "params": {"paragraphs": "int"}, "run": lambda a: _ok(text=_lorem(int(a.get("paragraphs", 3))))},
    {"name": "extra_chronometer", "description": "Return elapsed seconds (stopwatch simulation)", "params": {"seconds": "float"}, "run": lambda a: _ok(elapsed_seconds=float(a.get("seconds", 0)))},
    {"name": "extra_world_clock", "description": "Return time in common timezones", "params": {"timezone": "str"}, "run": lambda a: _ok(time=_world_clock(a.get("timezone", "UTC")))},
    {"name": "extra_unit_converter", "description": "Convert units (temperature, length, weight)", "params": {"value": "float", "from_unit": "str", "to_unit": "str"}, "run": lambda a: _ok(result=round(_unit_convert(float(a["value"]), a["from_unit"], a["to_unit"]), 6))},
    {"name": "extra_mortgage_calc", "description": "Calculate monthly mortgage payment", "params": {"principal": "float", "rate": "float", "years": "int"}, "run": lambda a: _ok(monthly_payment=round(_mortgage(float(a["principal"]), float(a.get("rate", 0)), int(a["years"])), 2))},
    {"name": "extra_bmi_calc", "description": "Calculate BMI", "params": {"weight_kg": "float", "height_m": "float"}, "run": lambda a: _ok(bmi=_bmi(float(a["weight_kg"]), float(a["height_m"])))},
    {"name": "extra_tip_calc", "description": "Calculate tip", "params": {"bill": "float", "tip_percent": "float", "split": "int"}, "run": lambda a: _ok(**_tip(float(a["bill"]), float(a.get("tip_percent", 15)), int(a.get("split", 1))))},
    {"name": "extra_random_picker", "description": "Pick random item(s) from a list", "params": {"items": "list", "count": "int"}, "run": lambda a: _ok(picked=random.sample(a["items"], min(int(a.get("count", 1)), len(a["items"]))))},
    {"name": "extra_text_diff", "description": "Line-by-line diff of two texts", "params": {"text1": "str", "text2": "str"}, "run": lambda a: _ok(diff=_text_diff(a["text1"], a["text2"]))},
    {"name": "extra_text_stats", "description": "Word/char/sentence count", "params": {"text": "str"}, "run": lambda a: _ok(**_text_stats(a["text"]))},
    {"name": "extra_slug_gen", "description": "Generate URL slug from text", "params": {"text": "str"}, "run": lambda a: _ok(slug=_slug(a["text"]))},
    {"name": "extra_cron_parser", "description": "Parse cron expression to description", "params": {"cron": "str"}, "run": lambda a: _ok(description=_cron_desc(a["cron"]))},
    {"name": "extra_regex_tester", "description": "Test regex against text", "params": {"pattern": "str", "text": "str"}, "run": lambda a: _ok(matches=re.findall(a["pattern"], a["text"]))},
    {"name": "extra_cron_to_natural", "description": "Convert cron to natural language", "params": {"cron": "str"}, "run": lambda a: _ok(text="Runs " + _cron_desc(a["cron"]).lower())},
    {"name": "extra_ascii_art", "description": "Convert text to ASCII art banner", "params": {"text": "str"}, "run": lambda a: _ok(art=_ascii_art(a["text"]))},
    {"name": "extra_morse_code", "description": "Encode/decode morse code", "params": {"text": "str", "mode": "str"}, "run": lambda a: _ok(result=_morse(a["text"], a.get("mode", "encode")))},
    {"name": "extra_rot13", "description": "Apply ROT13", "params": {"text": "str"}, "run": lambda a: _ok(result=_rot13(a["text"]))},
    {"name": "extra_binary_codec", "description": "Encode/decode binary", "params": {"text": "str", "mode": "str"}, "run": lambda a: _ok(result=_binary(a["text"], a.get("mode", "encode")))},
]