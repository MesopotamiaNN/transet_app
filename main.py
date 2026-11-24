import sys
import json
import requests
from datetime import datetime
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QScrollArea, QFrame,
    QDialog, QFormLayout, QSpinBox, QComboBox, QMessageBox, QSizePolicy,
    QStackedWidget, QButtonGroup
)
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError:
    print("الرجاء تثبيت PySide6-Addons: pip install PySide6-Addons")
    sys.exit(1)

# ================== الإعدادات ==================
SUPABASE_URL = "https://ewivzdrrujuwhkuqqgei.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV3aXZ6ZHJydWp1d2hrdXFxZ2VpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk1OTMwNDQsImV4cCI6MjEwNTE2OTA0NH0.ng8N-08Pl2SOr42Dw01fLSG6n8C17BNTG5XDVPdisM8"

# ================== خريطة HTML (Light Mode) ==================
MAP_HTML = """
<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="UTF-8">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body, html { margin: 0; padding: 0; height: 100%; background: #f8f9fa; overflow: hidden; }
        #map { width: 100%; height: 100%; background: #f8f9fa; }
        
        .leaflet-container { background: #f8f9fa; }
        .custom-icon { background: transparent; border: none; }
        
        /* تنسيق النافذة المنبثقة (Popup) بنمط فاتح */
        .leaflet-popup-content-wrapper { background: #ffffff; color: #1f2937; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        .leaflet-popup-tip { background: #ffffff; }
        
        /* لوحة التحكم داخل الخريطة بنمط فاتح */
        .control-panel {
            background: #ffffff; color: #1f2937; padding: 10px; border-radius: 12px;
            display: flex; flex-direction: column; gap: 8px; font-family: Tahoma, sans-serif;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1); border: 1px solid #e2e8f0;
        }
        .control-btn {
            background: #f8f9fa; color: #1f2937; border: 1px solid #cbd5e1;
            padding: 8px 14px; border-radius: 8px; cursor: pointer; font-weight: bold;
            transition: 0.2s; text-align: right;
        }
        .control-btn:hover { background: #e2e8f0; }
        .control-btn.active { background: #3b82f6; color: #ffffff; border-color: #3b82f6; }
    </style>
</head>
<body>
<div id="map"></div>
<script>
    const map = L.map('map', { zoomControl: false }).setView([33.2765, 44.3380], 12);
    
    // خريطة OpenStreetMap الفاتحة (بدون فلاتر عكس ألوان)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap'
    }).addTo(map);
    
    L.control.zoom({ position: 'bottomright' }).addTo(map);

    let driverMarkers = {}, studentMarkers = {}, pathLines = {};
    let showStudents = true, showPaths = true;

    function esc(str) {
        return String(str || '').replace(/[&<>"']/g, function(c) {
            return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
        });
    }

    const driverIcon = L.divIcon({
        className: 'custom-icon',
        html: '<div style="background:#10b981; color:white; border-radius:50%; width:36px; height:36px; display:flex; align-items:center; justify-content:center; border:3px solid white; box-shadow:0 4px 10px rgba(0,0,0,0.3);"><i class="fas fa-bus" style="font-size:16px;"></i></div>',
        iconSize: [36, 36], iconAnchor: [18, 18]
    });

    const studentIcon = L.divIcon({
        className: 'custom-icon',
        html: '<div style="background:#3b82f6; color:white; border-radius:50%; width:28px; height:28px; display:flex; align-items:center; justify-content:center; border:2px solid white; box-shadow:0 2px 5px rgba(0,0,0,0.3);"><i class="fas fa-user-graduate" style="font-size:14px;"></i></div>',
        iconSize: [28, 28], iconAnchor: [14, 14]
    });

    function updateData(drivers, students) {
        window._lastDrivers = drivers;
        window._lastStudents = students;
        
        // === السائقين ===
        const currentDriverIds = new Set();
        drivers.forEach(d => {
            if (!d.lat || !d.lng) return;
            const id = d.driver_phone;
            currentDriverIds.add(id);
            
            const popup = `<div style="direction: rtl; text-align: right; font-family: Tahoma;">
                <b style="font-size:14px; color:#10b981;">${esc(d.driver_name)}</b><br>
                <span style="color:#64748b;">${esc(d.area)}</span><br>
                <span style="color:#d97706; font-weight:bold;">${esc(d.available_seats)} مقاعد شاغرة</span>
            </div>`;

            if (driverMarkers[id]) {
                driverMarkers[id].setLatLng([d.lat, d.lng]).setPopupContent(popup);
            } else {
                driverMarkers[id] = L.marker([d.lat, d.lng], { icon: driverIcon })
                    .addTo(map).bindPopup(popup);
            }

            if (showPaths && d.path && d.path.length > 1) {
                if (pathLines[id]) {
                    pathLines[id].setLatLngs(d.path);
                } else {
                    pathLines[id] = L.polyline(d.path, { color: '#3b82f6', weight: 4, opacity: 0.7, dashArray: '8, 8' }).addTo(map);
                }
            } else if (pathLines[id]) {
                map.removeLayer(pathLines[id]);
                delete pathLines[id];
            }
        });

        for (let id in driverMarkers) {
            if (!currentDriverIds.has(id)) {
                map.removeLayer(driverMarkers[id]);
                delete driverMarkers[id];
                if (pathLines[id]) {
                    map.removeLayer(pathLines[id]);
                    delete pathLines[id];
                }
            }
        }

        // === الطلاب ===
        if (showStudents) {
            const currentStudentIds = new Set();
            students.forEach(s => {
                if (!s.lat || !s.lng) return; // يتخطى الطلاب الذين لا يملكون إحداثيات
                const id = s.reg_id || s.id || Math.random().toString();
                currentStudentIds.add(id);
                const popup = `<div style="direction: rtl; text-align: right; font-family: Tahoma;">
                    <b>${esc(s.name)}</b><br><span style="color:#3b82f6; font-weight:bold;">طالب</span>
                </div>`;
                if (studentMarkers[id]) {
                    studentMarkers[id].setLatLng([s.lat, s.lng]).setPopupContent(popup);
                } else {
                    studentMarkers[id] = L.marker([s.lat, s.lng], { icon: studentIcon })
                        .addTo(map).bindPopup(popup);
                }
            });
            for (let id in studentMarkers) {
                if (!currentStudentIds.has(id)) {
                    map.removeLayer(studentMarkers[id]);
                    delete studentMarkers[id];
                }
            }
        } else {
            for (let id in studentMarkers) {
                map.removeLayer(studentMarkers[id]);
                delete studentMarkers[id];
            }
        }
    }

    function fitBounds() {
        let bounds = L.latLngBounds();
        let hasPoints = false;
        for (let id in driverMarkers) { bounds.extend(driverMarkers[id].getLatLng()); hasPoints = true; }
        for (let id in studentMarkers) { bounds.extend(studentMarkers[id].getLatLng()); hasPoints = true; }
        if (hasPoints) map.fitBounds(bounds, { padding: [50, 50] });
    }

    function toggleStudents(btn) {
        showStudents = !showStudents;
        btn.classList.toggle('active', showStudents);
        updateData(window._lastDrivers || [], window._lastStudents || []);
    }

    function togglePaths(btn) {
        showPaths = !showPaths;
        btn.classList.toggle('active', showPaths);
        updateData(window._lastDrivers || [], window._lastStudents || []);
    }

    const controlPanel = L.control({position: 'topright'});
    controlPanel.onAdd = function(map) {
        const div = L.DomUtil.create('div', 'control-panel');
        div.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 4px; text-align: right; font-size: 14px;">خيارات الخريطة</div>
            <button class="control-btn" onclick="fitBounds()">🎯 توسيط الكل</button>
            <button class="control-btn active" id="btn-students" onclick="toggleStudents(this)">👨‍🎓 الطلاب</button>
            <button class="control-btn active" id="btn-paths" onclick="togglePaths(this)">🛣️ المسارات</button>
        `;
        L.DomEvent.disableClickPropagation(div);
        return div;
    };
    controlPanel.addTo(map);
</script>
</body>
</html>
"""

