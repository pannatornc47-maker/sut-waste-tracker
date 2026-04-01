import streamlit as st
import folium
from streamlit_folium import st_folium
import firebase_admin
from firebase_admin import credentials, db
import time
from streamlit_autorefresh import st_autorefresh

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="SUT Waste Tracker", page_icon="🚛", layout="wide")

# --- 2. เชื่อมต่อ Firebase (บรรทัดที่ 22-25 แก้ไขพิเศษ) ---
if not firebase_admin._apps:
    try:
        fb_creds = dict(st.secrets["firebase"])
        
        # แก้ไขปัญหา PEM file โดยการลบช่องว่างที่อาจติดมาและจัดการ newline
        pk = fb_creds["private_key"].strip()
        fb_creds["private_key"] = pk.replace("\\n", "\n")
        
        cred = credentials.Certificate(fb_creds)
        db_url = "https://sut-waste-tracker-default-rtdb.asia-southeast1.firebasedatabase.app/"
        firebase_admin.initialize_app(cred, {'databaseURL': db_url})
    except Exception as e:
        st.error(f"❌ Firebase Connection Error: {e}")

# --- 3. ฟังก์ชันจัดการข้อมูล ---
def update_location(truck_id, lat, lon):
    try:
        db.reference(f'trucks/{truck_id}/current').set({
            'lat': lat, 'lon': lon, 'timestamp': time.strftime("%H:%M:%S")
        })
        db.reference(f'trucks/{truck_id}/path').push({
            'lat': lat, 'lon': lon, 'time': time.time()
        })
        return True, "สำเร็จ"
    except Exception as e:
        return False, str(e)

def get_all_trucks():
    try:
        return db.reference('trucks').get()
    except:
        return None

# --- 4. ระบบ UI ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 SUT Waste Tracker Login")
    role = st.selectbox("เลือกสถานะ", ["Driver (คนขับรถ)", "Manager (ผู้ดูแล)"])
    pw = st.text_input("รหัสผ่าน", type="password")
    if st.button("เข้าสู่ระบบ"):
        if pw == "1234":
            st.session_state.logged_in, st.session_state.role = True, role
            st.rerun()
        else: st.error("รหัสผ่านผิด")
else:
    st_autorefresh(interval=5000, key="datarefresh")
    if st.sidebar.button("ออกจากระบบ"):
        st.session_state.logged_in = False
        st.rerun()

    if st.session_state.role == "Driver (คนขับรถ)":
        st.title("🚛 ส่งพิกัดรถขยะ")
        t_id = st.selectbox("หมายเลขรถ", ["Truck_01", "Truck_02", "Truck_03"])
        col1, col2 = st.columns(2)
        lat = col1.number_input("Lat", value=14.882000, format="%.6f")
        lon = col2.number_input("Lon", value=102.021000, format="%.6f")
        if st.toggle("ส่งอัตโนมัติ") or st.button("📍 ส่งตำแหน่ง"):
            ok, msg = update_location(t_id, lat, lon)
            if ok: st.success("บันทึกแล้ว")
            else: st.error(f"ผิดพลาด: {msg}")
    else:
        st.title("👨‍💼 Manager Real-time Tracking")
        data = get_all_trucks()
        if data:
            m = folium.Map(location=[14.882, 102.021], zoom_start=15)
            colors = {"Truck_01": "green", "Truck_02": "blue", "Truck_03": "orange"}
            for tid, info in data.items():
                c = colors.get(tid, "red")
                if 'path' in info:
                    folium.PolyLine([[p['lat'], p['lon']] for p in info['path'].values()], color=c).add_to(m)
                if 'current' in info:
                    curr = info['current']
                    folium.Marker([curr['lat'], curr['lon']], popup=tid, icon=folium.Icon(color=c, icon='truck', prefix='fa')).add_to(m)
            st_folium(m, width="100%", height=500)
        else: st.info("ไม่มีข้อมูล")
