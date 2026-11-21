# -*- coding: utf-8 -*-
import sys
import json
import math
import random
import urllib.request
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtPrintSupport import QPrinter, QPrintDialog

try:
    from PySide6.QtMultimedia import QSoundEffect
    HAS_SOUND = True
except ImportError:
    HAS_SOUND = False

try:
    from PIL import Image, ImageDraw, ImageFont
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

from supabase import create_client

# ═══════════════════════════════════════════════════════════
# الإعدادات
# ═══════════════════════════════════════════════════════════
SUPABASE_URL = "https://ewivzdrrujuwhkuqqgei.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV3aXZ6ZHJydWp1d2hrdXFxZ2VpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk1OTMwNDQsImV4cCI6MjEwNTE2OTA0NH0.ng8N-08Pl2SOr42Dw01fLSG6n8C17BNTG5XDVPdisM8"
client = create_client(SUPABASE_URL, SUPABASE_KEY)

REFRESH_INTERVAL     = 15_000
MAX_REQUESTS         = 300
MAX_ARCHIVED         = 500
PROCESSOR_NAME       = "قسم التسجيل"
PRESIDENT_SERVICE    = "S010"
NEW_THRESHOLD_MIN    = 5
URGENT_THRESHOLD_MIN = 30
SIDEBAR_WIDTH        = 250
DELETE_PASSWORD      = "1234"

ARCHIVED_STATUSES = ("delivered", "rejected")
PAPER_SERVICES = {"S009"}

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

SOUND_FILE = BASE_DIR / "notification.wav"
SETTINGS_FILE = BASE_DIR / "settings.json"
TEMPLATE_A4 = BASE_DIR / "template.png"
TEMPLATE_A5 = BASE_DIR / "template_A5.png"
TEMPLATE_MEDICAL = BASE_DIR / "template_medical.png"

LETTER_SERVICES_PATTERNS = {"استمرار": "A4", "مباشرة": "A5", "مراجعة": "MEDICAL", "إحالة": "MEDICAL"}

def get_letter_type(req):
    name = req.get('service_name', '') or ''
    for keyword, tmpl_type in LETTER_SERVICES_PATTERNS.items():
        if keyword in name: return tmpl_type
    return None

DEFAULT_SETTINGS = {
    "fixed_subject":  "م/ تأييد استمرارية بالدراسة",
    "fixed_greeting": "تحية طيبة ....",
    "fixed_thanks":   "مع التقدير ....",
    "stamp_right":    "قسم التسجيل",
    "stamp_left":     "الحسابات",
    "sign_name":      "أ.د منير حميد السعدي",
    "sign_title":     "رئيس الجامعة",
    "theme":          "dark",
}

def load_settings():
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            merged = DEFAULT_SETTINGS.copy()
            merged.update(data)
            return merged
        except: pass
    return DEFAULT_SETTINGS.copy()

def save_settings(data):
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except: return False

SETTINGS = load_settings()

THEMES = {
    "dark": {
        "bg_grad_top": "#0b1220", "bg_grad_bottom": "#111c2e",
        "surface": "rgba(30, 41, 59, 0.35)", "surface_hover": "rgba(30, 41, 59, 0.55)",
        "surface_soft": "rgba(255, 255, 255, 0.03)", "border": "rgba(255, 255, 255, 0.06)",
        "border_soft": "rgba(255, 255, 255, 0.04)", "border_hover": "rgba(56, 189, 248, 0.25)",
        "accent": "#38bdf8", "accent_soft": "rgba(56, 189, 248, 0.15)",
        "text_primary": "#f1f5f9", "text_secondary": "#e2e8f0", "text_muted": "#94a3b8", "text_dim": "#64748b",
    },
    "light": {
        "bg_grad_top": "#eef3f9", "bg_grad_bottom": "#dbe4f0",
        "surface": "rgba(255, 255, 255, 0.85)", "surface_hover": "rgba(255, 255, 255, 0.95)",
        "surface_soft": "rgba(0, 0, 0, 0.04)", "border": "rgba(15, 23, 42, 0.10)",
        "border_soft": "rgba(15, 23, 42, 0.06)", "border_hover": "rgba(56, 189, 248, 0.55)",
        "accent": "#0284c7", "accent_soft": "rgba(56, 189, 248, 0.18)",
        "text_primary": "#0f172a", "text_secondary": "#1e293b", "text_muted": "#475569", "text_dim": "#94a3b8",
    },
}

def get_colors():
    return THEMES.get(SETTINGS.get("theme", "dark"), THEMES["dark"]).copy()

COLORS = get_colors()

STATUS_MAP = {
    "pending":   {"text": "قيد المراجعة", "color": "#d97706"},
    "approved":  {"text": "موافق",        "color": "#2563eb"},
    "rejected":  {"text": "مرفوض",        "color": "#dc2626"},
    "ready":     {"text": "جاهز",         "color": "#059669"},
    "delivered": {"text": "تم التسليم",   "color": "#64748b"},
}

SERVICE_ICONS = {"S001": "📄", "S002": "📧", "S003": "🎓", "S004": "🪪", "S005": "⏸️", "S006": "🏥", "S007": "🔄", "S008": "📱", "S009": "⏰", "S010": "🏛️", "S011": "📖", "S012": "🎓", "S013": "🏥"}

POSITIONS_A4 = {
    "number": {"x": 92.0, "y": 19.3, "size": 1.50, "align": "right"}, "date": {"x": 92.0, "y": 21.6, "size": 1.50, "align": "right"},
    "photo": {"x": 8.6, "y": 20.0, "w": 14.4, "h": 10.5}, "to": {"x": 50.0, "y": 28.7, "size": 1.55, "align": "center"},
    "subject": {"x": 50.0, "y": 31.1, "size": 1.55, "align": "center"}, "greeting": {"x": 92.0, "y": 35.2, "size": 1.55, "align": "right"},
    "body": {"x": 5.0, "y": 38.5, "w": 90.0, "size": 1.35, "line_h": 1.9}, "thanks": {"x": 50.0, "y": 49.7, "size": 1.55, "align": "center"},
    "sign_name": {"x": 32.0, "y": 60.4, "size": 1.55, "align": "center"}, "sign_title": {"x": 32.0, "y": 62.8, "size": 1.55, "align": "center"},
    "sign_date": {"x": 32.0, "y": 65.4, "size": 1.45, "align": "center"}, "copy_to": {"x": 92.0, "y": 70.4, "size": 1.45, "align": "right"},
    "copy_1": {"x": 90.0, "y": 72.4, "size": 1.40, "align": "right"}, "copy_2": {"x": 90.0, "y": 74.6, "size": 1.40, "align": "right"},
}

POSITIONS_A5 = {
    "photo":       {"x": 7.5,  "y": 34.0, "w": 19.0, "h": 23.0},  # ✅ إنزال الصورة للأسفل
    "subject":     {"x": 50.0, "y": 50.0, "size": 1.80, "align": "center"}, # ✅ إنزال الموضوع
    "body":        {"x": 7.5,  "y": 61.0, "w": 85.0, "size": 1.50, "line_h": 1.9}, # ✅ إنزال النص
    "stamp_right": {"x": 80.0, "y": 87.0, "size": 1.60, "align": "center"},
    "stamp_left":  {"x": 20.0, "y": 87.0, "size": 1.60, "align": "center"},
}
POSITIONS_MEDICAL = {
    "univ_name": {"x": 89.0, "y": 20.5, "size": 1.50, "align": "right"}, "health_center": {"x": 55.0, "y": 20.5, "size": 1.50, "align": "right"},
    "student_name": {"x": 89.0, "y": 24.7, "size": 1.50, "align": "right"}, "age": {"x": 30.0, "y": 24.7, "size": 1.50, "align": "right"},
    "stage_line": {"x": 89.0, "y": 28.9, "size": 1.50, "align": "right"},
}

def F(size, bold=True): f = QFont("Segoe UI", size); f.setBold(bold); return f
def parse_ts(ts):
    if not ts: return None
    try: return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except: return None

def time_ago(ts):
    dt = parse_ts(ts)
    if not dt: return ""
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    d = (now - dt).total_seconds()
    if d < 60: return "الآن"
    if d < 3600: return f"منذ {int(d//60)} د"
    if d < 86400: return f"منذ {int(d//3600)} س"
    return f"منذ {int(d//86400)} ي"

def age_min(ts):
    dt = parse_ts(ts)
    if not dt: return 99999
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    return (now - dt).total_seconds() / 60

def is_paper(sid): return sid in PAPER_SERVICES
def is_president(sid): return sid == PRESIDENT_SERVICE
def is_new(req): return age_min(req.get('timestamp', '')) < NEW_THRESHOLD_MIN

def get_request_type(req):
    if req.get('service_id') != PRESIDENT_SERVICE: return None
    try:
        fd = json.loads(req.get('form_data', '{}') or '{}')
        for k, v in fd.items():
            if k.startswith('select:') and v in ('طالب منتسب', 'قبول جديد'): return v
    except: pass
    return 'طالب منتسب' if req.get('reg_id') else 'قبول جديد'

def get_study_type(req):
    st = req.get('_study_type')
    if st: return st
    try:
        fd = json.loads(req.get('form_data', '{}') or '{}')
        st = fd.get('_نوع_الدراسة') or fd.get('نوع الدراسة')
        if st: return st
    except: pass
    return '-'

def get_stage(req):
    st = req.get('_stage')
    if st: return st
    try:
        fd = json.loads(req.get('form_data', '{}') or '{}')
        st = fd.get('_المرحلة')
        if st: return st
    except: pass
    return req.get('stage', '-') or '-'

def urgency(req):
    if req.get('status') != 'pending': return 0
    m = age_min(req.get('timestamp', ''))
    if m > 120: return 3
    if m > 60: return 2
    if m > URGENT_THRESHOLD_MIN: return 1
    return 0

def priority(req):
    st = req.get('status', 'pending')
    weight = {'pending': 1000, 'approved': 500, 'ready': 300, 'rejected': 100, 'delivered': 0}.get(st, 0)
    dt = parse_ts(req.get('timestamp', ''))
    ts_val = dt.timestamp() if dt else 0
    return (weight * 10000000000) + ts_val

def is_archived(req): return req.get('status') in ARCHIVED_STATUSES
def extract_image_name(image_url):
    if not image_url: return None
    try: return image_url.split('/')[-1].split('?')[0]
    except: return None

def delete_image_from_storage(image_name):
    if not image_name: return True
    try:
        client.storage.from_('request-images').remove([image_name])
        return True
    except: return False

def esc(text):
    if text is None: return "-"
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def _ar(t): return get_display(arabic_reshaper.reshape(str(t))) if HAS_PILLOW and t else ""
def _load_font(size):
    for p in [Path("C:/Windows/Fonts/majalla.ttf"), Path("C:/Windows/Fonts/trado.ttf"), Path("C:/Windows/Fonts/tahoma.ttf")]:
        if p.exists():
            try: return ImageFont.truetype(str(p), size)
            except: pass
    return ImageFont.load_default()

def _meas(draw, text, font):
    b = draw.textbbox((0, 0), text, font=font); return b[2] - b[0], b[3] - b[1]