# ================== التصميم الخاص بـ PySide ==================
STYLES = """
QMainWindow, QWidget#root { background-color: #0b1220; }
QWidget { color: #e2e8f0; font-size: 13px; }
QFrame#panel { background-color: #111c2e; border-radius: 16px; border: 1px solid #1e293b; }
QFrame#statCard { background-color: #162032; border-radius: 14px; border: 1px solid #1e293b; }
QFrame#driverCard, QFrame#driverCardLive {
    background-color: #162032; border-radius: 12px; border: 1px solid #1e293b;
}
QFrame#driverCardLive { border: 1px solid #10b981; }
QFrame#driverCard:hover, QFrame#driverCardLive:hover { background-color: #1e293b; }
QLabel#appTitle { color: #f8fafc; font-size: 22px; font-weight: 900; }
QLabel#appSub, QLabel#muted { color: #94a3b8; }
QLabel#sectionTitle { color: #f8fafc; font-size: 15px; font-weight: 800; }
QLabel#liveDot { background-color: #10b981; border-radius: 6px; }
QLabel#driverName { color: #f8fafc; font-weight: 900; font-size: 14px; }
QLabel#badgeLive  { background-color: rgba(16,185,129,0.15); color:#10b981; border-radius:8px; padding:4px 10px; font-size:11px; font-weight:800; }
QLabel#badgeOff   { background-color: rgba(100,116,139,0.15); color:#94a3b8; border-radius:8px; padding:4px 10px; font-size:11px; font-weight:800; }
QLabel#badgeSeats { background-color: rgba(245,158,11,0.15); color:#f59e0b; border-radius:8px; padding:3px 8px; font-size:11px; font-weight:800; }
QLabel#badgePrice { background-color: rgba(139,92,246,0.15); color:#8b5cf6; border-radius:8px; padding:3px 8px; font-size:11px; font-weight:800; }
QPushButton { background-color: #1e293b; color:#e2e8f0; border:1px solid #334155; border-radius:10px; padding:8px 14px; font-weight:700; }
QPushButton:hover { background-color:#334155; }
QPushButton:pressed { background-color:#475569; }
QPushButton#primary { background-color:#3b82f6; color:#fff; border:none; }
QPushButton#primary:hover { background-color:#2563eb; }
QPushButton:checked { background-color:#3b82f6; color:#fff; border:none; }
QLineEdit { background-color:#0f172a; border:1px solid #334155; border-radius:10px; padding:8px 14px; color:#e2e8f0; }
QLineEdit:focus { border:1px solid #3b82f6; }
QComboBox, QSpinBox { background-color:#0f172a; border:1px solid #334155; border-radius:10px; padding:6px 10px; color:#e2e8f0; }
QScrollArea { border:none; background:transparent; }
QScrollBar:vertical { background:#0f172a; width:8px; border-radius:4px; }
QScrollBar::handle:vertical { background:#334155; border-radius:4px; min-height:30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QDialog { background-color:#0b1220; }
"""

