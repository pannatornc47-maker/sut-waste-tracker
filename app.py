import streamlit as st
import folium
from streamlit_folium import st_folium
import firebase_admin
from firebase_admin import credentials, db
import time
from streamlit_autorefresh import st_autorefresh

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="SUT Waste Tracker", page_icon="⚙️", layout="wide")

# --- 2. ข้อมูลกุญแจ Firebase (Hardcoded สำหรับแก้ปัญหา Signature) ---
firebase_key = {
  "type": "service_account",
  "project_id": "sut-waste-tracker",
  "private_key_id": "e341cf18cbe505be7ab63031d8a198dc8d5568ad",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDD9Uxn/t4Jd0qX\nZqRCzdX90PeF7KQfClHZtC4TXSmWnbFgnuV2bOzZ59A0vqirc9h1IQp550+IV0XN\nthGgNN+Sk6Qe76rFe5VEIuQGTfETKvyTbHiiAuiwen/C4kVK6eabLgAEqoL3FEfq\ncBjzAriFIL7RFKnrbp8b5DuBRe7Lk8X39fhM2NStlisdN90tJg+30cLWTTTS45LP\nUGCYt3ZDoSnRzYG4zoCmHHxtOJCrzl563p+RADIf7Ta9eMXrLjj+QJ5PSLf28MCv\nOlWMowjtTW1n4vQlKyuZvspvCx+SDjabpK0ySOLsU+YAAdIh330x5JnmTY2RLXvT\n1URrVFKBAgMBAAECggEAAzrUXYCxN9BZOLN8tLvsKXK/uKuuxRL0SEmAqqmp/0E2\nQKqfyzbWhM0uBKeJk8ldFYmj0MBt8ngnRrGn+tcyQeoIbgja3IZJ3pmRXvP7C6sF\nRpgGqTtxasK7Hzr/48ElD5TXk9wcXF6PhKMAO0WlxU51zLAJsK9mJJVbgHkGy4DK\scY9Ptf5qMogfGLJym733KHGuFihmRecbn0Gr3wtcQ7KsdJq6q/DcsfyG7sAh/pt\nlT3G/9p7Xv6dTALUoY4QoK/CYV+SRw52dfAKEwQBFuIhPEIvBgQefNBaScXUSMxy\nnv0yuWI0Wsaifn6dPFYC3PhV5l+jhFoxzUxXPRcu0QKBgQDrCHgPWxU6xGhXfmFs\ssJlZWd6Zg9wSLFrGX3O5tDzzB6cY6urHoBiJNpr2KD4MViw4nopn5KLMCUHeAkZ\no7MwPu8VynLLbeyKptvl5meIRGJ+PvT5oODBF3yrNPYSuupMtNJlaJADMYuFjoK+\nSZ/2gmp7sniSbsByt9aRsIXvsQKBgQDVcHaDkIdUWVu9Erzcd05mJaZDX42xaKBS\nq/t/otqh/aOGIWSZiWvBj/ZL9yQ4ZWBwCjaTF5qZNhWVZsr07kd9HKmTgf0B4QSu\nVOsmTQeAY+ZjawLqXlZpwST94mkNOY6cSSDxMOgGLAonNTMgAKgc06kiG5cIUcou\nzuhloimT0QKBgHdY6pZpmwMnfxCGxXQL5fjVIFGgB9DtqOIIpMDupkZWbWjel+qh\n53Fu41cGPt8pN69CoeQG+sQhI3yCcKSLYs9p9cAr+FTisc3KYzl/4SzqBNW0pHMq\nRVbn1U+e6iGitp1S6M/D4/UrMH0WW7/C5S6pFOdRPjaldKYMQjHi4HBRAoGAUxBm\nfwMjN5djFW0SZPZlY2lpkDTCrvVZ13Ko+N5HGd3c4tliDkKl1fmRz7SJuwzxAAlp\nfcsk1lVvBuqvN6z301/xOr/O2AlbSgEwVoKJ1dSLF8vQoac/F/8bx1ZyrbvlnTr0\ngAkZczV2ahXRJLY8tqNE4ko8d/dkqNzLIqp+ZdECgYAA0i+Y00oFtEe+dTitZ0jT\nCEp235MEqLOyGGGRaYRbYq4JA+tmjXpjK37N6yumBXcjfIOKb9wOpeTYIbNkMSJ1\ngdiwm9BEkTGronRuhJQqe07ldx3Axc9DgjpTbASvDW3NjdbEpdzvtwSHjubwARq7\nPWr+/eji/ZbFaAlAlbbt4Q==\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-fbsvc@sut-waste-tracker.iam.gserviceaccount.com",
  "client_id": "107808354896124963616",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40sut-waste-tracker.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

# --- 3. เชื่อมต่อ Firebase ---
if not firebase_admin._apps:
    try:
        # ใช้ข้อมูลจากตัวแปร firebase_key โดยตรง
        cred = credentials.Certificate(firebase_key)
        databaseURL = "https://sut-waste-tracker-default-rtdb.asia-southeast1.firebasedatabase.app/"
        firebase_admin.initialize_app(cred, {'databaseURL': databaseURL})
    except Exception as e:
        st.error(f"⚠️ Firebase Error: {e}")

# --- 4. ฟังก์ชันจัดการข้อมูล ---
def update_location(truck_id, lat, lon):
    try:
        ref_current = db.reference(f'trucks/{truck_id}/current')
        ref_current.set({
            'lat': lat, 'lon': lon, 
            'timestamp': time.strftime("%H:%M:%S", time.localtime())
        })
        ref_path = db.reference(f'trucks/{truck_id}/path')
        ref_path.push({'lat': lat, 'lon': lon, 'time': time.time()})
    except: pass

def get_all_trucks():
    try:
        return db.reference('trucks').get()
    except: return None

# --- 5. ระบบ UI ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 SUT Waste Tracker Login")
    role = st.selectbox("เลือกสถานะ", ["Driver (คนขับรถ)", "Manager (ผู้ดูแล)"])
    password = st.text_input("รหัสผ่าน", type="password")
    if st.button("เข้าสู่ระบบ"):
        if password == "1234":
            st.session_state.logged_in = True
            st.session_state.role = role
            st.rerun()
        else: st.error("รหัสผ่านผิด")
else:
    st_autorefresh(interval=5000, key="datarefresh")
    st.sidebar.write(f"ผู้ใช้: {st.session_state.role}")
    if st.sidebar.button("Log out"):
        st.session_state.logged_in = False
        st.rerun()

    if st.session_state.role == "Driver (คนขับรถ)":
        st.title("🚛 แผงควบคุมคนขับ")
        t_id = st.selectbox("เลือกรถ", ["Truck_01", "Truck_02", "Truck_03"])
        auto = st.toggle("Auto Tracking")
        col1, col2 = st.columns(2)
        lat = col1.number_input("Lat", value=14.882, format="%.6f")
        lon = col2.number_input("Lon", value=102.021, format="%.6f")
        if auto or st.button("ส่งพิกัด"):
            update_location(t_id, lat, lon)
            st.success("บันทึกแล้ว")
    else:
        st.title("👨‍💼 หน้าจอจัดการ")
        if st.button("🔄 รีเฟรช"): st.rerun()
        data = get_all_trucks()
        if data:
            m = folium.Map(location=[14.882, 102.021], zoom_start=15)
            cols = {"Truck_01": "green", "Truck_02": "blue", "Truck_03": "orange"}
            for tid, tinfo in data.items():
                c = cols.get(tid, "red")
                if 'path' in tinfo:
                    pts = [[p['lat'], p['lon']] for p in tinfo['path'].values()]
                    folium.PolyLine(pts, color=c).add_to(m)
                if 'current' in tinfo:
                    curr = tinfo['current']
                    folium.Marker([curr['lat'], curr['lon']], icon=folium.Icon(color=c, icon='truck', prefix='fa')).add_to(m)
            st_folium(m, width="100%", height=500)
        else: st.info("ไม่มีข้อมูล")