def _wrap(draw, text, font, max_w):
    words = text.split(); lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if _meas(draw, _ar(t), font)[0] <= max_w: cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def _draw(draw, text, x, y, font, color, align):
    r = _ar(text); w, _ = _meas(draw, r, font)
    px = x - w if align == "right" else (x - w // 2 if align == "center" else x)
    draw.text((px, y), r, font=font, fill=color)

def detect_template_type(req): return get_letter_type(req) or 'A4'

def generate_a4(data, photo_path=None, base_font_size=35):
    if not HAS_PILLOW or not TEMPLATE_A4.exists(): return None
    img = Image.open(TEMPLATE_A4).convert("RGB"); W, H = img.size; draw = ImageDraw.Draw(img)
    def px_x(p): return int(W * p / 100)
    def px_y(p): return int(H * p / 100)
    def fs(p): return max(10, int(base_font_size * (p / 1.5) * (H / 1800)))
    pcfg = POSITIONS_A4["photo"]
    if photo_path and Path(photo_path).exists():
        try:
            p = Image.open(photo_path).convert("RGB").resize((px_x(pcfg["w"]), px_y(pcfg["h"])), Image.LANCZOS)
            fr = Image.new("RGB", (px_x(pcfg["w"]) + 4, px_y(pcfg["h"]) + 4), "white"); fr.paste(p, (2, 2))
            img.paste(fr, (px_x(pcfg["x"]), px_y(pcfg["y"]))); draw = ImageDraw.Draw(img)
        except: pass
    def put(key, val):
        cfg = POSITIONS_A4[key]; _draw(draw, val, px_x(cfg["x"]), px_y(cfg["y"]), _load_font(fs(cfg["size"])), "#000000", cfg.get("align", "right"))
    put("number", data.get("number", "")); put("date", data.get("date", "")); put("to", data.get("to_text", "إلى /"))
    put("subject", SETTINGS.get("fixed_subject", "")); put("greeting", SETTINGS.get("fixed_greeting", ""))
    put("thanks", SETTINGS.get("fixed_thanks", "")); put("copy_to", data.get("copy_to_text", ""))
    put("copy_1", data.get("copy_1_text", "")); put("copy_2", data.get("copy_2_text", ""))
    bcfg = POSITIONS_A4["body"]; bf = _load_font(fs(bcfg["size"])); lines = _wrap(draw, data.get("body_text", ""), bf, int(W * bcfg["w"] / 100))
    y0 = px_y(bcfg["y"]); line_h = int(fs(bcfg["size"]) * bcfg["line_h"])
    for i, line in enumerate(lines):
        r = _ar(line); w, _ = _meas(draw, r, bf); draw.text((px_x(95) - w, y0 + i * line_h), r, font=bf, fill="#000000")
    sig_lines = [ln.strip() for ln in data.get("signature_text", "").split("\n") if ln.strip()]
    for i, line in enumerate(sig_lines[:3]):
        cfg = POSITIONS_A4[["sign_name", "sign_title", "sign_date"][i]]
        _draw(draw, line, px_x(cfg["x"]), px_y(cfg["y"]), _load_font(fs(cfg["size"])), "#000000", cfg.get("align", "center"))
    return img

def generate_a5(data, photo_path=None, base_font_size=35):
    if not HAS_PILLOW or not TEMPLATE_A5.exists(): return None
    img = Image.open(TEMPLATE_A5).convert("RGB"); W, H = img.size; draw = ImageDraw.Draw(img)
    def px_x(p): return int(W * p / 100)
    def px_y(p): return int(H * p / 100)
    def fs(p): return max(10, int(base_font_size * (p / 1.5) * (H / 1200)))
    pcfg = POSITIONS_A5["photo"]
    if photo_path and Path(photo_path).exists():
        try:
            p = Image.open(photo_path).convert("RGB").resize((px_x(pcfg["w"]), px_y(pcfg["h"])), Image.LANCZOS)
            fr = Image.new("RGB", (px_x(pcfg["w"]) + 4, px_y(pcfg["h"]) + 4), "white"); fr.paste(p, (2, 2))
            img.paste(fr, (px_x(pcfg["x"]), px_y(pcfg["y"]))); draw = ImageDraw.Draw(img)
        except: pass
    subj = POSITIONS_A5["subject"]; _draw(draw, "م/ مباشرة طالب", px_x(subj["x"]), px_y(subj["y"]), _load_font(fs(subj["size"])), "#000000", "center")
    bcfg = POSITIONS_A5["body"]; bf = _load_font(fs(bcfg["size"])); lines = _wrap(draw, data.get("body_text", ""), bf, int(W * bcfg["w"] / 100))
    y0 = px_y(bcfg["y"]); line_h = int(fs(bcfg["size"]) * bcfg["line_h"])
    for i, line in enumerate(lines):
        r = _ar(line); w, _ = _meas(draw, r, bf); draw.text((px_x(92.5) - w, y0 + i * line_h), r, font=bf, fill="#000000")
    sr = POSITIONS_A5["stamp_right"]; _draw(draw, data.get("stamp_right", SETTINGS.get("stamp_right", "")), px_x(sr["x"]), px_y(sr["y"]), _load_font(fs(sr["size"])), "#000000", "center")
    sl = POSITIONS_A5["stamp_left"]; _draw(draw, data.get("stamp_left", SETTINGS.get("stamp_left", "")), px_x(sl["x"]), px_y(sl["y"]), _load_font(fs(sl["size"])), "#000000", "center")
    return img

def generate_medical(data, photo_path=None, base_font_size=35):
    if not HAS_PILLOW or not TEMPLATE_MEDICAL.exists(): return None
    img = Image.open(TEMPLATE_MEDICAL).convert("RGB"); W, H = img.size; draw = ImageDraw.Draw(img)
    def px_x(p): return int(W * p / 100)
    def px_y(p): return int(H * p / 100)
    def fs(p): return max(10, int(base_font_size * (p / 1.5) * (H / 1800)))
    def put(key, val):
        val = (val or "").strip()
        if not val: return
        cfg = POSITIONS_MEDICAL[key]; _draw(draw, val, px_x(cfg["x"]), px_y(cfg["y"]), _load_font(fs(cfg["size"])), "#000000", cfg.get("align", "right"))
    put("univ_name", "اسم الجامعة: جامعة الناجي الأهلية")
    if data.get("health_center"): put("health_center", f"اسم المركز الصحي المحال اليه: {data['health_center']}")
    if data.get("name"): put("student_name", f"اسم الطالب الثلاثي: {data['name']}")
    if data.get("age"): put("age", f"العمر: {data['age']}")
    if data.get("stage_line"): put("stage_line", f"المرحلة الدراسية: {data['stage_line']}")
    return img

def generate_letter_image(data, photo_path=None, base_font_size=35, template_type='A4'):
    if template_type == 'A5': return generate_a5(data, photo_path, base_font_size)
    if template_type == 'MEDICAL': return generate_medical(data, photo_path, base_font_size)
    return generate_a4(data, photo_path, base_font_size)

def full_datetime(ts):
    dt = parse_ts(ts); return dt.strftime("%Y/%m/%d — %H:%M") if dt else "-"

def build_print_html(requests, service_name="طلب", service_id=""):
    now = datetime.now().strftime("%Y/%m/%d — %H:%M")
    html = f"""<!DOCTYPE html><html dir="rtl"><head><meta charset="utf-8"><style>
    @page {{ size: A4; margin: 12mm; }} body {{ font-family: 'Segoe UI', sans-serif; direction: rtl; color: #1f2937; font-size: 10pt; line-height: 1.35; }}
    .req {{ page-break-inside: avoid; }} .header {{ background-color: #fbbf24; color: #0f172a; padding: 10px 16px; border: 2px solid #b45309; border-radius: 6px; margin-bottom: 8px; }}
    .uni-name {{ font-size: 15pt; font-weight: bold; }} .meta {{ color: #475569; font-size: 9pt; padding: 6px 8px; margin-bottom: 8px; border: 1.5px solid #fbbf24; border-radius: 6px; background-color: #fffbeb; }}
    .info-table {{ width: 100%; border-collapse: collapse; margin-bottom: 8px; }} .info-table td {{ padding: 5px 10px; vertical-align: top; font-size: 10pt; border: 1px solid #cbd5e1; }}
    .info-table td.value {{ color: #1f2937; width: 72%; background-color: #ffffff; }} .info-table td.label {{ font-weight: bold; color: #334155; width: 28%; background-color: #fef3c7; }}
    .opinion-box {{ margin-top: 8px; border: 2px solid #b45309; border-radius: 6px; padding: 8px 12px; background-color: #fffbeb; min-height: 42mm; }}
    .opinion-title {{ font-size: 12pt; font-weight: bold; color: #78350f; border-bottom: 2px solid #fbbf24; padding-bottom: 5px; margin-bottom: 6px; }}
    .opinion-space {{ height: 35mm; }} .footer {{ font-size: 8pt; color: #94a3b8; text-align: center; margin-top: 8px; padding-top: 4px; border-top: 1px solid #e2e8f0; }}
    </style></head><body>"""
    for idx, req in enumerate(requests):
        try: fd = json.loads(req.get('form_data', '{}') or '{}')
        except: fd = {}
        rows_html = ""
        if req.get('reg_id'):
            rows_html += f'<tr><td class="value">{esc(req.get("student_name","-"))}</td><td class="label">الاسم</td></tr>'
            rows_html += f'<tr><td class="value">{esc(req.get("reg_id","-"))}</td><td class="label">رقم التسجيل</td></tr>'
            rows_html += f'<tr><td class="value">{esc(req.get("college","-"))}</td><td class="label">الكلية</td></tr>'
            rows_html += f'<tr><td class="value">{esc(req.get("dept","-"))}</td><td class="label">القسم</td></tr>'
        for k, v in fd.items():
            if k.startswith('select:') or k.startswith('_'): continue
            rows_html += f'<tr><td class="value">{esc(v) if v else "—"}</td><td class="label">{esc(k)}</td></tr>'
        page_break_style = 'style="page-break-before: always;"' if idx > 0 else ''
        html += f"""<div class="req" {page_break_style}><div class="header"><div class="uni-name">🏛️ جامعة الناجي — {esc(service_name)}</div></div>
            <div class="meta">رقم الطلب: <strong>{esc(req.get('request_id', '-'))}</strong> &nbsp;•&nbsp; التاريخ: <strong>{full_datetime(req.get('timestamp', ''))}</strong></div>
            <table class="info-table">{rows_html}</table><div class="opinion-box"><div class="opinion-title">📝 رأي رئاسة الجامعة:</div><div class="opinion-space"></div></div>
            <div class="footer">جامعة الناجي — طُبع بتاريخ {now}</div></div>"""
    html += "</body></html>"; return html

def build_yearly_log_html(requests, service_name, dept_label, year_label):
    ROWS_PER_PAGE = 20  # ✅ 20 طلباً في الصفحة
    pages = [requests[i:i+ROWS_PER_PAGE] for i in range(0, len(requests), ROWS_PER_PAGE)]
    now = datetime.now().strftime("%Y/%m/%d — %H:%M")
    total = len(requests)

    html = """<!DOCTYPE html><html dir="rtl"><head><meta charset="utf-8">
<style>
    @page { size: A4 portrait; margin: 8mm; }
    * { box-sizing: border-box; }
    body { font-family: 'Segoe UI', Tahoma, sans-serif; direction: rtl; color: #1f2937; font-size: 8pt; margin: 0; padding: 0; }
    .page { page-break-after: always; page-break-inside: avoid; }
    .page.last { page-break-after: auto; }
    .header { background: #fbbf24; color: #0f172a; padding: 8px 12px; border: 2px solid #b45309; border-radius: 6px; margin-bottom: 10px; text-align: center; }
    .header h2 { margin: 0; font-size: 13pt; }
    .header p { margin: 4px 0 0 0; font-size: 9pt; }
    table { width: 100%; border-collapse: collapse; direction: rtl; table-layout: fixed; }
    th { background: #fef3c7; border: 1px solid #b45309; padding: 5px 4px; font-size: 8pt; text-align: right; }
    td { border: 1px solid #cbd5e1; padding: 4px; font-size: 7.5pt; text-align: right; height: 25px; }
    tr:nth-child(even) td { background: #fffbeb; }
    .footer { font-size: 7pt; color: #94a3b8; text-align: center; margin-top: 8px; }
</style></head><body>"""

    counter = 0
    last_idx = len(pages) - 1
    for page_idx, page_reqs in enumerate(pages):
        cls = "page last" if page_idx == last_idx else "page"
        html += f'<div class="{cls}">'
        html += f'''<div class="header">
            <h2>🏛️ جامعة الناجي — {esc(service_name)}</h2>
            <p>السجل السنوي | القسم: {esc(dept_label)} | السنة: {esc(year_label)} | صفحة {page_idx+1} من {len(pages)} | إجمالي: {total}</p>
        </div>'''
        
        # ✅ الأعمدة معكوسة برمجياً (من اليسار لليمين) ليظهر الاسم والرقم على اليمين
        html += """<table><thead><tr>
            <th style="width:11%;">التاريخ</th><th style="width:11%;">الحالة</th>
            <th style="width:11%;">الدراسة</th><th style="width:11%;">المرحلة</th>
            <th style="width:18%;">القسم</th><th style="width:12%;">رقم التسجيل</th>
            <th style="width:21%;">الاسم</th><th style="width:5%;">#</th>
        </tr></thead><tbody>"""
        
        for r in page_reqs:
            counter += 1
            st = STATUS_MAP.get(r.get('status', 'pending'), STATUS_MAP['pending'])
            dt = parse_ts(r.get('timestamp', ''))
            date_str = dt.strftime("%Y/%m/%d") if dt else "-"
            
            html += f"""<tr>
                <td>{date_str}</td>
                <td style="color:{st['color']}; font-weight:bold;">{st['text']}</td>
                <td>{esc(get_study_type(r))}</td>
                <td>{esc(get_stage(r))}</td>
                <td>{esc(r.get('dept','-'))}</td>
                <td>{esc(r.get('reg_id','-'))}</td>
                <td>{esc(r.get('student_name','-'))}</td>
                <td style="text-align:center;">{counter}</td>
            </tr>"""
        html += '</tbody></table>'
        html += f'<div class="footer">جامعة الناجي — طُبع {now}</div></div>'
    html += "</body></html>"; return html

# ═══════════════════════════════════════════════════════════
# خلفية الجسيمات
# ═══════════════════════════════════════════════════════════
class ParticleBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.particles = [{
            'x': random.randint(0,1920), 'y': random.randint(0,1080),
            'size': random.randint(2,6), 'speed': random.uniform(0.08,0.3),
            'opacity': random.uniform(0.015,0.05), 'angle': random.uniform(0,6.28),
            'color': random.choice(['#38bdf8','#818cf8','#22d3ee','#fbbf24'])
        } for _ in range(20)]
        t = QTimer(self); t.timeout.connect(self.update_particles); t.start(50)
    def update_particles(self):
        for p in self.particles:
            p['x'] += math.cos(p['angle']) * p['speed']; p['y'] += math.sin(p['angle']) * p['speed']
            if p['x'] < -50: p['x'] = self.width()+50
            if p['x'] > self.width()+50: p['x'] = -50
            if p['y'] < -50: p['y'] = self.height()+50
            if p['y'] > self.height()+50: p['y'] = -50
        self.update()
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        for pt in self.particles:
            c = QColor(pt['color']); c.setAlphaF(pt['opacity']); g = QRadialGradient(pt['x'], pt['y'], pt['size']*3); g.setColorAt(0, c); g.setColorAt(1, QColor(0,0,0,0)); p.setBrush(QBrush(g)); p.setPen(Qt.NoPen); p.drawEllipse(QPointF(pt['x'],pt['y']), pt['size'], pt['size'])
        p.end()

class SmartClock(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.setStyleSheet(f"background: {COLORS['surface']}; border-radius: 14px; border: 1px solid {COLORS['border']};")
        l = QVBoxLayout(self); l.setContentsMargins(14,14,14,14); l.setSpacing(4)
        self.time_label = QLabel("00:00"); self.time_label.setFont(F(30)); self.time_label.setStyleSheet(f"color:{COLORS['text_primary']}; background:transparent; border:none;"); self.time_label.setAlignment(Qt.AlignCenter); l.addWidget(self.time_label)
        self.seconds_label = QLabel("00 ثانية"); self.seconds_label.setFont(F(11)); self.seconds_label.setStyleSheet(f"color:{COLORS['text_dim']}; background:transparent; border:none;"); self.seconds_label.setAlignment(Qt.AlignCenter); l.addWidget(self.seconds_label)
        self.period_label = QLabel("AM"); self.period_label.setFont(F(10)); self.period_label.setStyleSheet(f"color:{COLORS['text_muted']}; background:transparent; border:none;"); self.period_label.setAlignment(Qt.AlignCenter); l.addWidget(self.period_label)
        self.date_label = QLabel(""); self.date_label.setFont(F(10)); self.date_label.setStyleSheet(f"color:{COLORS['text_muted']}; background:transparent; border:none;"); self.date_label.setAlignment(Qt.AlignCenter); self.date_label.setWordWrap(True); l.addWidget(self.date_label)
        self.pbg = QFrame(); self.pbg.setFixedHeight(2); self.pbg.setStyleSheet(f"background: {COLORS['border']}; border-radius:1px; border:none;")
        self.pfill = QFrame(self.pbg); self.pfill.setFixedHeight(2); self.pfill.setStyleSheet(f"background:{COLORS['accent']}; border-radius:1px; border:none;")
        l.addSpacing(4); l.addWidget(self.pbg); l.addSpacing(8)
        self.uni_name = QLabel("جامعة الناجي"); self.uni_name.setFont(F(14)); self.uni_name.setStyleSheet(f"color:{COLORS['text_secondary']}; background:transparent; border:none;"); self.uni_name.setAlignment(Qt.AlignCenter); l.addWidget(self.uni_name)
        self.uni_sub = QLabel("شاشة استقبال الطلبات"); self.uni_sub.setFont(F(10)); self.uni_sub.setStyleSheet(f"color:{COLORS['text_dim']}; background:transparent; border:none;"); self.uni_sub.setAlignment(Qt.AlignCenter); l.addWidget(self.uni_sub); l.addStretch()
        self.conn_label = QLabel("● متصل"); self.conn_label.setFont(F(10)); self.conn_label.setStyleSheet("color:#10b981; background:transparent; border:none;"); self.conn_label.setAlignment(Qt.AlignCenter); l.addWidget(self.conn_label)
        self.greeting = QLabel(""); self.greeting.setFont(F(12)); self.greeting.setStyleSheet(f"color:{COLORS['text_secondary']}; background:transparent; border:none;"); self.greeting.setAlignment(Qt.AlignCenter); l.addWidget(self.greeting)
        t = QTimer(self); t.timeout.connect(self.update_clock); t.start(1000); self.update_clock()
    def set_connection(self, ok):
        if ok: self.conn_label.setText("● متصل"); self.conn_label.setStyleSheet("color:#10b981; background:transparent; border:none;")
        else: self.conn_label.setText("● غير متصل"); self.conn_label.setStyleSheet("color:#ef4444; background:transparent; border:none;")
    def update_clock(self):
        now = datetime.now(); h = now.hour; h12 = h if h <= 12 else h - 12
        if h12 == 0: h12 = 12
        self.time_label.setText(f"{h12:02d}:{now.minute:02d}")
        self.seconds_label.setText(f"{now.second:02d} ثانية")
        self.period_label.setText("AM" if h < 12 else "PM")
        days = ["الإثنين","الثلاثاء","الأربعاء","الخميس","الجمعة","السبت","الأحد"]
        months = ["يناير","فبراير","مارس","إبريل","مايو","يونيو","يوليو","أغسطس","سبتمبر","أكتوبر","نوفمبر","ديسمبر"]
        self.date_label.setText(f"{days[now.weekday()]} • {now.day} {months[now.month-1]}")
        if 5 <= h < 12: g = "☀️ صباح الخير"
        elif 12 <= h < 17: g = "🌤️ نهار سعيد"
        elif 17 <= h < 21: g = "🌅 مساء النور"
        else: g = "🌙 ليلة سعيدة"
        self.greeting.setText(g)
        w = int(self.pbg.width() * (now.second/60.0)); self.pfill.setGeometry(0, 0, max(w, 2), 2)

class Toast(QWidget):
    def __init__(self, title, message, color="#10b981", parent=None):
        super().__init__(parent); self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground); self.setAttribute(Qt.WA_ShowWithoutActivating); self.setFixedSize(340, 82)
        c = QFrame(self); c.setGeometry(0, 0, 340, 82); c.setStyleSheet(f"QFrame {{ background: {COLORS['bg_grad_top']}; border-radius: 12px; border: 1px solid {color}; }}")
        l = QHBoxLayout(c); l.setContentsMargins(14,12,14,12); l.setSpacing(10)
        ic = QLabel("🔔"); ic.setFont(F(22)); ic.setStyleSheet(f"color:{color}; background:transparent; border:none;"); l.addWidget(ic)
        v = QVBoxLayout(); v.setSpacing(2); t = QLabel(title); t.setFont(F(12)); t.setStyleSheet(f"color:{COLORS['text_primary']}; background:transparent; border:none;"); v.addWidget(t)
        m = QLabel(message); m.setFont(F(10, bold=False)); m.setStyleSheet(f"color:{COLORS['text_muted']}; background:transparent; border:none;"); m.setWordWrap(True); v.addWidget(m); l.addLayout(v, 1)
        s = QApplication.primaryScreen().availableGeometry(); self.move(s.width() - 360, 20); self.setWindowOpacity(0)
        self.anim = QPropertyAnimation(self, b"windowOpacity"); self.anim.setDuration(280); self.anim.setStartValue(0.0); self.anim.setEndValue(1.0); self.anim.start()
        QTimer.singleShot(4000, self.close_anim)
    def close_anim(self):
        self.anim2 = QPropertyAnimation(self, b"windowOpacity"); self.anim2.setDuration(400); self.anim2.setStartValue(1.0); self.anim2.setEndValue(0.0); self.anim2.finished.connect(self.close); self.anim2.start()
        # ═══════════════════════════════════════════════════════════
# العمال (Workers)
# ═══════════════════════════════════════════════════════════
class LoadServicesWorker(QThread):
    done = Signal(list, str)
    def run(self):
        try:
            r = client.table("services").select("*").order("sort_order").execute()
            self.done.emit(r.data or [], "")
        except Exception as e:
            self.done.emit([], str(e))

class LoadRequestsWorker(QThread):
    done = Signal(list, str)
    def run(self):
        try:
            active = (client.table("requests").select("*")
                      .in_("status", ["pending", "approved", "ready"])
                      .order("timestamp", desc=True).limit(MAX_REQUESTS).execute()).data or []
            
            archived = (client.table("requests").select("*")
                        .in_("status", ["delivered", "rejected"])
                        .order("timestamp", desc=True).limit(MAX_ARCHIVED).execute()).data or []

            requests = active + archived
            reg_ids = list(set(x.get('reg_id') for x in requests if x.get('reg_id')))
            students_map = {}
            if reg_ids:
                try:
                    s = (client.table("students").select("reg_id, study_type, stage")
                         .in_("reg_id", reg_ids).execute())
                    for st in (s.data or []):
                        students_map[st['reg_id']] = {
                            'study_type': st.get('study_type') or '',
                            'stage': st.get('stage') or '',
                        }
                except Exception as e:
                    print("خطأ جلب الطلاب:", e)

            for req in requests:
                if req.get('reg_id') and req['reg_id'] in students_map:
                    req['_study_type'] = students_map[req['reg_id']]['study_type']
                    req['_stage'] = students_map[req['reg_id']]['stage']

            self.done.emit(requests, "")
        except Exception as e:
            self.done.emit([], str(e))

class LoadAllServiceReqsWorker(QThread):
    done = Signal(list, str)
    def __init__(self, service_id):
        super().__init__()
        self.service_id = service_id
    def run(self):
        try:
            r = (client.table("requests").select("*")
                 .eq("service_id", self.service_id)
                 .order("timestamp", desc=True).execute())
            reqs = r.data or []
            reg_ids = list(set(x.get('reg_id') for x in reqs if x.get('reg_id')))
            students_map = {}
            if reg_ids:
                try:
                    s = (client.table("students").select("reg_id, study_type, stage")
                         .in_("reg_id", reg_ids).execute())
                    for st in (s.data or []):
                        students_map[st['reg_id']] = {
                            'study_type': st.get('study_type') or '',
                            'stage': st.get('stage') or '',
                        }
                except: pass
            for req in reqs:
                if req.get('reg_id') and req['reg_id'] in students_map:
                    req['_study_type'] = students_map[req['reg_id']]['study_type']
                    req['_stage'] = students_map[req['reg_id']]['stage']
            self.done.emit(reqs, "")
        except Exception as e:
            self.done.emit([], str(e))

class UpdateWorker(QThread):
    done = Signal(bool, str)
    def __init__(self, rid, up, delete_img_name=None):
        super().__init__()
        self.rid = rid
        self.up = up
        self.delete_img_name = delete_img_name
    def run(self):
        try:
            (client.table("requests").update(self.up).eq("request_id", self.rid).execute())
            if self.delete_img_name:
                delete_image_from_storage(self.delete_img_name)
            self.done.emit(True, "")
        except Exception as e:
            self.done.emit(False, str(e))

class DeleteWorker(QThread):
    done = Signal(bool, str)
    def __init__(self, rid):
        super().__init__()
        self.rid = rid
    def run(self):
        try:
            img_name = None
            try:
                r = (client.table("requests").select("image_name").eq("request_id", self.rid).execute())
                if r.data and len(r.data) > 0:
                    img_name = r.data[0].get('image_name')
            except: pass
            (client.table("requests").delete().eq("request_id", self.rid).execute())
            check = (client.table("requests").select("request_id").eq("request_id", self.rid).execute())
            if check.data and len(check.data) > 0:
                self.done.emit(False, "لم يتم الحذف — قد تكون سياسة DELETE غير مفعّلة")
                return
            if img_name:
                delete_image_from_storage(img_name)
            self.done.emit(True, "")
        except Exception as e:
            self.done.emit(False, str(e))

class BatchDeleteWorker(QThread):
    done = Signal(bool, int, str)
    def __init__(self, rids):
        super().__init__()
        self.rids = rids
    def run(self):
        try:
            count = 0
            for rid in self.rids:
                try:
                    img_name = None
                    try:
                        r = (client.table("requests").select("image_name").eq("request_id", rid).execute())
                        if r.data and len(r.data) > 0:
                            img_name = r.data[0].get('image_name')
                    except: pass
                    (client.table("requests").delete().eq("request_id", rid).execute())
                    count += 1
                    if img_name:
                        try: delete_image_from_storage(img_name)
                        except: pass
                except Exception as e:
                    print(f"فشل حذف {rid}: {e}")
            self.done.emit(True, count, "")
        except Exception as e:
            self.done.emit(False, 0, str(e))

class BatchUpdateWorker(QThread):
    done = Signal(bool, int, str)
    def __init__(self, updates_list):
        super().__init__()
        self.updates_list = updates_list
    def run(self):
        try:
            count = 0
            for rid, up in self.updates_list:
                try:
                    (client.table("requests").update(up).eq("request_id", rid).execute())
                    count += 1
                except Exception as e:
                    print(f"فشل {rid}: {e}")
            self.done.emit(True, count, "")
        except Exception as e:
            self.done.emit(False, 0, str(e))

class DeleteByRegIdWorker(QThread):
    done = Signal(bool, int, str, str)
    def __init__(self, reg_id, reqs):
        super().__init__()
        self.reg_id = reg_id
        self.reqs = reqs
    def run(self):
        try:
            name = self.reqs[0].get('student_name', '') if self.reqs else ''
            count = 0
            for r in self.reqs:
                rid = r.get('request_id')
                if not rid: continue
                img = r.get('image_name') or extract_image_name(r.get('image_url'))
                try:
                    (client.table("requests").delete().eq("request_id", rid).execute())
                    count += 1
                    if img:
                        try: delete_image_from_storage(img)
                        except: pass
                except Exception as e:
                    print(f"فشل حذف {rid}: {e}")
            self.done.emit(True, count, name, "")
        except Exception as e:
            self.done.emit(False, 0, "", str(e))

class DownloadImageWorker(QThread):
    done = Signal(bytes, str)
    def __init__(self, url):
        super().__init__()
        self.url = url
    def run(self):
        try:
            req = urllib.request.Request(self.url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = r.read()
            self.done.emit(data, "")
        except Exception as e:
            self.done.emit(b"", str(e))

class ArchiveWorker(QThread):
    progress = Signal(str, int, int); done = Signal(bool, str)
    def __init__(self, services, output_dir): super().__init__(); self.services = services; self.output_dir = output_dir
    def run(self):
        try:
            for idx, svc in enumerate(self.services):
                self.progress.emit(f"جاري معالجة: {svc.get('service_name')} ({idx+1}/{len(self.services)})", idx+1, len(self.services))
                r = client.table("requests").select("*").eq("service_id", svc.get('service_id')).execute()
                if not r.data: continue
                html = build_yearly_log_html(r.data, svc.get('service_name'), "جميع الأقسام", "جميع السنوات")
                printer = QPrinter(QPrinter.HighResolution); printer.setOutputFormat(QPrinter.PdfFormat); printer.setOutputFileName(str(Path(self.output_dir) / f"{svc.get('service_name')}_Archive.pdf")); printer.setPageSize(QPageSize(QPageSize.A4)); printer.setPageMargins(QMarginsF(8,8,8,8), QPageLayout.Millimeter)
                doc = QTextDocument(); doc.setHtml(html); doc.print_(printer)
            self.done.emit(True, "تم تصدير جميع الملفات بنجاح.")
        except Exception as e: self.done.emit(False, str(e))

class CleanDBWorker(QThread):
    progress = Signal(str, int, int); done = Signal(bool, str)
    def run(self):
        try:
            self.progress.emit("جاري جلب الصور...", 0, 0)
            r = client.table("requests").select("image_name, image_url").execute()
            images = [extract_image_name(x.get('image_url')) for x in r.data if x.get('image_url')]
            for i in range(0, len(images), 100):
                try: client.storage.from_('request-images').remove(images[i:i+100])
                except: pass
            self.progress.emit("جاري مسح الطلبات...", 0, 0)
            client.table("requests").delete().neq("request_id", "___").execute()
            self.done.emit(True, "تم التنظيف بنجاح.")
        except Exception as e: self.done.emit(False, str(e))

# ═══════════════════════════════════════════════════════════
# النوافذ (Dialogs)
# ═══════════════════════════════════════════════════════════
class ImageViewer(QDialog):
    def __init__(self, image_url, request_id="", title="صورة الطلب", parent=None):
        super().__init__(parent)
        self.image_url = image_url
        self.request_id = request_id or "image"
        self.image_data = None

        self.setWindowTitle(title)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumSize(750, 720)
        self.setStyleSheet(f"QDialog {{ background: {COLORS['bg_grad_top']}; }}")

        l = QVBoxLayout(self)
        l.setContentsMargins(18,18,18,18)
        l.setSpacing(12)

        head = QHBoxLayout()
        title_lbl = QLabel(f"🖼️  {title}")
        title_lbl.setFont(F(15))
        title_lbl.setStyleSheet(f"color:{COLORS['text_secondary']}; background:transparent;")
        head.addWidget(title_lbl, 1)

        close_top = QPushButton("✕")
        close_top.setFixedSize(30, 30)
        close_top.setCursor(Qt.PointingHandCursor)
        close_top.setStyleSheet("""
            QPushButton { background: rgba(239,68,68,0.15); color: #f87171;
                border-radius: 15px; border: none; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background: #dc2626; color: white; }
        """)
        close_top.clicked.connect(self.reject)
        head.addWidget(close_top)
        l.addLayout(head)

        self.status = QLabel("⏳  جاري تحميل الصورة...")
        self.status.setFont(F(11))
        self.status.setStyleSheet(f"color:{COLORS['text_muted']}; background:transparent;")
        self.status.setAlignment(Qt.AlignCenter)
        l.addWidget(self.status)

        img_frame = QFrame()
        img_frame.setStyleSheet(f"QFrame {{ background: {COLORS['surface']}; border-radius: 12px; border: 1px solid {COLORS['border']}; }}")
        il = QVBoxLayout(img_frame)
        il.setContentsMargins(12,12,12,12)
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setStyleSheet("background: transparent; border: none;")
        self.img_label.setMinimumHeight(450)
        il.addWidget(self.img_label)
        l.addWidget(img_frame, 1)

        btns = QHBoxLayout()
        btns.setSpacing(8)
        self.save_btn = QPushButton("💾  حفظ الصورة")
        self.save_btn.setFont(F(12))
        self.save_btn.setMinimumHeight(44)
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet("""
            QPushButton { background: #059669; color: white; border-radius: 10px; border: none; padding: 8px 18px; }
            QPushButton:hover:enabled { background: #047857; }
            QPushButton:disabled { background: rgba(100,116,139,0.3); color: #64748b; }
        """)
        self.save_btn.clicked.connect(self.save_image)
        btns.addWidget(self.save_btn, 1)

        close_btn = QPushButton("إغلاق")
        close_btn.setFont(F(12))
        close_btn.setMinimumHeight(44)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton { background: rgba(100,116,139,0.2); color: #cbd5e1; border-radius: 10px; border: 1px solid rgba(255,255,255,0.08); padding: 8px 18px; }
            QPushButton:hover { background: rgba(100,116,139,0.4); }
        """)
        close_btn.clicked.connect(self.accept)
        btns.addWidget(close_btn)
        l.addLayout(btns)

        self.worker = DownloadImageWorker(image_url)
        self.worker.done.connect(self._on_loaded)
        self.worker.start()

    def _on_loaded(self, data, err):
        if err or not data:
            self.status.setText("❌  فشل تحميل الصورة")
            self.img_label.setText("⚠️ لا يمكن عرض الصورة")
            return
        self.image_data = data
        pix = QPixmap()
        if pix.loadFromData(data):
            self.img_label.setPixmap(pix.scaled(700, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.status.setText(f"✅  تم التحميل ({len(data)/1024:.0f} KB)")
            self.save_btn.setEnabled(True)

    def save_image(self):
        if not self.image_data: return
        path, _ = QFileDialog.getSaveFileName(self, "حفظ الصورة", f"{self.request_id}.jpg", "JPEG (*.jpg);;PNG (*.png);;كل الملفات (*)")
        if path:
            try:
                with open(path, 'wb') as f: f.write(self.image_data)
                QMessageBox.information(self, "تم", f"تم حفظ الصورة في:\n{path}")
            except Exception as e: QMessageBox.critical(self, "خطأ", f"فشل الحفظ:\n{e}")

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ إعدادات النصوص الثابتة")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumSize(600, 550)
        self.setStyleSheet(f"QDialog {{ background: {COLORS['bg_grad_top']}; }}")

        l = QVBoxLayout(self)
        l.setContentsMargins(25, 25, 25, 25)
        l.setSpacing(12)

        title = QLabel("⚙️  النصوص الثابتة في القوالب")
        title.setFont(F(16))
        title.setStyleSheet(f"color: {COLORS['accent']}; background: transparent; border: none;")
        l.addWidget(title)

        hint = QLabel("هذه النصوص تظهر في الورقة الرسمية. تُحفظ في settings.json بجانب البرنامج.")
        hint.setFont(F(10, bold=False))
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent; border: none;")
        l.addWidget(hint)
        l.addSpacing(10)

        self.inputs = {}
        def make_field(label, key, val):
            lbl = QLabel(label)
            lbl.setFont(F(11))
            lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent; border: none;")
            l.addWidget(lbl)
            inp = QLineEdit(val)
            inp.setFont(F(12))
            inp.setMinimumHeight(40)
            inp.setStyleSheet(f"""
                QLineEdit {{ background: {COLORS['surface_soft']}; color: {COLORS['text_primary']};
                    border: 1px solid {COLORS['border']}; border-radius: 8px; padding: 8px 14px; }}
                QLineEdit:focus {{ border: 1px solid #3b82f6; }}
            """)
            l.addWidget(inp)
            self.inputs[key] = inp

        make_field("الموضوع (A4):", "fixed_subject", SETTINGS.get("fixed_subject", ""))
        make_field("التحية (A4):", "fixed_greeting", SETTINGS.get("fixed_greeting", ""))
        make_field("التقدير (A4):", "fixed_thanks", SETTINGS.get("fixed_thanks", ""))
        make_field("الختم الأيمن (A5):", "stamp_right", SETTINGS.get("stamp_right", ""))
        make_field("الختم الأيسر (A5):", "stamp_left", SETTINGS.get("stamp_left", ""))
        make_field("اسم الموقع (A4):", "sign_name", SETTINGS.get("sign_name", ""))
        make_field("صفة الموقع (A4):", "sign_title", SETTINGS.get("sign_title", ""))
        l.addStretch()

        btn_row = QHBoxLayout()
        save_btn = QPushButton("💾  حفظ")
        save_btn.setFont(F(13))
        save_btn.setMinimumHeight(46)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton { background: #059669; color: white; border-radius: 10px; border: none; font-weight: bold; }
            QPushButton:hover { background: #047857; }
        """)
        save_btn.clicked.connect(self.save_and_close)
        btn_row.addWidget(save_btn, 1)

        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setFont(F(12))
        cancel_btn.setMinimumHeight(46)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton { background: #334155; color: #e2e8f0; border-radius: 10px; border: none; }
            QPushButton:hover { background: #475569; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn, 1)
        l.addLayout(btn_row)

    def save_and_close(self):
        global SETTINGS
        new_settings = dict(SETTINGS)
        for k, inp in self.inputs.items():
            new_settings[k] = inp.text().strip()
        if save_settings(new_settings):
            SETTINGS = load_settings()
            QMessageBox.information(self, "✅ تم", "تم حفظ الإعدادات بنجاح")
            self.accept()
        else:
            QMessageBox.critical(self, "خطأ", "فشل حفظ الإعدادات")

class ArchiveDialog(QDialog):
    def __init__(self, services, parent=None):
        super().__init__(parent); self.services = services; self.output_dir = ""; self.setWindowTitle("🗄️ أرشفة وتنظيف السنة"); self.setLayoutDirection(Qt.RightToLeft); self.setMinimumSize(650, 550); self.setStyleSheet(f"QDialog {{ background: {COLORS['bg_grad_top']}; }}")
        layout = QVBoxLayout(self); layout.setSpacing(15)
        title = QLabel("🗄️ أرشفة وتنظيف السنة الدراسية"); title.setFont(F(16)); title.setStyleSheet("color:#fbbf24; background:transparent;"); layout.addWidget(title)
        desc = QLabel("هذه العملية ستقوم بتصدير ملف PDF لكل خدمة.\nيرجى التأكد من اختيار مجلد الحفظ قبل البدء."); desc.setFont(F(11, bold=False)); desc.setStyleSheet(f"color:{COLORS['text_muted']}; background:transparent;"); desc.setWordWrap(True); layout.addWidget(desc)
        g1 = QFrame(); g1.setStyleSheet(f"QFrame {{ background: {COLORS['surface']}; border-radius: 10px; border: 1px solid {COLORS['border']}; }}"); g1l = QVBoxLayout(g1); g1l.setContentsMargins(15, 15, 15, 15)
        g1_title = QLabel("📄 1. تصدير الأرشيف إلى PDF"); g1_title.setFont(F(13)); g1_title.setStyleSheet("color:#38bdf8; background:transparent;"); g1l.addWidget(g1_title)
        row1 = QHBoxLayout(); self.folder_lbl = QLabel("لم يتم اختيار مجلد"); self.folder_lbl.setFont(F(11)); self.folder_lbl.setStyleSheet(f"color:{COLORS['text_secondary']}; background:transparent;"); row1.addWidget(self.folder_lbl, 1)
        browse_btn = QPushButton("📂 اختيار مجلد"); browse_btn.setFont(F(10)); browse_btn.setCursor(Qt.PointingHandCursor); browse_btn.setStyleSheet(f"QPushButton {{ background: {COLORS['surface_soft']}; color: {COLORS['text_primary']}; border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 5px 10px; }}"); browse_btn.clicked.connect(self.select_folder); row1.addWidget(browse_btn); g1l.addLayout(row1)
        self.progress_lbl = QLabel(""); self.progress_lbl.setFont(F(10)); self.progress_lbl.setStyleSheet(f"color:{COLORS['text_dim']}; background:transparent;"); g1l.addWidget(self.progress_lbl)
        self.progress_bar = QProgressBar(); self.progress_bar.setRange(0, 100); self.progress_bar.hide(); g1l.addWidget(self.progress_bar)
        self.export_btn = QPushButton("🚀 بدء التصدير"); self.export_btn.setFont(F(12)); self.export_btn.setMinimumHeight(40); self.export_btn.setCursor(Qt.PointingHandCursor); self.export_btn.setEnabled(False); self.export_btn.setStyleSheet("QPushButton { background: #38bdf8; color: #0b1220; border-radius: 8px; font-weight: bold; border: none; } QPushButton:hover { background: #0284c7; color: white; } QPushButton:disabled { background: #475569; color: #94a3b8; }"); self.export_btn.clicked.connect(self.start_export); g1l.addWidget(self.export_btn); layout.addWidget(g1)
        g2 = QFrame(); g2.setStyleSheet("QFrame { background: rgba(239,68,68,0.1); border-radius: 10px; border: 1px solid rgba(239,68,68,0.3); }"); g2l = QVBoxLayout(g2); g2l.setContentsMargins(15, 15, 15, 15)
        g2_title = QLabel("🗑️ 2. تنظيف قاعدة البيانات"); g2_title.setFont(F(13)); g2_title.setStyleSheet("color:#ef4444; background:transparent;"); g2l.addWidget(g2_title)
        warn = QLabel("⚠️ تحذير: هذه العملية ستحذف جميع الطلبات نهائياً. يُرجى تصدير PDF أولاً."); warn.setFont(F(10)); warn.setWordWrap(True); warn.setStyleSheet("color:#f87171; background:transparent;"); g2l.addWidget(warn)
        self.clean_btn = QPushButton("🗑️ حذف جميع الطلبات نهائياً"); self.clean_btn.setFont(F(12)); self.clean_btn.setMinimumHeight(40); self.clean_btn.setCursor(Qt.PointingHandCursor); self.clean_btn.setStyleSheet("QPushButton { background: #ef4444; color: white; border-radius: 8px; font-weight: bold; border: none; } QPushButton:hover { background: #dc2626; }"); self.clean_btn.clicked.connect(self.start_clean); g2l.addWidget(self.clean_btn); layout.addWidget(g2)
        layout.addStretch()
        close_btn = QPushButton("إغلاق"); close_btn.setFont(F(11)); close_btn.setMinimumHeight(36); close_btn.setCursor(Qt.PointingHandCursor); close_btn.setStyleSheet(f"QPushButton {{ background: {COLORS['surface_soft']}; color: {COLORS['text_primary']}; border-radius: 8px; border: 1px solid {COLORS['border']}; }}"); close_btn.clicked.connect(self.reject); layout.addWidget(close_btn)
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "اختر مجلد الحفظ")
        if folder: self.output_dir = folder; self.folder_lbl.setText(folder); self.export_btn.setEnabled(True)
    def start_export(self):
        if not self.output_dir: return
        self.export_btn.setEnabled(False); self.progress_bar.show(); self.progress_bar.setValue(0)
        self.export_worker = ArchiveWorker(self.services, self.output_dir); self.export_worker.progress.connect(self.on_progress); self.export_worker.done.connect(self.on_export_done); self.export_worker.start()
    def on_progress(self, msg, val, total):
        self.progress_lbl.setText(msg)
        if total > 0: self.progress_bar.setMaximum(total); self.progress_bar.setValue(val)
        else: self.progress_bar.setMaximum(0)
    def on_export_done(self, ok, msg):
        self.progress_bar.hide(); self.export_btn.setEnabled(True)
        if ok: QMessageBox.information(self, "✅ تم", msg); self.progress_lbl.setText("✅ تم التصدير")
        else: QMessageBox.critical(self, "خطأ", msg); self.progress_lbl.setText("❌ فشل")
    def start_clean(self):
        pwd, ok = QInputDialog.getText(self, "🔒 تأكيد", "أدخل كلمة المرور:", QLineEdit.Password)
        if not ok or pwd != DELETE_PASSWORD:
            if ok: QMessageBox.critical(self, "خطأ", "الرمز غير صحيح")
            return
        if QMessageBox.warning(self, "⚠️ تأكيد", "سيتم حذف كل الطلبات ولا يمكن التراجع!", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes: return
        self.clean_btn.setEnabled(False); self.progress_bar.show(); self.progress_bar.setMaximum(0); self.progress_lbl.setText("جاري الحذف...")
        self.clean_worker = CleanDBWorker(); self.clean_worker.progress.connect(self.on_progress); self.clean_worker.done.connect(self.on_clean_done); self.clean_worker.start()
    def on_clean_done(self, ok, msg):
        self.progress_bar.hide(); self.clean_btn.setEnabled(True)
        if ok: QMessageBox.information(self, "✅ تم", msg); self.accept()
        else: QMessageBox.critical(self, "خطأ", msg)

class LetterPreviewDialog(QDialog):
    def __init__(self, req, parent=None):
        super().__init__(parent)
        self.req = req
        self.photo_path = None
        self.current_image = None
        self.inputs = {}
        self.font_size = 35
        self.template_type = detect_template_type(req)

        titles = {'A4': "📄 معاينة الورقة (A4)", 'A5': "📄 معاينة مباشرة (A5)", 'MEDICAL': "📄 معاينة إحالة"}
        self.setWindowTitle(titles.get(self.template_type, "📄 معاينة"))
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(f"QDialog {{ background: {COLORS['bg_grad_top']}; }}")

        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.refresh)
        self._timer.setInterval(250)

        self.build_ui()
        self.fill_from_request()

        url = req.get('image_url')
        if url and self.template_type != 'MEDICAL':
            self.w = DownloadImageWorker(url)
            self.w.done.connect(self._on_photo_downloaded)
            self.w.start()
        else:
            QTimer.singleShot(200, self.refresh)

    def build_ui(self):
        ml = QHBoxLayout(self)
        ml.setContentsMargins(10, 10, 10, 10)
        ml.setSpacing(10)

        psc = QScrollArea()
        psc.setWidgetResizable(True)
        psc.setFixedWidth(420)
        psc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        psc.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{ background: transparent; width: 6px; }}
            QScrollBar::handle:vertical {{ background: {COLORS['border']}; border-radius: 3px; min-height: 25px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar:horizontal {{ height: 0; }}
        """)
        pn = QFrame()
        pn.setStyleSheet(f"QFrame {{ background: {COLORS['surface']}; border-radius: 12px; }}")
        psc.setWidget(pn)
        pl2 = QVBoxLayout(pn)
        pl2.setContentsMargins(15, 15, 15, 15)
        pl2.setSpacing(6)

        def section(t):
            sep = QFrame()
            sep.setFixedHeight(1)
            sep.setStyleSheet(f"background: {COLORS['border']}; border: none;")
            pl2.addWidget(sep)
            lbl = QLabel(t)
            lbl.setFont(F(11))
            lbl.setStyleSheet(f"color: {COLORS['accent']}; background: transparent; border: none; padding-top: 4px;")
            pl2.addWidget(lbl)

        def field(label, key, default="", placeholder=""):
            lbl = QLabel(label)
            lbl.setFont(F(10))
            lbl.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent; border: none;")
            pl2.addWidget(lbl)
            inp = QLineEdit(default)
            inp.setFont(F(11))
            inp.setMinimumHeight(32)
            if placeholder: inp.setPlaceholderText(placeholder)
            inp.setStyleSheet(f"""
                QLineEdit {{ background: {COLORS['surface_soft']}; color: {COLORS['text_primary']};
                    border: 1px solid {COLORS['border']}; border-radius: 7px; padding: 5px 10px; }}
                QLineEdit:focus {{ border: 1px solid {COLORS['accent']}; }}
            """)
            inp.textChanged.connect(lambda: self._timer.start())
            pl2.addWidget(inp)
            self.inputs[key] = inp

        def textarea(label, key, default="", min_h=100):
            lbl = QLabel(label)
            lbl.setFont(F(10))
            lbl.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent; border: none;")
            pl2.addWidget(lbl)
            tx = QTextEdit()
            tx.setPlainText(default)
            tx.setMinimumHeight(min_h)
            tx.setFont(F(11))
            tx.setStyleSheet(f"""
                QTextEdit {{ background: {COLORS['surface_soft']}; color: {COLORS['text_primary']};
                    border: 1px solid {COLORS['border']}; border-radius: 7px; padding: 6px; }}
                QTextEdit:focus {{ border: 1px solid {COLORS['accent']}; }}
            """)
            tx.textChanged.connect(lambda: self._timer.start())
            pl2.addWidget(tx)
            self.inputs[key] = tx

        section("👤  بيانات الطالب")
        field("الاسم", "name", "")
        field("القسم", "dept", "")
        field("المرحلة", "stage", "")
        field("نوع الدراسة", "study_type", "")

        if self.template_type == 'A4':
            field("الكلية", "college", "")
            field("السنة الدراسية", "academic_year", f"{datetime.now().year}-{datetime.now().year+1}")
            section("📌  الأرقام (يدوي)")
            field("العدد", "number", "", "يدوي")
            field("التاريخ", "date", "", "يدوي")
            section("📝  النصوص")
            field("إلى /", "to_text", "إلى /")
            textarea("نص الفقرة", "body_text", "", min_h=200)
            section("✍️  التوقيع")
            textarea("التوقيع", "signature_text", f"{SETTINGS.get('sign_name')}\n{SETTINGS.get('sign_title')}\n{datetime.now().year} /    /", min_h=100)
            section("📋  النسخ")
            field("نسخه منه إلى", "copy_to_text", "نسخه منه إلى:")
            field("نسخة 1", "copy_1_text", "- الصادرة")
            field("نسخة 2", "copy_2_text", "- جنان")

        elif self.template_type == 'A5':
            field("الكلية", "college", "")
            field("السنة الدراسية", "academic_year", f"{datetime.now().year}-{datetime.now().year+1}")
            section("📝  النص")
            textarea("نص الفقرة", "body_text", "", min_h=140)
            section("🏛️  الختمين")
            field("الختم الأيمن", "stamp_right", SETTINGS.get("stamp_right", ""))
            field("الختم الأيسر", "stamp_left", SETTINGS.get("stamp_left", ""))

        else: # MEDICAL
            field("الكلية / القسم", "college", "")
            section("🩺  بيانات الإحالة")
            field("العمر", "age", "", "مثال: 22")
            field("المركز الصحي المحال اليه", "health_center", "", "مثال: مركز صحي")

        if self.template_type != 'MEDICAL':
            section("📷  صورة الطالب")
            prow = QHBoxLayout()
            self.photo_txt = QLabel("لم يتم اختيار صورة")
            self.photo_txt.setFont(F(10))
            self.photo_txt.setStyleSheet(f"color: {COLORS['text_dim']}; background: transparent; border: none;")
            prow.addWidget(self.photo_txt, 1)
            pb = QPushButton("📁 اختيار")
            pb.setFont(F(10))
            pb.setCursor(Qt.PointingHandCursor)
            pb.setFixedHeight(32)
            pb.setStyleSheet(f"""
                QPushButton {{ background: {COLORS['border']}; color: {COLORS['text_primary']}; border-radius: 7px; border: none; padding: 5px 12px; }}
                QPushButton:hover {{ background: {COLORS['border_hover']}; }}
            """)
            pb.clicked.connect(self.select_photo)
            prow.addWidget(pb)
            pl2.addLayout(prow)

        section("🔤  حجم النص")
        srow = QHBoxLayout()
        srow.setSpacing(6)
        minus_btn = QPushButton("−")
        minus_btn.setFont(F(11))
        minus_btn.setCursor(Qt.PointingHandCursor)
        minus_btn.setFixedHeight(40)
        minus_btn.setStyleSheet("QPushButton { background: #dc2626; color: white; border-radius: 8px; border: none; }")
        minus_btn.clicked.connect(lambda: self.change_font_size(-1))
        srow.addWidget(minus_btn, 1)

        self.font_size_lbl = QLabel("35")
        self.font_size_lbl.setFont(F(18))
        self.font_size_lbl.setAlignment(Qt.AlignCenter)
        self.font_size_lbl.setFixedHeight(40)
        self.font_size_lbl.setStyleSheet(f"color: {COLORS['text_primary']}; background: {COLORS['surface_soft']}; border-radius: 8px; border: 1px solid {COLORS['border']};")
        srow.addWidget(self.font_size_lbl)

        plus_btn = QPushButton("+")
        plus_btn.setFont(F(11))
        plus_btn.setCursor(Qt.PointingHandCursor)
        plus_btn.setFixedHeight(40)
        plus_btn.setStyleSheet("QPushButton { background: #059669; color: white; border-radius: 8px; border: none; }")
        plus_btn.clicked.connect(lambda: self.change_font_size(1))
        srow.addWidget(plus_btn, 1)
        pl2.addLayout(srow)
        pl2.addSpacing(10)

        pr_btn = QPushButton("🖨️  طباعة")
        pr_btn.setFont(F(12))
        pr_btn.setMinimumHeight(46)
        pr_btn.setCursor(Qt.PointingHandCursor)
        pr_btn.setStyleSheet("QPushButton { background: #fbbf24; color: #0b1220; border-radius: 10px; border: none; font-weight: bold; }")
        pr_btn.clicked.connect(self.print_letter)
        pl2.addWidget(pr_btn)

        close_btn = QPushButton("إغلاق")
        close_btn.setFont(F(11))
        close_btn.setMinimumHeight(36)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton { background: #334155; color: #e2e8f0; border-radius: 8px; border: none; }")
        close_btn.clicked.connect(self.accept)
        pl2.addWidget(close_btn)
        pl2.addStretch()
        ml.addWidget(psc, 0)

        pf = QFrame()
        pf.setStyleSheet(f"QFrame {{ background: {COLORS['surface']}; border-radius: 12px; }}")
        pl = QVBoxLayout(pf)
        pl.setContentsMargins(10, 10, 10, 10)
        t = QLabel("📄  المعاينة")
        t.setFont(F(13))
        t.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent; border: none;")
        pl.addWidget(t)
        self.preview = QLabel("⏳ جاري التحميل...")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet(f"color: {COLORS['text_muted']}; background: {COLORS['surface_soft']}; border-radius: 8px;")
        self.preview.setMinimumSize(200, 200)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setStyleSheet(f"QScrollArea {{ background: {COLORS['surface_soft']}; border-radius: 8px; border: none; }}")
        sc.setWidget(self.preview)
        pl.addWidget(sc, 1)
        ml.addWidget(pf, 1)

    def change_font_size(self, delta):
        self.font_size = max(8, min(72, self.font_size + delta))
        self.font_size_lbl.setText(str(self.font_size))
        self.refresh()

    def _on_photo_downloaded(self, data, err):
        if data and not err:
            try:
                tmp = BASE_DIR / f"_photo_{self.req.get('request_id','x')}.jpg"
                with open(tmp, 'wb') as f: f.write(data)
                self.photo_path = str(tmp)
                self.photo_txt.setText("✅ تم التحميل من الطلب")
            except Exception as e: print(f"خطأ حفظ صورة: {e}")
        else: self.photo_txt.setText("لا توجد صورة")
        self.refresh()

    def fill_from_request(self):
        req = self.req
        try: fd = json.loads(req.get('form_data', '{}') or '{}')
        except: fd = {}
        self.inputs['name'].setText(req.get('student_name', '') or '')
        self.inputs['dept'].setText(req.get('dept', '') or '')
        self.inputs['stage'].setText(get_stage(req))
        self.inputs['study_type'].setText(get_study_type(req))
        year = f"{datetime.now().year}-{datetime.now().year+1}"

        if self.template_type == 'A4':
            self.inputs['college'].setText(req.get('college', '') or '')
            self.inputs['academic_year'].setText(year)
            entity = fd.get('اسم الجهة', '').strip()
            if entity: self.inputs['to_text'].setText(f"إلى / {entity}")
            body = (f"نؤيد لكم بأن الطالب/ـة ( {req.get('student_name','')} ) الملصق صورته أعلاه هو/ هي احد طلبة جامعتنا "
                    f"( {req.get('college','')} / {req.get('dept','')} / المرحلة {get_stage(req)} / الدراسة {get_study_type(req)} ) "
                    f"للعام الدراسي {year} ,وبناءاً على طلبه زود بهذا التأييد.")
            self.inputs['body_text'].setPlainText(body)
        elif self.template_type == 'A5':
            self.inputs['college'].setText(req.get('college', '') or '')
            self.inputs['academic_year'].setText(year)
            body = (f"نؤيد لكم ان الطالب/ة ( {req.get('student_name','')} ) في قسم ( {req.get('dept','')} ) "
                    f"المرحلة ( {get_stage(req)} ) و للدراسة ( {get_study_type(req)} ) قد باشر في دراسته للعام الدراسي {year}")
            self.inputs['body_text'].setPlainText(body)
        else:
            self.inputs['college'].setText(req.get('college', '') or '')
            self.inputs['age'].setText(fd.get('العمر', '').strip())
            self.inputs['health_center'].setText(fd.get('المركز الصحي المحال اليه', '').strip())

    def select_photo(self):
        path, _ = QFileDialog.getOpenFileName(self, "اختر صورة", "", "صور (*.png *.jpg *.jpeg)")
        if path:
            self.photo_path = path
            self.photo_txt.setText(Path(path).name)
            self._timer.start()

    def refresh(self):
        if not HAS_PILLOW:
            self.preview.setText("⚠️ ثبّت Pillow")
            return
        try:
            data = {}
            for k, inp in self.inputs.items():
                data[k] = inp.toPlainText() if isinstance(inp, QTextEdit) else inp.text()
            if self.template_type == 'MEDICAL':
                data['stage_line'] = f"{self.inputs['dept'].text()} - {self.inputs['study_type'].text()} / {self.inputs['stage'].text()}"

            img = generate_letter_image(data, self.photo_path, base_font_size=self.font_size, template_type=self.template_type)
            self.current_image = img
            tmp = BASE_DIR / "_preview.png"
            img.save(tmp, "PNG")
            pix = QPixmap(str(tmp))
            if not pix.isNull():
                self.preview.setPixmap(pix.scaled(max(200, self.preview.width()-20), max(300, self.preview.height()-20), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.preview.setText("")
        except Exception as e:
            self.preview.setText(f"⚠️ {e}")

    def print_letter(self):
        if not self.current_image: return
        tmp = BASE_DIR / "_print_temp.png"
        try: self.current_image.save(str(tmp), "PNG")
        except: return

        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.A5) if self.template_type == 'A5' else QPageSize(QPageSize.A4))
        printer.setPageOrientation(QPageLayout.Portrait)
        printer.setPageMargins(QMarginsF(8, 8, 8, 8), QPageLayout.Millimeter)

        dlg = QPrintDialog(printer, self)
        if dlg.exec() != QDialog.Accepted: return

        try:
            pix = QPixmap(str(tmp))
            if pix.isNull(): return
            painter = QPainter(printer)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
            painter.setRenderHint(QPainter.Antialiasing, True)
            rect = painter.viewport()
            size = pix.size()
            size.scale(rect.size(), Qt.KeepAspectRatio)
            painter.setViewport(rect.x(), rect.y(), size.width(), size.height())
            painter.setWindow(pix.rect())
            painter.drawPixmap(0, 0, pix)
            painter.end()
            QMessageBox.information(self, "✅ تم", "تم إرسال الورقة إلى الطابعة")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل الطباعة:\n{e}")

class YearlyLogDialog(QDialog):
    def __init__(self, service, all_requests, parent=None):
        super().__init__(parent)
        self.service = service
        self.svc_reqs = []
        self.setWindowTitle("📚 طباعة السجل السنوي")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumSize(500, 420)
        self.setStyleSheet(f"QDialog {{ background: {COLORS['bg_grad_top']}; }}")

        l = QVBoxLayout(self)
        l.setContentsMargins(25,25,25,25)
        l.setSpacing(12)
        t = QLabel(f"📚  السجل السنوي — {service.get('service_name','')}")
        t.setFont(F(15))
        t.setStyleSheet("color:#a78bfa; background:transparent; border:none;")
        l.addWidget(t)

        h = QLabel("يُطبع 20 طالباً في كل ورقة A4 — يشمل جميع الحالات (المنجزة والمعلقة)")
        h.setFont(F(10, bold=False))
        h.setWordWrap(True)
        h.setStyleSheet(f"color:{COLORS['text_muted']}; background:transparent; border:none;")
        l.addWidget(h)
        l.addSpacing(8)

        combo_style = f"""
            QComboBox {{ background:{COLORS['surface_soft']}; color:{COLORS['text_primary']}; border:1px solid {COLORS['border']};
                border-radius:8px; padding:6px 14px; }}
            QComboBox QAbstractItemView {{ background:{COLORS['surface']}; color:{COLORS['text_primary']}; selection-background-color:#8b5cf6; }}
        """
        lbl1 = QLabel("القسم:")
        lbl1.setFont(F(11))
        lbl1.setStyleSheet(f"color:{COLORS['text_secondary']}; background:transparent; border:none;")
        l.addWidget(lbl1)
        self.dept_combo = QComboBox()
        self.dept_combo.setFont(F(11))
        self.dept_combo.setMinimumHeight(38)
        self.dept_combo.setStyleSheet(combo_style)
        self.dept_combo.addItem("الكل — جميع الأقسام", "ALL")
        l.addWidget(self.dept_combo)

        lbl2 = QLabel("السنة:")
        lbl2.setFont(F(11))
        lbl2.setStyleSheet(f"color:{COLORS['text_secondary']}; background:transparent; border:none;")
        l.addWidget(lbl2)
        self.year_combo = QComboBox()
        self.year_combo.setFont(F(11))
        self.year_combo.setMinimumHeight(38)
        self.year_combo.setStyleSheet(combo_style)
        self.year_combo.addItem("الكل — جميع السنوات", "ALL")
        l.addWidget(self.year_combo)

        self.count_lbl = QLabel("⏳ جاري تحميل كل الطلبات...")
        self.count_lbl.setFont(F(11))
        self.count_lbl.setStyleSheet(f"color:{COLORS['accent']}; background:transparent; border:none; padding:8px;")
        self.count_lbl.setAlignment(Qt.AlignCenter)
        l.addWidget(self.count_lbl)

        self.dept_combo.currentIndexChanged.connect(self._update_count)
        self.year_combo.currentIndexChanged.connect(self._update_count)
        l.addStretch()

        row = QHBoxLayout()
        self.print_btn = QPushButton("🖨️  طباعة")
        self.print_btn.setFont(F(12))
        self.print_btn.setMinimumHeight(44)
        self.print_btn.setCursor(Qt.PointingHandCursor)
        self.print_btn.setEnabled(False)
        self.print_btn.setStyleSheet("""
            QPushButton { background:#8b5cf6; color:white; border-radius:10px; border:none; font-weight:bold; }
            QPushButton:hover:enabled { background:#7c3aed; }
            QPushButton:disabled { background: rgba(100,116,139,0.3); color:#64748b; }
        """)
        self.print_btn.clicked.connect(self.do_print)
        row.addWidget(self.print_btn, 1)

        cb = QPushButton("إلغاء")
        cb.setFont(F(12))
        cb.setMinimumHeight(44)
        cb.setCursor(Qt.PointingHandCursor)
        cb.setStyleSheet(f"QPushButton {{ background:{COLORS['surface_soft']}; color:{COLORS['text_primary']}; border-radius:10px; border:none; }}")
        cb.clicked.connect(self.reject)
        row.addWidget(cb, 1)
        l.addLayout(row)

        self.loader = LoadAllServiceReqsWorker(service.get('service_id'))
        self.loader.done.connect(self._on_all_loaded)
        self.loader.start()

    def _on_all_loaded(self, data, err):
        if err:
            self.count_lbl.setText(f"⚠️ فشل التحميل: {err}")
            return
        self.svc_reqs = data
        self.dept_combo.blockSignals(True)
        self.year_combo.blockSignals(True)
        self.dept_combo.clear()
        self.year_combo.clear()

        depts = sorted(set((r.get('dept') or '').strip() for r in self.svc_reqs if r.get('dept')))
        self.dept_combo.addItem("الكل — جميع الأقسام", "ALL")
        for d in depts: self.dept_combo.addItem(d, d)

        years = set()
        for r in self.svc_reqs:
            dt = parse_ts(r.get('timestamp',''))
            if dt: years.add(dt.year)
        self.year_combo.addItem("الكل — جميع السنوات", "ALL")
        for y in sorted(years, reverse=True): self.year_combo.addItem(str(y), y)

        self.dept_combo.blockSignals(False)
        self.year_combo.blockSignals(False)
        self.print_btn.setEnabled(True)
        self._update_count()

    def _get_filtered(self):
        dept = self.dept_combo.currentData()
        year = self.year_combo.currentData()
        result = []
        for r in self.svc_reqs:
            if dept and dept != "ALL" and (r.get('dept') or '') != dept: continue
            if year and year != "ALL":
                dt = parse_ts(r.get('timestamp',''))
                if not dt or dt.year != year: continue
            result.append(r)
        result.sort(key=lambda r: r.get('timestamp') or '')
        return result

    def _update_count(self):
        f = self._get_filtered()
        self.count_lbl.setText(f"عدد الطلبات: {len(f)} — الصفحات: {(len(f)+19)//20}")

    def do_print(self):
        filtered = self._get_filtered()
        if not filtered: return

        dept = self.dept_combo.currentData()
        year = self.year_combo.currentData()
        dept_lbl = "جميع الأقسام" if dept == "ALL" else dept
        year_lbl = "جميع السنوات" if year == "ALL" else str(year)

        if QMessageBox.question(self, "تأكيد الطباعة",
            f"طباعة {len(filtered)} طلب\n• القسم: {dept_lbl}\n• السنة: {year_lbl}\n• 20 طلاب/ورقة A4\n\nمتابعة؟",
            QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes: return

        html = build_yearly_log_html(filtered, self.service.get('service_name','طلب'), dept_lbl, year_lbl)
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.A4))
        printer.setPageOrientation(QPageLayout.Portrait)
        printer.setPageMargins(QMarginsF(8,8,8,8), QPageLayout.Millimeter)
        dlg = QPrintDialog(printer, self)
        if dlg.exec() == QDialog.Accepted:
            doc = QTextDocument()
            doc.setHtml(html)
            doc.print_(printer)
            # ═══════════════════════════════════════════════════════════
# ويدجت وبطاقات
# ═══════════════════════════════════════════════════════════
class DeleteByRegIdWidget(QFrame):
    delete_requested = Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"QFrame {{ background:{COLORS['surface']}; border-radius:12px; border:1px solid {COLORS['border']}; }}")
        l = QVBoxLayout(self)
        l.setContentsMargins(10,8,10,8)
        l.setSpacing(6)
        t = QLabel("🗑️ حذف طلبات طالب")
        t.setFont(F(10))
        t.setStyleSheet("color:#f87171; background:transparent; border:none;")
        l.addWidget(t)

        row = QHBoxLayout()
        row.setSpacing(5)
        self.reg_input = QLineEdit()
        self.reg_input.setPlaceholderText("رقم التسجيل...")
        self.reg_input.setFont(F(10))
        self.reg_input.setMinimumHeight(30)
        self.reg_input.setStyleSheet(f"QLineEdit {{ background:{COLORS['surface_soft']}; color:{COLORS['text_primary']}; border:1px solid {COLORS['border']}; border-radius:6px; padding:4px 10px; }} QLineEdit:focus {{ border:1px solid #ef4444; }}")
        self.reg_input.returnPressed.connect(self._click)
        row.addWidget(self.reg_input, 1)

        btn = QPushButton("حذف")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFont(F(10))
        btn.setFixedHeight(30)
        btn.setMinimumWidth(55)
        btn.setStyleSheet("QPushButton { background:rgba(239,68,68,0.2); color:#f87171; border:1px solid rgba(239,68,68,0.4); border-radius:6px; font-weight:bold; } QPushButton:hover { background:#dc2626; color:white; }")
        btn.clicked.connect(self._click)
        row.addWidget(btn)
        l.addLayout(row)

    def _click(self):
        txt = self.reg_input.text().strip()
        if txt: self.delete_requested.emit(txt)

class QuickBar(QWidget):
    action = Signal(str)
    def __init__(self, req, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        l = QHBoxLayout(self)
        l.setContentsMargins(0,0,0,0)
        l.setSpacing(6)

        st = req.get('status','pending')
        buttons = []
        if st == 'pending':
            buttons.append(("موافقة", "#2563eb", "approved"))
            buttons.append(("رفض", "#dc2626", "rejected"))
        elif st == 'approved': buttons.append(("جاهز", "#059669", "ready"))
        elif st == 'ready': buttons.append(("تسليم", "#7c3aed", "delivered"))

        for label, color, action in buttons:
            b = QPushButton(label)
            b.setCursor(Qt.PointingHandCursor)
            b.setFont(F(10))
            b.setMinimumHeight(28)
            b.setMinimumWidth(72)
            b.setStyleSheet(f"QPushButton {{ background: {color}; color: white; border-radius: 7px; border: none; padding: 4px 10px; }} QPushButton:hover {{ border: 1px solid rgba(255,255,255,0.3); }}")
            b.clicked.connect(lambda _, a=action: self.action.emit(a))
            l.addWidget(b)
        l.addStretch()

class RequestCard(QFrame):
    clicked      = Signal(dict)
    quick_action = Signal(dict, str)

    def __init__(self, req, request_count=1, parent=None):
        super().__init__(parent)
        self.req = req
        self.setObjectName("reqCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(160)

        st = STATUS_MAP.get(req.get('status','pending'), STATUS_MAP['pending'])
        urg = urgency(req)
        sid = req.get('service_id', '')

        if is_president(sid): accent = "#fbbf24"
        elif sid == "S012": accent = "#a78bfa"
        else: accent = st['color']

        warn = ""
        if urg == 2: accent = "#f97316"; warn = "⚠️ "
        elif urg == 3: accent = "#dc2626"; warn = "🚨 "

        self.setStyleSheet(f"""
            QFrame#reqCard {{
                background: {COLORS['surface']};
                border-radius: 12px;
                border-left: 3px solid {accent};
                border-top: 1px solid {COLORS['border_soft']};
                border-right: 1px solid {COLORS['border_soft']};
                border-bottom: 1px solid {COLORS['border_soft']};
            }}
            QFrame#reqCard:hover {{
                background: {COLORS['surface_hover']};
                border-top: 1px solid {COLORS['border_hover']};
                border-right: 1px solid {COLORS['border_hover']};
                border-bottom: 1px solid {COLORS['border_hover']};
            }}
        """)

        l = QVBoxLayout(self)
        l.setContentsMargins(14,12,14,12)
        l.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(5)
        ic = QLabel(SERVICE_ICONS.get(sid, "📋"))
        ic.setFont(F(16))
        ic.setStyleSheet("background: transparent; border: none;")
        top.addWidget(ic)

        svc = QLabel(warn + (req.get('service_name') or '')[:22])
        svc.setFont(F(11))
        svc.setStyleSheet(f"color:{COLORS['text_primary']}; background:transparent; border:none;")
        top.addWidget(svc, 1)

        if request_count > 1:
            cnt_badge = QLabel(f"🔁 طلب سابق: {request_count}")
            cnt_badge.setFont(F(8))
            cnt_badge.setStyleSheet("color: #fbbf24; background: rgba(251,191,36,0.12); padding: 2px 8px; border-radius: 8px; border: 1px solid rgba(251,191,36,0.3);")
            top.addWidget(cnt_badge)

        badge = QLabel(f"● {st['text']}")
        badge.setFont(F(9))
        badge.setStyleSheet(f"color: {st['color']}; background: {COLORS['surface_soft']}; padding: 2px 8px; border-radius: 8px; border: 1px solid {st['color']}55;")
        top.addWidget(badge)
        l.addLayout(top)

        name = QLabel(req.get('student_name',''))
        name.setFont(F(13))
        name.setStyleSheet(f"color:{COLORS['text_primary']}; background:transparent; border:none;")
        l.addWidget(name)

        if req.get('reg_id'):
            parts = [f"🎫 {req.get('reg_id','')}", (req.get('dept') or '')[:18]]
            if get_stage(req) != '-': parts.append(f"📖 {get_stage(req)}")
            if get_study_type(req) != '-': parts.append(f"🌅 {get_study_type(req)}")
            info_text = "  •  ".join(parts)
        else: info_text = "🆕 زائر"
        info = QLabel(info_text)
        info.setFont(F(10, bold=False))
        info.setStyleSheet(f"color:{COLORS['text_muted']}; background:transparent; border:none;")
        info.setWordWrap(True)
        l.addWidget(info)

        try:
            fd = json.loads(req.get('form_data','{}') or '{}')
            subject = fd.get('موضوع الطلب', '')
            if subject:
                subj = QLabel(f"📌 {subject[:55]}")
                subj.setFont(F(10, bold=False))
                subj.setStyleSheet(f"color:{COLORS['text_secondary']}; background:transparent; border:none;")
                subj.setWordWrap(True)
                l.addWidget(subj)
        except: pass

        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        t = QLabel(time_ago(req.get('timestamp','')))
        t.setFont(F(10, bold=False))
        t.setStyleSheet(f"color:{COLORS['text_dim']}; background:transparent; border:none;")
        bottom.addWidget(t)

        if req.get('image_url'):
            im = QLabel("🖼️")
            im.setFont(F(13))
            im.setStyleSheet(f"color:{COLORS['accent']}; background:transparent; border:none;")
            bottom.addWidget(im)
        if is_paper(sid):
            pp = QLabel("📋")
            pp.setFont(F(13))
            pp.setStyleSheet("color:#d97706; background:transparent; border:none;")
            bottom.addWidget(pp)

        bottom.addStretch()
        self.quick_bar = QuickBar(req)
        self.quick_bar.action.connect(lambda a: self.quick_action.emit(self.req, a))
        bottom.addWidget(self.quick_bar)
        l.addLayout(bottom)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self.clicked.emit(self.req)
        super().mousePressEvent(e)

class DetailDialog(QDialog):
    updated = Signal()

    def __init__(self, req, request_count=1, parent=None):
        super().__init__(parent)
        self.req = req
        self.request_count = request_count
        self._drag_pos = None
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(720, 780)
        self.build_ui()

    def _card(self, accent=None):
        border = f"border-left: 3px solid {accent};" if accent else ""
        f = QFrame()
        f.setStyleSheet(f"QFrame {{ background: {COLORS['surface']}; border-radius: 10px; border: 1px solid {COLORS['border']}; {border} }}")
        return f

    def _selectable_label(self, text, color=None, size=12, bold=False):
        lbl = QLabel(str(text) if text else "—")
        lbl.setFont(F(size, bold=bold))
        lbl.setStyleSheet(f"color:{color or COLORS['text_primary']}; background:transparent; border:none;")
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        lbl.setCursor(Qt.IBeamCursor)
        return lbl

    def build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0,0,0,0)
        c = QFrame()
        c.setObjectName("dlg")
        c.setStyleSheet(f"QFrame#dlg {{ background: {COLORS['bg_grad_top']}; border-radius: 14px; border: 1px solid {COLORS['border']}; }}")
        outer.addWidget(c)
        layout = QVBoxLayout(c)
        layout.setSpacing(12)
        layout.setContentsMargins(26,20,26,20)

        sid = self.req.get('service_id', '')
        header = QHBoxLayout()
        title = QLabel(f"{SERVICE_ICONS.get(sid, '📋')}  {self.req.get('service_name','')}")
        title.setFont(F(16))
        title.setStyleSheet(f"color:{'#fbbf24' if is_president(sid) else COLORS['text_secondary']}; background:transparent; border:none;")
        header.addWidget(title, 1)
        cx = QPushButton("✕")
        cx.setFixedSize(30,30)
        cx.setCursor(Qt.PointingHandCursor)
        cx.setStyleSheet("QPushButton { background: rgba(239,68,68,0.15); color: #f87171; border-radius: 15px; font-weight: bold; border: none; } QPushButton:hover { background: #dc2626; color: white; }")
        cx.clicked.connect(self.reject)
        header.addWidget(cx)
        layout.addLayout(header)

        meta = QLabel(f"رقم الطلب: {self.req.get('request_id','-')}   •   {time_ago(self.req.get('timestamp',''))}")
        meta.setFont(F(10, bold=False))
        meta.setStyleSheet(f"color:{COLORS['text_dim']}; background:transparent; border:none;")
        layout.addWidget(meta)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ background: transparent; border: none; }} QScrollBar:vertical {{ background: transparent; width: 8px; }} QScrollBar::handle:vertical {{ background: {COLORS['border']}; border-radius: 4px; }}")
        inner = QWidget()
        inner.setStyleSheet("background:transparent;")
        il = QVBoxLayout(inner)
        il.setContentsMargins(0,0,8,0)
        il.setSpacing(10)

        il.addWidget(QLabel("💡 يمكنك نسخ أي نص بالنقر عليه واختياره"))

        if self.request_count > 1:
            cnt_card = self._card("#fbbf24")
            ch = QHBoxLayout(cnt_card)
            clbl = QLabel(f"🔁  عدد المرات التي طلب فيها الطالب هذه الخدمة: {self.request_count} مرة")
            clbl.setFont(F(12))
            clbl.setStyleSheet("color:#fbbf24; background:transparent; border:none;")
            ch.addWidget(clbl)
            il.addWidget(cnt_card)

        ic = self._card()
        ig = QGridLayout(ic)
        rows_info = []
        if self.req.get('reg_id'):
            rows_info = [("🎫 رقم التسجيل", str(self.req.get('reg_id','-'))), ("👤 الاسم", self.req.get('student_name','-')), ("🏛️ الكلية", self.req.get('college','-')), ("📚 القسم", self.req.get('dept','-')), ("📖 المرحلة", get_stage(self.req)), ("🌅 نوع الدراسة", get_study_type(self.req))]
        else:
            try: phone = json.loads(self.req.get('form_data','{}') or '{}').get('رقم الهاتف', '-')
            except: phone = '-'
            rows_info = [("👤 الاسم الرباعي", self.req.get('student_name','-')), ("📞 رقم الهاتف", phone)]

        for i, (k, v) in enumerate(rows_info):
            kl = QLabel(k); kl.setFont(F(11, bold=False)); kl.setStyleSheet(f"color:{COLORS['text_dim']}; background:transparent; border:none;")
            ig.addWidget(kl, i, 0)
            ig.addWidget(self._selectable_label(v, size=12), i, 1)
        il.addWidget(ic)

        fc = self._card(); fl = QVBoxLayout(fc)
        ft = QLabel("بيانات النموذج"); ft.setFont(F(12)); ft.setStyleSheet(f"color:{COLORS['text_muted']}; background:transparent; border:none;")
        fl.addWidget(ft)
        try: fd = json.loads(self.req.get('form_data','{}') or '{}')
        except: fd = {}
        visible = {k.replace('image:', '').replace('notes:', ''): v for k, v in fd.items() if not k.startswith('select:') and not k.startswith('_')}

        if not visible:
            e = QLabel("لا توجد بيانات إضافية"); e.setFont(F(11, bold=False)); e.setStyleSheet(f"color:{COLORS['text_dim']}; background:transparent; border:none;")
            fl.addWidget(e)
        else:
            for k, v in visible.items():
                row = QHBoxLayout()
                kl = QLabel(f"{k}"); kl.setFont(F(11, bold=False)); kl.setStyleSheet(f"color:{COLORS['text_dim']}; background:transparent; border:none;"); kl.setMinimumWidth(140)
                txt_val = str(v) if v else "—"
                if len(txt_val) > 80 or '\n' in txt_val:
                    vl = QTextEdit(); vl.setPlainText(txt_val); vl.setReadOnly(True); vl.setFont(F(11, bold=False))
                    vl.setStyleSheet(f"QTextEdit {{ background: {COLORS['surface_soft']}; color:{COLORS['text_primary']}; border:1px solid {COLORS['border']}; border-radius:6px; padding:6px; }}")
                    vl.setMaximumHeight(120)
                    row.addWidget(kl); row.addWidget(vl, 1)
                else:
                    row.addWidget(kl); row.addWidget(self._selectable_label(txt_val, size=12), 1)
                fl.addLayout(row)
        il.addWidget(fc)

        if self.req.get('image_url'):
            img_card = self._card("#38bdf8")
            ih = QHBoxLayout(img_card)
            il1 = QLabel("🖼️  صورة مرفقة"); il1.setFont(F(12)); il1.setStyleSheet("color:#38bdf8; background:transparent; border:none;")
            ih.addWidget(il1, 1)
            view_btn = QPushButton("عرض الصورة"); view_btn.setCursor(Qt.PointingHandCursor); view_btn.setFont(F(11))
            view_btn.setStyleSheet("QPushButton { background: rgba(56,189,248,0.15); color: #38bdf8; border-radius: 8px; border: 1px solid rgba(56,189,248,0.3); padding: 5px 16px; } QPushButton:hover { background: rgba(56,189,248,0.25); }")
            view_btn.clicked.connect(self._open_image)
            ih.addWidget(view_btn)
            il.addWidget(img_card)

        st = STATUS_MAP.get(self.req.get('status','pending'), STATUS_MAP['pending'])
        sc = self._card(st['color']); sh = QHBoxLayout(sc)
        sl = QLabel(f"● الحالة الحالية: {st['text']}"); sl.setFont(F(12)); sl.setStyleSheet(f"color:{st['color']}; background:transparent; border:none;")
        sh.addWidget(sl); il.addWidget(sc)

        nl = QLabel("ملاحظة الموظف (مطلوبة عند الرفض)"); nl.setFont(F(11, bold=False)); nl.setStyleSheet(f"color:{COLORS['text_dim']}; background:transparent; border:none;")
        il.addWidget(nl)
        self.note_edit = QTextEdit(); self.note_edit.setMaximumHeight(75); self.note_edit.setPlaceholderText("اكتب ملاحظة...")
        self.note_edit.setText(self.req.get('employee_note','') or ''); self.note_edit.setFont(F(11, bold=False))
        self.note_edit.setStyleSheet(f"QTextEdit {{ background: {COLORS['surface_soft']}; color:{COLORS['text_primary']}; border:1px solid {COLORS['border']}; border-radius:8px; padding:8px; }}")
        il.addWidget(self.note_edit)
        il.addStretch()

        scroll.setWidget(inner)
        layout.addWidget(scroll, 1)

        btns = QHBoxLayout()
        for text, color, status in [("مراجعة","#d97706","pending"), ("موافقة","#2563eb","approved"), ("جاهز","#059669","ready"), ("تسليم","#7c3aed","delivered"), ("رفض","#dc2626","rejected")]:
            b = QPushButton(text); b.setCursor(Qt.PointingHandCursor); b.setFont(F(11)); b.setMinimumHeight(42)
            b.setStyleSheet(f"QPushButton {{ background:{color}; color:white; border-radius:9px; border:none; padding:8px 12px; font-weight:bold; }} QPushButton:hover {{ border:1px solid rgba(255,255,255,0.3); }}")
            b.clicked.connect(lambda _, s=status: self.update_status(s))
            btns.addWidget(b)
        layout.addLayout(btns)

        if get_letter_type(self.req) is not None and HAS_PILLOW:
            preview_btn = QPushButton("📄  معاينة الورقة الرسمية"); preview_btn.setCursor(Qt.PointingHandCursor); preview_btn.setFont(F(12)); preview_btn.setMinimumHeight(46)
            preview_btn.setStyleSheet("QPushButton { background: #3b82f6; color: white; border-radius: 10px; border: none; padding: 8px 18px; font-weight: bold; } QPushButton:hover { background: #2563eb; }")
            preview_btn.clicked.connect(self.open_letter_preview)
            layout.addWidget(preview_btn)

        print_btn = QPushButton("🖨️  طباعة عادية (HTML)"); print_btn.setCursor(Qt.PointingHandCursor); print_btn.setFont(F(11)); print_btn.setMinimumHeight(36)
        print_btn.setStyleSheet(f"QPushButton {{ background: {COLORS['surface_soft']}; color: {COLORS['text_secondary']}; border-radius: 8px; border: 1px solid {COLORS['border']}; padding: 6px 18px; }} QPushButton:hover {{ background: {COLORS['surface_hover']}; }}")
        print_btn.clicked.connect(self.print_single)
        layout.addWidget(print_btn)

    def open_letter_preview(self):
        LetterPreviewDialog(self.req, self).exec()

    def print_single(self):
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.A4))
        printer.setPageOrientation(QPageLayout.Portrait)
        if QPrintDialog(printer, self).exec() == QDialog.Accepted:
            doc = QTextDocument()
            doc.setHtml(build_print_html([self.req], self.req.get('service_name', 'طلب'), self.req.get('service_id', '')))
            doc.print_(printer)

    def _open_image(self):
        url = self.req.get('image_url')
        if url: ImageViewer(url, self.req.get('request_id',''), "صورة الطلب", self).exec()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and e.position().y() < 55:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept(); return
        super().mousePressEvent(e)
    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos); e.accept()
    def mouseReleaseEvent(self, e):
        self._drag_pos = None; super().mouseReleaseEvent(e)

    def update_status(self, new_status):
        if new_status == "rejected" and not self.note_edit.toPlainText().strip():
            QMessageBox.warning(self, "تنبيه","الرجاء كتابة سبب الرفض."); return
        if QMessageBox.question(self, "تأكيد", f"تغيير حالة الطلب إلى:\n{STATUS_MAP[new_status]['text']}؟", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes: return

        delete_img_name = (self.req.get('image_name') or extract_image_name(self.req.get('image_url'))) if new_status == "delivered" else None
        updates = {
            "status": new_status,
            "employee_note": self.note_edit.toPlainText().strip() or None,
            "processed_by": PROCESSOR_NAME,
            "processed_at": datetime.now().isoformat(),
        }
        if delete_img_name:
            updates["image_url"] = None
            updates["image_name"] = None

        self.worker = UpdateWorker(self.req['request_id'], updates, delete_img_name)
        self.worker.done.connect(self.on_update_done)
        self.worker.start()

    def on_update_done(self, ok, err):
        if ok: self.updated.emit(); self.accept()
        else: QMessageBox.critical(self, "خطأ", f"فشل التحديث:\n{err}")

class ServiceListItem(QFrame):
    clicked = Signal(dict)
    def __init__(self, svc, pending, total, item_h=58, parent=None):
        super().__init__(parent)
        self.svc = svc
        self.setObjectName("svcItem")
        self.setMinimumHeight(item_h)
        self.setMaximumHeight(item_h)
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("selected", "false")
        l = QHBoxLayout(self)
        l.setContentsMargins(8, 4, 8, 4)
        l.setSpacing(8)
        sid = svc.get('service_id','')
        icon = QLabel(SERVICE_ICONS.get(sid, "📋"))
        icon.setFixedSize(30, 30)
        icon.setFont(F(18))
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("background: transparent; border: none;")
        l.addWidget(icon)

        v = QVBoxLayout()
        v.setSpacing(1)
        name = QLabel(svc.get('service_name',''))
        name.setFont(F(9))
        name.setStyleSheet(f"color:{COLORS['text_secondary']}; background:transparent; border:none;")
        name.setWordWrap(True)
        v.addWidget(name)
        sub = QLabel(f"{total} طلب" if total > 0 else "لا طلبات")
        sub.setFont(F(8, bold=False))
        sub.setStyleSheet(f"color:{COLORS['text_dim']}; background:transparent; border:none;")
        v.addWidget(sub)
        l.addLayout(v, 1)

        if pending > 0:
            badge = QLabel(str(pending) if pending < 100 else "99+")
            badge.setFixedHeight(18)
            badge.setMinimumWidth(18)
            badge.setAlignment(Qt.AlignCenter)
            badge.setFont(F(9))
            bg_color = "#f59e0b" if is_president(sid) else "#dc2626"
            badge.setStyleSheet(f"background: {bg_color}; color: white; border-radius: 9px; padding: 0 5px; border: 1px solid rgba(255,255,255,0.15);")
            l.addWidget(badge)

    def set_item_height(self, h):
        self.setMinimumHeight(h)
        self.setMaximumHeight(h)
    def set_selected(self, val: bool):
        self.setProperty("selected", "true" if val else "false")
        self.style().unpolish(self); self.style().polish(self)
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self.clicked.emit(self.svc)

class CompletedLogItem(QFrame):
    clicked      = Signal(dict)
    delete_click = Signal(dict)
    def __init__(self, req, parent=None):
        super().__init__(parent)
        self.req = req
        st = req.get('status','delivered')
        accent = "#10b981" if st == 'delivered' else "#ef4444"
        icon_char = "✓" if st == 'delivered' else "✕"
        self.setObjectName("logItem")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(52)
        self.setMaximumHeight(52)
        self.setStyleSheet(f"""
            QFrame#logItem {{ background: {COLORS['surface_soft']}; border-radius: 8px; border: 1px solid {COLORS['border_soft']}; }}
            QFrame#logItem:hover {{ background: {COLORS['surface_hover']}; border: 1px solid {COLORS['border']}; }}
        """)
        l = QHBoxLayout(self)
        l.setContentsMargins(10, 5, 10, 5)
        l.setSpacing(6)

        ic = QLabel(SERVICE_ICONS.get(req.get('service_id',''), "📋"))
        ic.setFixedSize(26, 26)
        ic.setFont(F(14))
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("background: transparent; border: none;")
        l.addWidget(ic)

        v = QVBoxLayout()
        v.setSpacing(0)
        name = QLabel((req.get('student_name') or '')[:18])
        name.setFont(F(10))
        name.setStyleSheet(f"color:{COLORS['text_secondary']}; background:transparent; border:none;")
        name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        name.setMinimumWidth(1)
        v.addWidget(name)
        
        ts = req.get('processed_at') or req.get('timestamp') or ''
        sub = QLabel(f"{req.get('reg_id','')} • {time_ago(ts)}")
        sub.setFont(F(8, bold=False))
        sub.setStyleSheet(f"color:{COLORS['text_dim']}; background:transparent; border:none;")
        sub.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        sub.setMinimumWidth(1)
        v.addWidget(sub)
        l.addLayout(v, 1)

        mark = QLabel(icon_char)
        mark.setFixedSize(22, 22)
        mark.setFont(F(12))
        mark.setAlignment(Qt.AlignCenter)
        mark.setStyleSheet(f"color: white; background: {accent}; border-radius: 11px; border: none; font-weight: bold;")
        l.addWidget(mark)

        del_btn = QPushButton("🗑")
        del_btn.setFixedSize(30, 30)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet("QPushButton { background: rgba(239,68,68,0.25); color: #ef4444; border-radius: 8px; border: 1px solid rgba(239,68,68,0.45); font-size: 14px; font-weight: bold; } QPushButton:hover { background: #dc2626; color: white; border: 1px solid #dc2626; }")
        del_btn.clicked.connect(lambda: self.delete_click.emit(self.req))
        l.addWidget(del_btn)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self.clicked.emit(self.req)
        super().mousePressEvent(e)
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(f"QMenu {{ background: {COLORS['surface']}; color: {COLORS['text_primary']}; border: 1px solid {COLORS['border']}; border-radius: 8px; padding: 4px; }} QMenu::item {{ padding: 8px 24px; border-radius: 6px; }} QMenu::item:selected {{ background: #dc2626; color: white; }}")
        open_action = menu.addAction("👁️  فتح الطلب")
        menu.addSeparator()
        del_action = menu.addAction("🗑️  حذف الطلب")
        chosen = menu.exec(event.globalPos())
        if chosen == open_action: self.clicked.emit(self.req)
        elif chosen == del_action:
            if QMessageBox.question(self, "تأكيد الحذف", f"هل أنت متأكد من حذف الطلب؟\n\nالطالب: {self.req.get('student_name','')}", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
                self.delete_click.emit(self.req)

# ═══════════════════════════════════════════════════════════
# السجل
# ═══════════════════════════════════════════════════════════
class CompletedLog(QFrame):
    request_clicked    = Signal(dict)
    delete_clicked     = Signal(dict)
    batch_delete_asked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['surface']};
                border-radius: 14px;
                border: 1px solid {COLORS['border']};
            }}
        """)

        self.all_archived = []
        l = QVBoxLayout(self)
        l.setContentsMargins(10,10,10,10)
        l.setSpacing(8)

        hdr = QHBoxLayout()
        hdr.setSpacing(6)
        ttl = QLabel("السجل")
        ttl.setFont(F(12))
        ttl.setStyleSheet(f"color:{COLORS['text_secondary']}; background:transparent; border:none;")
        hdr.addWidget(ttl)
        hdr.addStretch()

        self.batch_del_btn = QPushButton("🗑️ 100")
        self.batch_del_btn.setFixedHeight(22)
        self.batch_del_btn.setMinimumWidth(55)
        self.batch_del_btn.setCursor(Qt.PointingHandCursor)
        self.batch_del_btn.setToolTip("حذف آخر 100 طلب من السجل")
        self.batch_del_btn.setStyleSheet("""
            QPushButton { color: #f87171; background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.3); border-radius: 6px; font-size: 10px; font-weight: bold; }
            QPushButton:hover { background: #dc2626; color: white; }
        """)
        self.batch_del_btn.clicked.connect(self.batch_delete_asked.emit)
        hdr.addWidget(self.batch_del_btn)

        self.deliv_lbl = QLabel("✓ 0")
        self.deliv_lbl.setFont(F(9))
        self.deliv_lbl.setStyleSheet("color: #10b981; background: rgba(16,185,129,0.1); padding: 2px 8px; border-radius: 8px; border: 1px solid rgba(16,185,129,0.2);")
        self.deliv_lbl.setAlignment(Qt.AlignCenter)
        hdr.addWidget(self.deliv_lbl)

        self.rej_lbl = QLabel("✕ 0")
        self.rej_lbl.setFont(F(9))
        self.rej_lbl.setStyleSheet("color: #ef4444; background: rgba(239,68,68,0.1); padding: 2px 8px; border-radius: 8px; border: 1px solid rgba(239,68,68,0.2);")
        self.rej_lbl.setAlignment(Qt.AlignCenter)
        hdr.addWidget(self.rej_lbl)
        l.addLayout(hdr)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 بحث باسم الطالب...")
        self.search_input.setFont(F(10, bold=False))
        self.search_input.setMinimumHeight(32)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{ background: {COLORS['surface_soft']}; color: {COLORS['text_primary']}; border: 1px solid {COLORS['border']}; border-radius: 8px; padding: 4px 12px; }}
            QLineEdit:focus {{ border: 1px solid {COLORS['accent']}; }}
        """)
        self.search_input.textChanged.connect(self.filter_log)
        l.addWidget(self.search_input)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{ background:transparent; border:none; }}
            QScrollBar:vertical {{ background:transparent; width:6px; }}
            QScrollBar::handle:vertical {{ background: {COLORS['border']}; border-radius:3px; min-height:25px; }}
            QScrollBar::handle:vertical:hover {{ background: {COLORS['border_hover']}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
            QScrollBar:horizontal {{ height: 0px; }}
        """)

        self.list_w = QWidget()
        self.list_w.setStyleSheet("background:transparent;")
        self.list_l = QVBoxLayout(self.list_w)
        self.list_l.setContentsMargins(0,0,0,0)
        self.list_l.setSpacing(4)
        self.list_l.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.list_w)
        l.addWidget(self.scroll, 1)

    def update_data(self, all_reqs):
        archived = [r for r in all_reqs if is_archived(r)]
        archived.sort(key=lambda r: r.get('processed_at') or r.get('timestamp') or '', reverse=True)

        n_deliv = sum(1 for r in archived if r.get('status') == 'delivered')
        n_rej   = sum(1 for r in archived if r.get('status') == 'rejected')
        self.deliv_lbl.setText(f"✓ {n_deliv}")
        self.rej_lbl.setText(f"✕ {n_rej}")

        self.all_archived = archived
        self.filter_log(self.search_input.text())

    def filter_log(self, text):
        text = text.strip().lower()
        while self.list_l.count():
            it = self.list_l.takeAt(0)
            w = it.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        filtered = self.all_archived
        if text:
            filtered = [r for r in self.all_archived if text in (r.get('student_name') or '').lower()]

        if not filtered:
            msg = "لا توجد نتائج مطابقة" if text else "لا توجد طلبات منجزة بعد"
            e = QLabel(msg)
            e.setFont(F(10, bold=False))
            e.setStyleSheet(f"color:{COLORS['text_dim']}; background:transparent; border:none; padding:20px;")
            e.setAlignment(Qt.AlignCenter)
            self.list_l.addWidget(e)
            return

        for r in filtered[:50]:
            item = CompletedLogItem(r)
            item.clicked.connect(self.request_clicked.emit)
            item.delete_click.connect(self.delete_clicked.emit)
            self.list_l.addWidget(item)

# ═══════════════════════════════════════════════════════════
# قائمة الخدمات
# ═══════════════════════════════════════════════════════════
class ServicesList(QFrame):
    service_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(SIDEBAR_WIDTH)
        self.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['surface']};
                border-radius: 14px;
                border: 1px solid {COLORS['border']};
            }}
        """)

        l = QVBoxLayout(self)
        l.setContentsMargins(8,10,8,10)
        l.setSpacing(8)

        hdr = QHBoxLayout()
        ttl = QLabel("الخدمات")
        ttl.setFont(F(12))
        ttl.setStyleSheet(f"color:{COLORS['text_secondary']}; background:transparent; border:none;")
        hdr.addWidget(ttl)
        hdr.addStretch()
        self.count_lbl = QLabel("")
        self.count_lbl.setFont(F(9, bold=False))
        self.count_lbl.setStyleSheet("color:#ef4444; background:transparent; border:none;")
        hdr.addWidget(self.count_lbl)
        l.addLayout(hdr)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{ background:transparent; border:none; }}
            QScrollBar:vertical {{ background:transparent; width:3px; }}
            QScrollBar::handle:vertical {{ background: {COLORS['border']}; border-radius:2px; min-height:20px; }}
            QScrollBar::handle:vertical:hover {{ background: {COLORS['border_hover']}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
            QScrollBar:horizontal {{ height: 0px; }}
        """)
        self.list_w = QWidget()
        self.list_w.setStyleSheet(f"""
            QWidget {{ background: transparent; }}
            QFrame#svcItem {{ background: {COLORS['surface_soft']}; border-radius: 10px; border: 1px solid {COLORS['border_soft']}; }}
            QFrame#svcItem:hover {{ background: {COLORS['surface_hover']}; border: 1px solid {COLORS['border']}; }}
            QFrame#svcItem[selected="true"] {{ background: {COLORS['accent_soft']}; border: 1px solid {COLORS['accent']}; }}
        """)
        self.list_l = QVBoxLayout(self.list_w)
        self.list_l.setContentsMargins(0,0,0,0)
        self.list_l.setSpacing(4)
        self.list_l.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.list_w)
        l.addWidget(self.scroll, 1)

        self.items = []
        self.selected = None
        self.services = []
        self.all_reqs = []

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adjust_heights()

    def _adjust_heights(self):
        n = len(self.items)
        if n == 0: return
        avail = self.scroll.viewport().height() - 10
        item_h = (avail - (n - 1) * 4) // n
        item_h = max(44, min(72, item_h))
        for it in self.items:
            it.set_item_height(item_h)

    def update_data(self, services, all_reqs):
        while self.list_l.count():
            it = self.list_l.takeAt(0)
            w = it.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
                
        self.items = []
        self.services = services
        self.all_reqs = all_reqs

        if not services:
            e = QLabel("جاري التحميل...")
            e.setFont(F(11))
            e.setStyleSheet(f"color:{COLORS['text_dim']}; background:transparent; border:none; padding:20px;")
            e.setAlignment(Qt.AlignCenter)
            self.list_l.addWidget(e)
            self.count_lbl.setText("")
            return

        def key(s):
            sid = s.get('service_id')
            pend = sum(1 for r in all_reqs if r.get('service_id')==sid and r.get('status')=='pending')
            return (-pend, s.get('sort_order', 999))

        ordered = sorted(services, key=key)
        total_pending = 0

        for svc in ordered:
            sid = svc.get('service_id')
            pend = sum(1 for r in all_reqs if r.get('service_id')==sid and r.get('status')=='pending')
            tot = sum(1 for r in all_reqs if r.get('service_id')==sid and not is_archived(r))
            total_pending += pend

            it = ServiceListItem(svc, pend, tot, item_h=52)
            it.clicked.connect(self._on_click)
            self.list_l.addWidget(it)
            self.items.append(it)

        self.count_lbl.setText(f"{total_pending} معلّق" if total_pending else "")
        QTimer.singleShot(50, self._adjust_heights)

        if self.selected:
            for it in self.items:
                if it.svc.get('service_id') == self.selected.get('service_id'):
                    it.set_selected(True)
                    break

    def _on_click(self, svc):
        self.selected = svc
        for it in self.items:
            it.set_selected(it.svc.get('service_id') == svc.get('service_id'))
        self.service_selected.emit(svc)

    def select_first(self):
        if not self.selected and self.items:
            self._on_click(self.items[0].svc)

    def move_selection(self, step):
        if not self.items: return
        cur = -1
        for i, it in enumerate(self.items):
            if self.selected and it.svc.get('service_id') == self.selected.get('service_id'):
                cur = i
                break
        nxt = max(0, min(cur + step, len(self.items) - 1))
        self._on_click(self.items[nxt].svc)
        self.scroll.ensureWidgetVisible(self.items[nxt])