# ================== جلب البيانات ==================
class FetchWorker(QThread):
    data_ready = Signal(list, list, list)
    error = Signal(str)

    def run(self):
        try:
            h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
            r1 = requests.get(f"{SUPABASE_URL}/rest/v1/routes?select=*", headers=h, timeout=10)
            r2 = requests.get(f"{SUPABASE_URL}/rest/v1/live_buses?select=*", headers=h, timeout=10)
            r3 = requests.get(f"{SUPABASE_URL}/rest/v1/students?select=*", headers=h, timeout=10)
            
            routes = r1.json() if r1.ok and isinstance(r1.json(), list) else []
            live = r2.json() if r2.ok and isinstance(r2.json(), list) else []
            students = r3.json() if r3.ok and isinstance(r3.json(), list) else []
            
            self.data_ready.emit(routes, live, students)
        except Exception as e:
            self.error.emit(str(e))

# ================== الأقسام الجانبية ==================
class LeftSidebar(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("panel")
        self.setFixedWidth(240)
        v = QVBoxLayout(self); v.setContentsMargins(18, 20, 18, 20); v.setSpacing(14)

        title = QLabel("جامعة الناجي"); title.setObjectName("appTitle")
        sub = QLabel("خدمة النقل الطلابي"); sub.setObjectName("appSub")
        v.addWidget(title); v.addWidget(sub)

        status = QHBoxLayout()
        dot = QLabel(); dot.setObjectName("liveDot"); dot.setFixedSize(12, 12)
        lbl = QLabel("متصل"); lbl.setStyleSheet("color:#10b981; font-weight:800;")
        status.addWidget(dot); status.addWidget(lbl); status.addStretch()
        v.addLayout(status)

        div = QFrame(); div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("background:#1e293b; max-height:1px;"); v.addWidget(div)

        self.stats = {}
        for key, name, color in [
            ("routes", "إجمالي السائقين", "#3b82f6"),
            ("live", "المباشرون الآن", "#10b981"),
            ("seats", "المقاعد الشاغرة", "#f59e0b"),
        ]:
            row = QHBoxLayout()
            t = QLabel(name); t.setObjectName("muted")
            val = QLabel("0"); val.setStyleSheet(f"color:{color}; font-size:16px; font-weight:900;")
            row.addWidget(t); row.addStretch(); row.addWidget(val)
            v.addLayout(row); self.stats[key] = val

        v.addStretch()
        self.footer = QLabel("آخر تحديث: —"); self.footer.setObjectName("muted")
        v.addWidget(self.footer)

class RightSidebar(QFrame):
    add_clicked = Signal()
    refresh_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("panel")
        self.setFixedWidth(240)
        v = QVBoxLayout(self); v.setContentsMargins(18, 20, 18, 20); v.setSpacing(10)

        t = QLabel("الإجراءات"); t.setObjectName("sectionTitle"); v.addWidget(t)

        b1 = QPushButton("＋  إضافة سائق"); b1.setObjectName("primary")
        b1.clicked.connect(self.add_clicked.emit); v.addWidget(b1)

        b2 = QPushButton("🔄  تحديث البيانات")
        b2.clicked.connect(self.refresh_clicked.emit); v.addWidget(b2)

        v.addStretch()
        info = QLabel("لوحة تحكم خدمة النقل\nإدارة السائقين والرحلات\nاستعلام مباشر من Supabase")
        info.setObjectName("muted"); info.setWordWrap(True)
        v.addWidget(info)

# ================== بطاقات الإحصائيات ==================
class StatCard(QFrame):
    def __init__(self, title, color):
        super().__init__()
        self.setObjectName("statCard"); self.setFixedHeight(90)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        v = QVBoxLayout(self); v.setContentsMargins(16, 12, 16, 12)
        t = QLabel(title); t.setStyleSheet("color:#94a3b8; font-weight:700;")
        self.val = QLabel("0"); self.val.setStyleSheet(f"color:{color}; font-size:22px; font-weight:900;")
        v.addWidget(t); v.addWidget(self.val)
    def set_value(self, v): self.val.setText(str(v))

# ================== بطاقة السائق (للقائمة) ==================
class DriverCard(QFrame):
    def __init__(self, d, live):
        super().__init__()
        self.setObjectName("driverCardLive" if live else "driverCard")
        h = QHBoxLayout(self); h.setContentsMargins(14, 12, 14, 12); h.setSpacing(12)

        info = QVBoxLayout(); info.setSpacing(4)
        name = QLabel(d.get("driver_name", "بدون اسم")); name.setObjectName("driverName")
        info.addWidget(name)

        detail = QLabel(f"{d.get('area','—')}  •  {d.get('driver_phone','—')}")
        detail.setObjectName("muted"); info.addWidget(detail)

        badges = QHBoxLayout(); badges.setSpacing(6)
        b1 = QLabel(f"🪑 {d.get('available_seats',0)} مقاعد"); b1.setObjectName("badgeSeats")
        b2 = QLabel(f"💰 {d.get('price',0)} د.ع"); b2.setObjectName("badgePrice")
        badges.addWidget(b1); badges.addWidget(b2); badges.addStretch()
        info.addLayout(badges)

        h.addLayout(info, 1)
        st = QLabel("مباشر الآن" if live else "غير متصل")
        st.setObjectName("badgeLive" if live else "badgeOff")
        st.setAlignment(Qt.AlignCenter)
        h.addWidget(st, 0, Qt.AlignTop)

# ================== نافذة إضافة سائق ==================
class AddDriverDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إضافة سائق جديد")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setFixedSize(420, 540)
        v = QVBoxLayout(self); v.setContentsMargins(20,20,20,20); v.setSpacing(10)
        t = QLabel("سائق جديد"); t.setObjectName("sectionTitle"); v.addWidget(t)

        form = QFormLayout(); form.setSpacing(8)
        self.name  = QLineEdit(); self.name.setPlaceholderText("الاسم الكامل"); form.addRow("الاسم:", self.name)
        self.phone = QLineEdit(); self.phone.setPlaceholderText("07XXXXXXXXX"); form.addRow("الهاتف:", self.phone)
        self.area  = QLineEdit(); self.area.setPlaceholderText("المناطق"); form.addRow("المناطق:", self.area)
        self.car   = QLineEdit(); self.car.setPlaceholderText("نوع السيارة (اختياري)"); form.addRow("السيارة:", self.car)
        self.vt = QComboBox(); self.vt.addItems(["bus - باص", "car - سيارة"]); form.addRow("المركبة:", self.vt)
        self.seats = QSpinBox(); self.seats.setRange(1,50); self.seats.setValue(14); form.addRow("المقاعد:", self.seats)
        self.price = QSpinBox(); self.price.setRange(0,1000000); self.price.setValue(5000); self.price.setSingleStep(500); form.addRow("السعر:", self.price)
        self.time  = QLineEdit(); self.time.setPlaceholderText("07:00 صباحاً"); form.addRow("الانطلاق:", self.time)
        v.addLayout(form); v.addStretch()

        btns = QHBoxLayout()
        c = QPushButton("إلغاء"); c.clicked.connect(self.reject)
        s = QPushButton("حفظ السائق"); s.setObjectName("primary"); s.clicked.connect(self._check)
        btns.addWidget(c); btns.addWidget(s); v.addLayout(btns)

    def _check(self):
        if not self.name.text().strip(): return QMessageBox.warning(self,"تنبيه","الاسم مطلوب")
        if not self.phone.text().strip(): return QMessageBox.warning(self,"تنبيه","الهاتف مطلوب")
        if not self.area.text().strip(): return QMessageBox.warning(self,"تنبيه","المناطق مطلوبة")
        self.accept()

    def get_data(self):
        return {
            "driver_name": self.name.text().strip(),
            "driver_phone": self.phone.text().strip(),
            "area": self.area.text().strip(),
            "car": self.car.text().strip(),
            "vehicle_type": "bus" if self.vt.currentIndex()==0 else "car",
            "total_seats": self.seats.value(),
            "available_seats": self.seats.value(),
            "price": self.price.value(),
            "time": self.time.text().strip(),
            "active": True,
        }

# ================== المركز (خريطة + قائمة) ==================
class CenterPanel(QFrame):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.setObjectName("panel")
        v = QVBoxLayout(self); v.setContentsMargins(20,20,20,20); v.setSpacing(14)

        # الرأس
        head = QHBoxLayout()
        title = QLabel("لوحة تحكم خدمة النقل"); title.setObjectName("appTitle")
        head.addWidget(title); head.addStretch()
        
        self.btn_map = QPushButton("🗺️ الخريطة")
        self.btn_map.setCheckable(True); self.btn_map.setChecked(True)
        self.btn_list = QPushButton("📋 القائمة")
        self.btn_list.setCheckable(True)
        
        group = QButtonGroup(self)
        group.addButton(self.btn_map, 0); group.addButton(self.btn_list, 1)
        group.idClicked.connect(self.switch_view)
        head.addWidget(self.btn_map); head.addWidget(self.btn_list)

        self.last_update = QLabel("آخر تحديث: —"); self.last_update.setObjectName("muted")
        head.addWidget(self.last_update); v.addLayout(head)

        # الإحصائيات
        cards = QHBoxLayout(); cards.setSpacing(12)
        self.c_total  = StatCard("إجمالي السائقين", "#3b82f6")
        self.c_live   = StatCard("المباشرون الآن", "#10b981")
        self.c_seats  = StatCard("المقاعد الشاغرة", "#f59e0b")
        self.c_active = StatCard("رحلات نشطة", "#8b5cf6")
        for c in (self.c_total, self.c_live, self.c_seats, self.c_active):
            cards.addWidget(c)
        v.addLayout(cards)

        # شريط البحث والإجراءات
        tb = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText("🔍 البحث بالاسم أو المنطقة أو الهاتف...")
        self.search.textChanged.connect(self.render_list)
        tb.addWidget(self.search, 1)
        rb = QPushButton("تحديث"); rb.clicked.connect(main_window.fetch_data); tb.addWidget(rb)
        ab = QPushButton("＋ إضافة سائق"); ab.setObjectName("primary"); ab.clicked.connect(main_window.open_add); tb.addWidget(ab)
        v.addLayout(tb)

        # المكدس: 0=الخريطة، 1=القائمة
        self.stack = QStackedWidget()
        
        self.map_view = QWebEngineView()
        self.map_view.setHtml(MAP_HTML)
        self.map_view.loadFinished.connect(self.on_map_loaded)
        self.stack.addWidget(self.map_view)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_w = QWidget(); self.list_v = QVBoxLayout(self.list_w)
        self.list_v.setContentsMargins(0,0,0,0); self.list_v.setSpacing(8); self.list_v.addStretch()
        scroll.setWidget(self.list_w)
        self.stack.addWidget(scroll)

        v.addWidget(self.stack, 1)
        self.map_ready = False

    def switch_view(self, idx):
        self.stack.setCurrentIndex(idx)
        if idx == 0:
            self.btn_map.setStyleSheet("background-color:#3b82f6; color:white; border:none;")
            self.btn_list.setStyleSheet("")
        else:
            self.btn_list.setStyleSheet("background-color:#3b82f6; color:white; border:none;")
            self.btn_map.setStyleSheet("")

    def on_map_loaded(self):
        self.map_ready = True
        self.update_map(self.main.routes_data, self.main.live_data, self.main.students_data)

    def update_map(self, routes, live, students):
        if not self.map_ready: return

        drivers_data = []
        for l in live:
            route = next((r for r in routes if r.get('driver_phone') == l.get('driver_phone')), {})
            drivers_data.append({
                'driver_phone': l.get('driver_phone'),
                'driver_name': l.get('driver_name'),
                'area': l.get('area'),
                'lat': l.get('lat'),
                'lng': l.get('lng'),
                'path': l.get('path', []),
                'available_seats': route.get('available_seats', 0)
            })

        students_data = []
        for s in students:
            # التحقق من وجود الإحداثيات في قاعدة البيانات
            if s.get('lat') and s.get('lng'):
                students_data.append({
                    'reg_id': s.get('reg_id'),
                    'name': s.get('name'),
                    'lat': s.get('lat'),
                    'lng': s.get('lng')
                })

        js = f"updateData({json.dumps(drivers_data, ensure_ascii=False)}, {json.dumps(students_data, ensure_ascii=False)});"
        self.map_view.page().runJavaScript(js)

    def render_list(self):
        q = self.search.text().strip().lower()
        live_phones = {l.get("driver_phone") for l in self.main.live_data}

        while self.list_v.count() > 1:
            it = self.list_v.takeAt(0)
            if it.widget(): it.widget().deleteLater()

        rows = [r for r in self.main.routes_data if r.get("active")]
        if q:
            rows = [r for r in rows if q in str(r.get("driver_name","")).lower()
                    or q in str(r.get("area","")).lower() or q in str(r.get("driver_phone","")).lower()]

        if not rows:
            e = QLabel("لا يوجد سائقون مطابقون"); e.setObjectName("muted")
            e.setAlignment(Qt.AlignCenter); e.setStyleSheet("padding:30px;")
            self.list_v.insertWidget(0, e); return

        for r in rows:
            live = r.get("driver_phone") in live_phones
            self.list_v.insertWidget(self.list_v.count()-1, DriverCard(r, live))

    def update_stats(self, routes, live):
        live_phones = {l.get("driver_phone") for l in live}
        active = [r for r in routes if r.get("active")]
        total = len(active)
        live_count = len(live_phones & {r.get("driver_phone") for r in active})
        seats = sum(int(r.get("available_seats", 0) or 0) for r in active)

        self.c_total.set_value(total); self.c_live.set_value(live_count)
        self.c_seats.set_value(seats); self.c_active.set_value(total)
        self.main.left.stats["routes"].setText(str(total))
        self.main.left.stats["live"].setText(str(live_count))
        self.main.left.stats["seats"].setText(str(seats))
        self.last_update.setText("آخر تحديث: " + datetime.now().strftime("%H:%M:%S"))

# ================== النافذة الرئيسية ==================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("جامعة الناجي — لوحة تحكم خدمة النقل")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(1400, 900); self.setMinimumSize(1100, 700)

        self.is_fetching = False
        self.routes_data, self.live_data, self.students_data = [], [], []

        root = QWidget(); root.setObjectName("root"); self.setCentralWidget(root)
        H = QHBoxLayout(root); H.setContentsMargins(16,16,16,16); H.setSpacing(16)

        self.right = RightSidebar()
        self.right.add_clicked.connect(self.open_add)
        self.right.refresh_clicked.connect(self.fetch_data)

        self.center_panel = CenterPanel(self)
        self.left = LeftSidebar()

        H.addWidget(self.right)
        H.addWidget(self.center_panel, 1)
        H.addWidget(self.left)

        self.timer = QTimer(); self.timer.timeout.connect(self.fetch_data); self.timer.start(5000)
        self.fetch_data()

    def open_add(self):
        dlg = AddDriverDialog(self)
        if dlg.exec() != QDialog.Accepted: return
        data = dlg.get_data()
        try:
            h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                 "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates,return=minimal"}
            r = requests.post(f"{SUPABASE_URL}/rest/v1/routes?on_conflict=driver_phone",
                              headers=h, json=data, timeout=10)
            if r.status_code not in (200, 201, 204): raise Exception(r.text)
            QMessageBox.information(self, "نجاح", "تم إضافة السائق بنجاح")
            self.fetch_data()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل الإضافة:\n{e}")

    def fetch_data(self):
        if self.is_fetching: return
        self.is_fetching = True
        self.worker = FetchWorker()
        self.worker.data_ready.connect(self.on_data)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_data(self, routes, live, students):
        self.is_fetching = False
        self.routes_data, self.live_data, self.students_data = routes, live, students
        self.center_panel.update_stats(routes, live)
        self.center_panel.render_list()
        self.center_panel.update_map(routes, live, students)
        self.left.footer.setText("آخر تحديث: " + datetime.now().strftime("%H:%M:%S"))

    def on_error(self, msg):
        self.is_fetching = False
        print("Fetch error:", msg)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    app.setFont(QFont("Cairo", 10))
    app.setStyleSheet(STYLES)
    w = MainWindow(); w.show()
    sys.exit(app.exec())