# ═══════════════════════════════════════════════════════════
# لوحة الطلبات
# ═══════════════════════════════════════════════════════════
class RequestsPanel(QWidget):
    detail_requested = Signal(dict)
    quick_action     = Signal(dict, str)
    refresh_clicked  = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        self.service = None
        self.all_requests = []
        self.current_filter = "all"
        self.search_text = ""
        self.cards = []
        self.selected_idx = -1
        self.current_displayed = []
        self.last_batch = []

        l = QVBoxLayout(self)
        l.setContentsMargins(0,0,0,0)
        l.setSpacing(8)

        head = QHBoxLayout()
        self.title = QLabel("اختر خدمة من القائمة")
        self.title.setFont(F(15))
        self.title.setStyleSheet(f"color:{COLORS['text_secondary']}; background:transparent; border:none;")
        head.addWidget(self.title, 1)

        self.last_upd = QLabel("")
        self.last_upd.setFont(F(9, bold=False))
        self.last_upd.setStyleSheet(f"color:{COLORS['text_dim']}; background:transparent; border:none;")
        head.addWidget(self.last_upd)

        self.refresh_btn = QPushButton("↻")
        self.refresh_btn.setFixedSize(32,32)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.setToolTip("تحديث (F5)")
        self.refresh_btn.setStyleSheet("""
            QPushButton { background: rgba(16,185,129,0.12); color:#10b981; border-radius:16px; font-size:16px; border:1px solid rgba(16,185,129,0.2); }
            QPushButton:hover { background: rgba(16,185,129,0.25); }
        """)
        self.refresh_btn.clicked.connect(self.refresh_clicked.emit)
        head.addWidget(self.refresh_btn)
        l.addLayout(head)

        fr = QHBoxLayout()
        fr.setSpacing(6)
        self.f_btns = {}
        for k, txt, c in [("all","الكل","#64748b"), ("pending","قيد المراجعة","#d97706"), ("approved","موافق","#2563eb"), ("ready","جاهز","#059669")]:
            b = QPushButton(txt)
            b.setCursor(Qt.PointingHandCursor)
            b.setCheckable(True)
            b.setFont(F(10))
            b.setProperty("k", k)
            b.setProperty("c", c)
            b.clicked.connect(lambda _, x=k: self.set_filter(x))
            self.f_btns[k] = b
            fr.addWidget(b)

        self.type_combo = QComboBox()
        self.type_combo.addItem("الكل", "all")
        self.type_combo.addItem("🎓 طالب منتسب", "طالب منتسب")
        self.type_combo.addItem("🆕 قبول جديد", "قبول جديد")
        self.type_combo.setFont(F(10))
        self.type_combo.setFixedWidth(150)
        self.type_combo.setStyleSheet(f"""
            QComboBox {{ background: {COLORS['surface_soft']}; color: {COLORS['text_primary']}; border: 1px solid {COLORS['border']}; border-radius: 14px; padding: 5px 12px; }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{ background: {COLORS['surface']}; color: {COLORS['text_primary']}; selection-background-color: {COLORS['accent']}; }}
        """)
        self.type_combo.currentIndexChanged.connect(lambda: self.render())
        fr.addWidget(self.type_combo)
        fr.addStretch()

        self.search = QLineEdit()
        self.search.setPlaceholderText("بحث...")
        self.search.setFixedWidth(200)
        self.search.setFont(F(11, bold=False))
        self.search.setStyleSheet(f"""
            QLineEdit {{ background: {COLORS['surface_soft']}; color:{COLORS['text_primary']}; border:1px solid {COLORS['border']}; border-radius:14px; padding:7px 15px; }}
            QLineEdit:focus {{ border:1px solid {COLORS['border_hover']}; }}
        """)
        self.search.textChanged.connect(self.on_search)
        fr.addWidget(self.search)
        l.addLayout(fr)

        self.batch_bar = QFrame()
        self.batch_bar.setStyleSheet("QFrame { background: rgba(37,99,235,0.10); border-radius: 10px; border: 1px solid rgba(37,99,235,0.30); }")
        self.batch_bar.setMinimumHeight(46)
        bbl = QHBoxLayout(self.batch_bar)
        bbl.setContentsMargins(12,4,12,4)
        bbl.setSpacing(8)
        bbl.addWidget(QLabel("⚡"))
        blbl = QLabel("تغيير حالة الطلبات:")
        blbl.setFont(F(10, bold=False))
        blbl.setStyleSheet("color:#93c5fd; background:transparent; border:none;")
        bbl.addWidget(blbl)

        for text, color, status in [("✅  موافقة", "#2563eb", "approved"), ("📦  جاهز", "#10b981", "ready"), ("🎉  تسليم", "#8b5cf6", "delivered")]:
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFont(F(11))
            btn.setFixedHeight(32)
            btn.setMinimumWidth(110)
            btn.setStyleSheet(f"QPushButton {{ background: {color}; color: white; border-radius: 8px; border: 2px solid {color}; padding: 4px 18px; font-weight: bold; }} QPushButton:hover {{ background: white; color: {color}; }}")
            btn.clicked.connect(lambda _, s=status: self.batch_change_status(s))
            bbl.addWidget(btn)

        bbl.addStretch()

        self.undo_btn = QPushButton("↩️  رجوع خطوة")
        self.undo_btn.setCursor(Qt.PointingHandCursor)
        self.undo_btn.setFont(F(11))
        self.undo_btn.setFixedHeight(32)
        self.undo_btn.setMinimumWidth(120)
        self.undo_btn.setEnabled(False)
        self.undo_btn.setStyleSheet("""
            QPushButton { background: #d97706; color: white; border-radius: 8px; border: 2px solid #d97706; padding: 4px 16px; font-weight: bold; }
            QPushButton:hover:enabled { background: white; color: #d97706; }
            QPushButton:disabled { background: rgba(100,116,139,0.3); color: #64748b; border: 2px solid rgba(100,116,139,0.3); }
        """)
        self.undo_btn.clicked.connect(self.undo_last_batch)
        bbl.addWidget(self.undo_btn)
        l.addWidget(self.batch_bar)

        self.print_bar = QFrame()
        self.print_bar.setStyleSheet("QFrame { background: rgba(251,191,36,0.10); border-radius: 10px; border: 1px solid rgba(251,191,36,0.30); }")
        self.print_bar.setMinimumHeight(46)
        pbl = QHBoxLayout(self.print_bar)
        pbl.setContentsMargins(14,4,14,4)
        pbl.setSpacing(10)
        pbl.addWidget(QLabel("🖨️"))
        pbl_info = QLabel("طباعة — كل طلب في ورقة A4 كاملة")
        pbl_info.setFont(F(10, bold=False))
        pbl_info.setStyleSheet("color:#fbbf24; background:transparent; border:none;")
        pbl.addWidget(pbl_info, 1)

        self.print_all_btn = QPushButton("🖨️  طباعة الكل")
        self.print_all_btn.setCursor(Qt.PointingHandCursor)
        self.print_all_btn.setFont(F(11))
        self.print_all_btn.setFixedHeight(34)
        self.print_all_btn.setMinimumWidth(160)
        self.print_all_btn.setStyleSheet("QPushButton { background: #fbbf24; color: #0b1220; border-radius: 8px; border: 2px solid #fbbf24; padding: 5px 20px; font-weight: bold; } QPushButton:hover { background: white; color: #b45309; border: 2px solid #fbbf24; }")
        self.print_all_btn.clicked.connect(self.print_all)
        pbl.addWidget(self.print_all_btn)

        self.print_yearly_btn = QPushButton("📚  السجل السنوي")
        self.print_yearly_btn.setCursor(Qt.PointingHandCursor)
        self.print_yearly_btn.setFont(F(11))
        self.print_yearly_btn.setFixedHeight(34)
        self.print_yearly_btn.setMinimumWidth(160)
        self.print_yearly_btn.setStyleSheet("QPushButton { background:#8b5cf6; color:white; border-radius:8px; border:2px solid #8b5cf6; padding:5px 20px; font-weight:bold; } QPushButton:hover { background:white; color:#7c3aed; }")
        self.print_yearly_btn.clicked.connect(self.print_yearly_log)
        pbl.addWidget(self.print_yearly_btn)
        l.addWidget(self.print_bar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{ background:transparent; border:none; }}
            QScrollBar:vertical {{ background:transparent; width:8px; }}
            QScrollBar::handle:vertical {{ background: {COLORS['border']}; border-radius:4px; min-height:30px; }}
            QScrollBar::handle:vertical:hover {{ background: {COLORS['border_hover']}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
        """)
        self.req_w = QWidget()
        self.req_w.setStyleSheet("background:transparent;")
        self.grid = QGridLayout(self.req_w)
        self.grid.setSpacing(8)
        self.grid.setContentsMargins(2,2,2,2)
        self.grid.setAlignment(Qt.AlignTop)
        self.grid.setColumnStretch(0, 1)
        self.scroll.setWidget(self.req_w)
        l.addWidget(self.scroll, 1)

        hint = QLabel("↑↓ خدمات  •  ←→ بطاقات  •  Enter فتح  •  A موافقة  •  R رفض  •  S جاهز  •  D تسليم  •  F5 تحديث  •  / بحث")
        hint.setFont(F(9, bold=False))
        hint.setStyleSheet(f"color:{COLORS['text_dim']}; background:transparent; border:none;")
        hint.setAlignment(Qt.AlignCenter)
        l.addWidget(hint)

        self.batch_bar.hide()
        self.type_combo.hide()
        self.set_filter("all")
        self.show_welcome()

    def print_yearly_log(self):
        if not self.service: return
        YearlyLogDialog(self.service, self.all_requests, self).exec()

    def print_all(self):
        reqs = sorted(self.current_displayed, key=lambda r: r.get('timestamp',''))
        if not reqs:
            QMessageBox.warning(self, "تنبيه", "لا توجد طلبات للطباعة في هذا الفلتر")
            return
        self._print_requests(reqs)

    def _print_requests(self, reqs):
        if not self.service: return
        confirm = QMessageBox.question(self, "تأكيد الطباعة", f"سيتم طباعة {len(reqs)} طلب\n• كل طلب في ورقة A4 كاملة\n\nهل تريد المتابعة؟", QMessageBox.Yes | QMessageBox.No)
        if confirm != QMessageBox.Yes: return

        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.A4))
        printer.setPageOrientation(QPageLayout.Portrait)
        printer.setPageMargins(QMarginsF(12, 12, 12, 12), QPageLayout.Millimeter)

        dlg = QPrintDialog(printer, self)
        if dlg.exec() == QDialog.Accepted:
            doc = QTextDocument()
            doc.setHtml(build_print_html(reqs, self.service.get('service_name', 'طلب'), self.service.get('service_id', '')))
            doc.print_(printer)

    def batch_change_status(self, new_status):
        reqs = [r for r in self.current_displayed if r.get('status') != new_status]
        if not reqs:
            QMessageBox.information(self, "تنبيه", "جميع الطلبات في هذه الحالة")
            return
        if QMessageBox.question(self, "تأكيد التغيير الجماعي", f"سيتم تغيير حالة {len(reqs)} طلب إلى:\n\n👉 {STATUS_MAP[new_status]['text']}", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes: return

        self.last_batch = [(r['request_id'], r.get('status', 'pending')) for r in reqs]
        self.undo_btn.setEnabled(True)
        now_iso = datetime.now().isoformat()
        updates_list = []
        for r in reqs:
            up = {"status": new_status, "processed_by": PROCESSOR_NAME, "processed_at": now_iso}
            if new_status == "delivered":
                img = (r.get('image_name') or extract_image_name(r.get('image_url')))
                if img:
                    up["image_url"] = None
                    up["image_name"] = None
                    try: delete_image_from_storage(img)
                    except: pass
            updates_list.append((r['request_id'], up))

        self.batch_worker = BatchUpdateWorker(updates_list)
        self.batch_worker.done.connect(self._on_batch_done)
        self.batch_worker.start()

    def _on_batch_done(self, ok, count, err):
        if ok: QMessageBox.information(self, "✅ تم", f"تم تحديث {count} طلب بنجاح")
        else: QMessageBox.critical(self, "خطأ", f"فشل:\n{err}")
        self.refresh_clicked.emit()

    def undo_last_batch(self):
        if not self.last_batch: return
        if QMessageBox.question(self, "تأكيد الرجوع", f"سيتم إرجاع {len(self.last_batch)} طلب لحالتها السابقة", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes: return
        
        now_iso = datetime.now().isoformat()
        updates_list = [(rid, {"status": old_status, "processed_by": PROCESSOR_NAME, "processed_at": now_iso}) for rid, old_status in self.last_batch]
        self.batch_worker = BatchUpdateWorker(updates_list)
        self.batch_worker.done.connect(self._on_undo_done)
        self.batch_worker.start()

    def _on_undo_done(self, ok, count, err):
        if ok:
            QMessageBox.information(self, "✅ تم الرجوع", f"تم إرجاع {count} طلب")
            self.last_batch = []
            self.undo_btn.setEnabled(False)
        else: QMessageBox.critical(self, "خطأ", f"فشل:\n{err}")
        self.refresh_clicked.emit()

    def show_welcome(self):
        self._clear_grid()
        w = QLabel("اختر خدمة من القائمة على اليمين\nلعرض طلباتها")
        w.setFont(F(14))
        w.setStyleSheet(f"color:{COLORS['text_dim']}; background:transparent; border:none; padding:80px;")
        w.setAlignment(Qt.AlignCenter)
        self.grid.addWidget(w, 0, 0, 1, 1)
        self.title.setText("اختر خدمة من القائمة")

    def open_service(self, svc, all_reqs):
        self.service = svc
        self.all_requests = all_reqs
        self.title.setText(f"{SERVICE_ICONS.get(svc.get('service_id',''), '📋')}  {svc.get('service_name','')}")
        self.search.clear()
        self.search_text = ""
        self.batch_bar.show()
        self.print_bar.show()
        if is_president(svc.get('service_id','')):
            self.type_combo.show()
            self.type_combo.setCurrentIndex(0)
        else:
            self.type_combo.hide()
        self.set_filter("all")
        self.render()

    def update_requests(self, all_reqs):
        self.all_requests = all_reqs
        self._update_counts()
        self.render()

    def _svc_reqs(self):
        if not self.service: return []
        sid = self.service.get('service_id')
        return [r for r in self.all_requests if r.get('service_id') == sid and not is_archived(r)]

    def _update_counts(self):
        svc = self._svc_reqs()
        cnt = {k:0 for k in STATUS_MAP}
        for r in svc:
            st = r.get('status','pending')
            if st in cnt: cnt[st] += 1
        lbl = {"all": f"الكل ({len(svc)})", "pending": f"قيد المراجعة ({cnt['pending']})", "approved": f"موافق ({cnt['approved']})", "ready": f"جاهز ({cnt['ready']})"}
        for k, b in self.f_btns.items():
            b.setText(lbl.get(k, b.text()))

    def set_filter(self, k):
        self.current_filter = k
        for kk, b in self.f_btns.items():
            on = (kk == k)
            b.setChecked(on)
            c = b.property("c")
            if on:
                b.setStyleSheet(f"QPushButton {{ background: {c}22; color:{c}; border: 1px solid {c}66; padding:6px 14px; border-radius:14px; font-weight:bold; }}")
            else:
                b.setStyleSheet(f"QPushButton {{ background: {COLORS['surface_soft']}; color:{COLORS['text_muted']}; border: 1px solid {COLORS['border_soft']}; padding:6px 14px; border-radius:14px; }} QPushButton:hover {{ background: {COLORS['surface_hover']}; color:{COLORS['text_primary']}; }}")

        filter_names = {"all": "طباعة الكل", "pending": "طباعة قيد المراجعة", "approved": "طباعة الموافق عليها", "ready": "طباعة الجاهزة"}
        if hasattr(self, 'print_all_btn'):
            self.print_all_btn.setText(f"🖨️  {filter_names.get(k, 'طباعة الكل')}")
        self.render()

    def on_search(self, t):
        self.search_text = t.strip().lower()
        self.render()

    def _clear_grid(self):
        while self.grid.count():
            it = self.grid.takeAt(0)
            w = it.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

    def render(self):
        if not self.service: return
        self._clear_grid()
        self.cards = []

        filtered = self._svc_reqs()
        if self.current_filter != "all":
            filtered = [r for r in filtered if r.get('status') == self.current_filter]
        if is_president(self.service.get('service_id','')):
            type_filter = self.type_combo.currentData()
            if type_filter and type_filter != "all":
                filtered = [r for r in filtered if get_request_type(r) == type_filter]
        if self.search_text:
            s = self.search_text
            new_filtered = []
            for r in filtered:
                if (s in str(r.get('request_id','')).lower() or s in str(r.get('reg_id','')).lower() or s in (r.get('student_name') or '').lower() or s in (r.get('college') or '').lower() or s in (r.get('dept') or '').lower()):
                    new_filtered.append(r)
                    continue
                try:
                    fd = json.loads(r.get('form_data','{}') or '{}')
                    for v in fd.values():
                        if s in str(v).lower():
                            new_filtered.append(r)
                            break
                except: pass
            filtered = new_filtered

        filtered = sorted(filtered, key=priority, reverse=True)
        self.current_displayed = list(filtered)

        if not filtered:
            m = "لا توجد طلبات في هذا الفلتر"
            e = QLabel(m)
            e.setFont(F(14))
            e.setStyleSheet(f"color:{COLORS['text_dim']}; background:transparent; border:none; padding:60px;")
            e.setAlignment(Qt.AlignCenter)
            self.grid.addWidget(e, 0, 0, 1, 1)
            return

        for i, r in enumerate(filtered[:100]):
            reg_id = r.get('reg_id')
            svc_id = r.get('service_id')
            count = sum(1 for req in self.all_requests if req.get('reg_id') == reg_id and req.get('service_id') == svc_id) if reg_id else 1
            c = RequestCard(r, request_count=count)
            c.clicked.connect(self.detail_requested.emit)
            c.quick_action.connect(self.quick_action.emit)
            self.grid.addWidget(c, i, 0)
            self.cards.append(c)

        if self.cards:
            self.selected_idx = 0
            self._highlight()

    def _highlight(self):
        for i, c in enumerate(self.cards):
            if i == self.selected_idx:
                c.setStyleSheet(c.styleSheet().replace(COLORS['surface'], COLORS['accent_soft']))
            else:
                c.setStyleSheet(c.styleSheet().replace(COLORS['accent_soft'], COLORS['surface']))

    def move_card_selection(self, step):
        if not self.cards: return
        self.selected_idx = max(0, min(self.selected_idx + step, len(self.cards) - 1))
        self._highlight()
        self.scroll.ensureWidgetVisible(self.cards[self.selected_idx])

# ═══════════════════════════════════════════════════════════
# النافذة الرئيسية
# ═══════════════════════════════════════════════════════════
_main_window_ref = None

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("شاشة استقبال الطلبات - جامعة الناجي")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.services_list = []
        self.all_requests = []
        self.seen_ids = set()
        self.first_load = True
        self.loading = False
        self._drag_pos = None

        self.sound_effect = None
        if HAS_SOUND and SOUND_FILE.exists():
            self.sound_effect = QSoundEffect()
            self.sound_effect.setSource(QUrl.fromLocalFile(str(SOUND_FILE)))
            self.sound_effect.setVolume(0.6)

        central = QWidget()
        self.setCentralWidget(central)
        central.setAttribute(Qt.WA_TranslucentBackground)
        self.particles = ParticleBackground(central)

        ml = QHBoxLayout(central)
        ml.setContentsMargins(10,10,10,10)
        ml.setSpacing(8)

        left_col = QWidget()
        left_col.setFixedWidth(240)
        left_col.setStyleSheet("background:transparent;")
        left_l = QVBoxLayout(left_col)
        left_l.setContentsMargins(0,0,0,0)
        left_l.setSpacing(10)

        self.clock = SmartClock()
        left_l.addWidget(self.clock, 0)

        self.delete_by_regid = DeleteByRegIdWidget()
        self.delete_by_regid.delete_requested.connect(self._delete_by_regid)
        left_l.addWidget(self.delete_by_regid, 0)

        self.completed_log = CompletedLog()
        left_l.addWidget(self.completed_log, 1)

        ml.addWidget(left_col, 0)

        content = QFrame()
        content.setStyleSheet(f"QFrame {{ background: {COLORS['surface']}; border-radius: 16px; border: 1px solid {COLORS['border']}; }}")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(14,12,14,12)
        cl.setSpacing(12)

        top = QHBoxLayout()
        header = QLabel("استقبال الطلبات الإلكترونية")
        header.setFont(F(16))
        header.setStyleSheet(f"color:{COLORS['text_primary']}; background:transparent; border:none;")
        top.addWidget(header)
        top.addStretch()

        self.last_update_lbl = QLabel("")
        self.last_update_lbl.setFont(F(10, bold=False))
        self.last_update_lbl.setStyleSheet(f"color:{COLORS['text_dim']}; background:transparent; border:none;")
        top.addWidget(self.last_update_lbl)
        top.addSpacing(12)

        self.theme_btn = QPushButton("☀️" if SETTINGS.get("theme") == "dark" else "🌙")
        self.theme_btn.setFixedSize(32,32)
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.setToolTip("تبديل الوضع الليلي/النهاري")
        self.theme_btn.setStyleSheet(f"QPushButton {{ background: {COLORS['surface_soft']}; color:{COLORS['text_secondary']}; border-radius:16px; border:none; font-size: 15px; }} QPushButton:hover {{ background:{COLORS['border']}; color:{COLORS['text_primary']}; }}")
        self.theme_btn.clicked.connect(self._toggle_theme)
        top.addWidget(self.theme_btn)

        settings_btn = QPushButton("⚙️")
        settings_btn.setFixedSize(32,32)
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.setToolTip("إعدادات النصوص الثابتة")
        settings_btn.setStyleSheet(f"QPushButton {{ background: {COLORS['surface_soft']}; color:{COLORS['text_secondary']}; border-radius:16px; border:none; font-size: 15px; }} QPushButton:hover {{ background:{COLORS['border']}; color:{COLORS['text_primary']}; }}")
        settings_btn.clicked.connect(self._open_settings)
        top.addWidget(settings_btn)

        self.archive_btn = QPushButton("🗄️")
        self.archive_btn.setFixedSize(32,32)
        self.archive_btn.setCursor(Qt.PointingHandCursor)
        self.archive_btn.setToolTip("أرشفة وتنظيف السنة الدراسية")
        self.archive_btn.setStyleSheet(f"QPushButton {{ background: {COLORS['surface_soft']}; color:#fbbf24; border-radius:16px; border:none; font-size: 15px; }} QPushButton:hover {{ background:{COLORS['border']}; color:#f59e0b; }}")
        self.archive_btn.clicked.connect(self._open_archive)
        top.addWidget(self.archive_btn)

        min_btn = QPushButton("−")
        min_btn.setFixedSize(32,32)
        min_btn.setCursor(Qt.PointingHandCursor)
        min_btn.setStyleSheet(f"QPushButton {{ background: {COLORS['surface_soft']}; color:{COLORS['text_secondary']}; border-radius:16px; font-weight:bold; font-size:18px; border:none; padding-bottom: 4px; }} QPushButton:hover {{ background:{COLORS['border']}; color:{COLORS['text_primary']}; }}")
        min_btn.clicked.connect(self.showMinimized)
        top.addWidget(min_btn)

        self.max_btn = QPushButton("□")
        self.max_btn.setFixedSize(32,32)
        self.max_btn.setCursor(Qt.PointingHandCursor)
        self.max_btn.setStyleSheet(f"QPushButton {{ background: {COLORS['surface_soft']}; color:{COLORS['text_secondary']}; border-radius:16px; font-weight:bold; font-size:14px; border:none; }} QPushButton:hover {{ background:{COLORS['border']}; color:{COLORS['text_primary']}; }}")
        self.max_btn.clicked.connect(self.toggle_maximize)
        top.addWidget(self.max_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32,32)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton { background: rgba(239,68,68,0.15); color:#f87171; border-radius:16px; font-weight:bold; font-size:13px; border:none; } QPushButton:hover { background:#dc2626; color:white; }")
        close_btn.clicked.connect(self.close)
        top.addWidget(close_btn)
        cl.addLayout(top)

        body = QHBoxLayout()
        body.setSpacing(12)

        left_body = QWidget()
        left_body.setStyleSheet("background:transparent;")
        left_body_l = QVBoxLayout(left_body)
        left_body_l.setContentsMargins(0,0,0,0)
        left_body_l.setSpacing(12)

        self.stats_layout = QHBoxLayout()
        self.stats_layout.setSpacing(8)
        left_body_l.addLayout(self.stats_layout)

        self.requests_panel = RequestsPanel()
        left_body_l.addWidget(self.requests_panel, 1)

        body.addWidget(left_body, 1)
        cl.addLayout(body, 1)
        ml.addWidget(content, 1)

        self.services_list_widget = ServicesList()
        ml.addWidget(self.services_list_widget, 0)

        self.particles.setGeometry(0,0,self.width(),self.height())
        self.particles.lower()

        self.services_list_widget.service_selected.connect(self._on_service_selected)
        self.requests_panel.detail_requested.connect(self._open_detail)
        self.requests_panel.quick_action.connect(self._quick_action)
        self.requests_panel.refresh_clicked.connect(self._manual_refresh)
        self.completed_log.request_clicked.connect(self._open_detail)
        self.completed_log.delete_clicked.connect(self._delete_request)
        self.completed_log.batch_delete_asked.connect(self._batch_delete)

        self.auto_timer = QTimer()
        self.auto_timer.timeout.connect(self.load_requests)
        self.auto_timer.start(REFRESH_INTERVAL)

        QTimer.singleShot(400, self.load_services)
        QTimer.singleShot(600, self.load_requests)

    def _toggle_theme(self):
        global SETTINGS, COLORS, _main_window_ref
        new_theme = "light" if SETTINGS.get("theme") == "dark" else "dark"
        SETTINGS["theme"] = new_theme
        save_settings(SETTINGS)
        COLORS = get_colors()
        
        self.auto_timer.stop()
        _main_window_ref = MainWindow()
        _main_window_ref.showMaximized()
        self.deleteLater()

    def _open_settings(self):
        SettingsDialog(self).exec()

    def _open_archive(self):
        ArchiveDialog(self.services_list, self).exec()
        self.load_requests()

    def toggle_maximize(self):
        if self.isMaximized() or self.isFullScreen(): self.showNormal()
        else: self.showMaximized()

    def _on_service_selected(self, svc):
        self.requests_panel.open_service(svc, self.all_requests)

    def load_services(self):
        self.w1 = LoadServicesWorker()
        self.w1.done.connect(self._on_services)
        self.w1.start()

    def _on_services(self, data, err):
        if err: return
        self.services_list = data
        self.services_list_widget.update_data(self.services_list, self.all_requests)

    def load_requests(self):
        if self.loading: return
        self.loading = True
        self.w2 = LoadRequestsWorker()
        self.w2.done.connect(self._on_requests)
        self.w2.start()

    def _on_requests(self, data, err):
        self.loading = False
        if err:
            self.clock.set_connection(False)
            self.last_update_lbl.setText("خطأ في الاتصال")
            self.last_update_lbl.setStyleSheet("color:#ef4444; background:transparent; border:none;")
            return

        self.clock.set_connection(True)
        new_reqs = []
        if not self.first_load:
            for r in data:
                rid = r.get('request_id')
                if rid and rid not in self.seen_ids: new_reqs.append(r)
                
        self.seen_ids = set(r.get('request_id') for r in data if r.get('request_id'))
        self.first_load = False
        self.all_requests = data

        if new_reqs: self._notify_new(new_reqs)

        self.update_stats()
        self.services_list_widget.update_data(self.services_list, self.all_requests)
        self.completed_log.update_data(self.all_requests)

        if self.requests_panel.service:
            self.requests_panel.update_requests(self.all_requests)
        else:
            if not self.services_list_widget.selected:
                self.services_list_widget.select_first()

        now_str = datetime.now().strftime('%H:%M:%S')
        self.last_update_lbl.setText(f"آخر تحديث: {now_str}")
        self.last_update_lbl.setStyleSheet(f"color:{COLORS['text_dim']}; background:transparent; border:none;")

    def _notify_new(self, new_reqs):
        if self.sound_effect: self.sound_effect.play()
        else: QApplication.beep()

        pres_reqs = [r for r in new_reqs if is_president(r.get('service_id'))]
        if pres_reqs:
            r = pres_reqs[0]
            t = get_request_type(r) or 'طلب'
            Toast(f"🏛️ طلب مكتب الرئيس ({t})", f"{r.get('student_name','')}", "#fbbf24", self).show()
            return
        if len(new_reqs) == 1:
            r = new_reqs[0]
            Toast("طلب جديد", f"{r.get('student_name','')} — {r.get('service_name','')}", "#10b981", self).show()
        else:
            Toast(f"{len(new_reqs)} طلبات جديدة", "افتح الخدمة لعرضها", "#7c3aed", self).show()

    def update_stats(self):
        while self.stats_layout.count():
            it = self.stats_layout.takeAt(0)
            w = it.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        counts = {k:0 for k in STATUS_MAP}
        today_date = datetime.now().date()
        urgent_count = 0
        pres_count = 0
        for r in self.all_requests:
            st = r.get('status','pending')
            if st in counts: counts[st] += 1
            if urgency(r) >= 2: urgent_count += 1
            if is_president(r.get('service_id')) and st == 'pending': pres_count += 1

        for label, value, color in [
            ("قيد المراجعة", counts['pending'], "#d97706"),
            ("موافق", counts['approved'],"#2563eb"),
            ("جاهز", counts['ready'],   "#059669"),
            ("🏛️ مكتب الرئيس", pres_count,    "#fbbf24"),
            ("متأخرة", urgent_count,      "#dc2626"),
            ("الإجمالي", len(self.all_requests),"#64748b"),
        ]:
            card = QFrame()
            card.setFixedHeight(68)
            card.setStyleSheet(f"QFrame {{ background: {COLORS['surface_soft']}; border-radius:10px; border-left:2px solid {color}; }}")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(12,8,12,8)
            cl.setSpacing(1)
            v = QLabel(str(value))
            v.setFont(F(19))
            v.setStyleSheet(f"color:{color}; background:transparent; border:none;")
            v.setAlignment(Qt.AlignCenter)
            cl.addWidget(v)
            t = QLabel(label)
            t.setFont(F(9, bold=False))
            t.setStyleSheet(f"color:{COLORS['text_dim']}; background:transparent; border:none;")
            t.setAlignment(Qt.AlignCenter)
            cl.addWidget(t)
            self.stats_layout.addWidget(card)

    def _manual_refresh(self):
        self.requests_panel.refresh_btn.setText("...")
        self.requests_panel.refresh_btn.setEnabled(False)
        self.load_requests()
        QTimer.singleShot(1500, lambda: (self.requests_panel.refresh_btn.setText("↻"), self.requests_panel.refresh_btn.setEnabled(True)))

    def _open_detail(self, req):
        reg_id = req.get('reg_id')
        svc_id = req.get('service_id')
        count = sum(1 for r in self.all_requests if r.get('reg_id') == reg_id and r.get('service_id') == svc_id) if reg_id else 1
        dlg = DetailDialog(req, request_count=count, parent=self)
        dlg.updated.connect(self.load_requests)
        dlg.exec()

    def _quick_action(self, req, action):
        if action == "rejected":
            self._open_detail(req)
            return
        if QMessageBox.question(self, "تأكيد", f"{STATUS_MAP[action]['text']} للطلب؟\n{req.get('student_name','')}", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes: return

        delete_img_name = None
        updates = {"status": action, "processed_by": PROCESSOR_NAME, "processed_at": datetime.now().isoformat()}
        if action == "delivered":
            delete_img_name = (req.get('image_name') or extract_image_name(req.get('image_url')))
            if delete_img_name:
                updates["image_url"] = None
                updates["image_name"] = None

        self.w3 = UpdateWorker(req['request_id'], updates, delete_img_name)
        self.w3.done.connect(lambda ok, err: self.load_requests() if ok else QMessageBox.critical(self, "خطأ", err))
        self.w3.start()

    def _delete_request(self, req):
        pwd, ok = QInputDialog.getText(self, "🔒 تأكيد الحذف", f"أدخل الرمز لحذف الطلب:\n{req.get('request_id','')}", QLineEdit.Password)
        if not ok: return
        if pwd.strip() != DELETE_PASSWORD:
            QMessageBox.critical(self, "خطأ", "❌ الرمز غير صحيح")
            return
        if QMessageBox.question(self, "تأكيد نهائي", f"هل أنت متأكد من حذف الطلب نهائياً؟\n\nالطالب: {req.get('student_name','')}", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes: return
        
        self.del_worker = DeleteWorker(req['request_id'])
        self.del_worker.done.connect(self._on_delete_done)
        self.del_worker.start()

    def _on_delete_done(self, ok, err):
        if ok: QMessageBox.information(self, "✅ تم", "تم حذف الطلب بنجاح")
        else: QMessageBox.critical(self, "خطأ في الحذف", f"فشل حذف الطلب:\n\n{err}")
        self.load_requests()

    def _batch_delete(self):
        archived = [r for r in self.all_requests if is_archived(r)]
        if not archived: return
        archived.sort(key=lambda r: r.get('processed_at') or r.get('timestamp') or '', reverse=True)
        to_delete = archived[:100]

        pwd, ok = QInputDialog.getText(self, "🔒 تأكيد الحذف الجماعي", f"سيتم حذف {len(to_delete)} طلب من السجل نهائياً\n\nأدخل الرمز للتأكيد:", QLineEdit.Password)
        if not ok: return
        if pwd.strip() != DELETE_PASSWORD:
            QMessageBox.critical(self, "خطأ", "❌ الرمز غير صحيح")
            return
        if QMessageBox.warning(self, "⚠️ تأكيد نهائي", f"هل أنت متأكد من حذف {len(to_delete)} طلب نهائياً؟\n\nلا يمكن التراجع!", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes: return

        self.batch_del_worker = BatchDeleteWorker([r['request_id'] for r in to_delete])
        self.batch_del_worker.done.connect(lambda ok, cnt, err: self.load_requests())
        self.batch_del_worker.start()

    def _delete_by_regid(self, reg_id):
        reqs = [r for r in self.all_requests if str(r.get('reg_id','')) == reg_id]
        if not reqs:
            QMessageBox.information(self, "لا يوجد", f"لا توجد طلبات للرقم: {reg_id}")
            return

        name = reqs[0].get('student_name','')
        pwd, ok = QInputDialog.getText(self, "🔒 تأكيد الحذف", f"سيتم حذف {len(reqs)} طلب للطالب:\n{name} ({reg_id})\n\nأدخل الرمز:", QLineEdit.Password)
        if not ok: return
        if pwd.strip() != DELETE_PASSWORD:
            QMessageBox.critical(self, "خطأ", "❌ الرمز غير صحيح")
            return
        if QMessageBox.warning(self, "⚠️ تأكيد نهائي", f"حذف {len(reqs)} طلب نهائياً؟\n\nالطالب: {name}\nالرقم: {reg_id}", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes: return

        self.del_regid_worker = DeleteByRegIdWorker(reg_id, reqs)
        self.del_regid_worker.done.connect(self._on_delete_by_regid_done)
        self.del_regid_worker.start()

    def _on_delete_by_regid_done(self, ok, count, name, err):
        if ok:
            QMessageBox.information(self, "✅ تم", f"تم حذف {count} طلب للطالب: {name}")
            self.delete_by_regid.reg_input.clear()
        else: QMessageBox.critical(self, "خطأ", f"فشل الحذف:\n{err}")
        self.load_requests()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and e.position().y() < 55:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept(); return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos); e.accept(); return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
        super().mouseReleaseEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.particles.setGeometry(0,0,self.width(),self.height())

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        g = QLinearGradient(0,0,self.width(),self.height())
        g.setColorAt(0.0, QColor(COLORS['bg_grad_top']))
        g.setColorAt(1.0, QColor(COLORS['bg_grad_bottom']))
        p.setBrush(QBrush(g))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(self.rect(), 20, 20)
        p.end()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape: self.close()
        elif e.key() == Qt.Key_F5: self._manual_refresh()
        elif e.key() == Qt.Key_Slash:
            self.requests_panel.search.setFocus()
            self.requests_panel.search.selectAll()
        elif e.key() in (Qt.Key_Up, Qt.Key_Down):
            self.services_list_widget.move_selection(-1 if e.key() == Qt.Key_Up else 1)
        elif e.key() in (Qt.Key_Left, Qt.Key_Right):
            self.requests_panel.move_card_selection(-1 if e.key() == Qt.Key_Right else 1)
        elif e.key() in (Qt.Key_Return, Qt.Key_Enter):
            idx = self.requests_panel.selected_idx
            cards = self.requests_panel.cards
            if 0 <= idx < len(cards): self._open_detail(cards[idx].req)
        elif e.key() in (Qt.Key_A, Qt.Key_R, Qt.Key_S, Qt.Key_D):
            idx = self.requests_panel.selected_idx
            cards = self.requests_panel.cards
            if 0 <= idx < len(cards):
                m = {Qt.Key_A:"approved", Qt.Key_R:"rejected", Qt.Key_S:"ready", Qt.Key_D:"delivered"}
                self._quick_action(cards[idx].req, m[e.key()])
        else:
            super().keyPressEvent(e)


# ═══════════════════════════════════════════════════════════
# التشغيل
# ═══════════════════════════════════════════════════════════
def main():
    global _main_window_ref
    app = QApplication(sys.argv)
    app.setFont(F(11))
    _main_window_ref = MainWindow()
    _main_window_ref.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()