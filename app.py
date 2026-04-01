import streamlit as st
import folium
from streamlit_folium import st_folium
import firebase_admin
from firebase_admin import credentials, db
import time
from streamlit_autorefresh import st_autorefresh

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="SUT Waste Smart Tracking", page_icon="⚙️", layout="wide")

st.markdown(
    """
    <style>
    .stSpinner i { color: #FF4B4B !important; }
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    .gear-icon { display: inline-block; animation: spin 2s infinite linear; font-size: 24px; color: #FF4B4B; }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
    """,
    unsafe_allow_html=True
)

# --- 2. เชื่อมต่อ Firebase (ดึงจาก Secrets) ---
if not firebase_admin._apps:
    try:
        # อ่านค่าจาก st.secrets["firebase"] ที่เราตั้งไว้
        key_dict = dict(st.secrets["firebase"])
        # แก้ไขปัญหา newline ใน private_key
        key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
        
        cred = credentials.Certificate(key_dict)
        databaseURL = "https://sut-waste-tracker-default-rtdb.asia-southeast1.firebasedatabase.app/"
        
        firebase_admin.initialize_app(cred, {
            'databaseURL': databaseURL,
            'httpTimeout': 60
        })
    except Exception as e:
        st.error(f"⚠️ Firebase Connection Error: {e}")

# --- 3. ฟังก์ชันจัดการข้อมูล ---
def update_location(truck_id, lat, lon):
    try:
        ref_current = db.reference(f'trucks/{truck_id}/current')
        ref_current.set({
            'lat': lat, 'lon': lon, 
            'timestamp': time.strftime("%H:%M:%S", time.localtime())
        })
        ref_path = db.reference(f'trucks/{truck_id}/path')
        ref_path.push({'lat': lat, 'lon': lon, 'time': time.time()})
    except Exception as e:
        st.error(f"Update failed: {e}")

def get_all_trucks():
    try:
        ref = db.reference('trucks')
        return ref.get()
    except Exception as e:
        st.error(f"Fetch failed: {e}")
        return None

def clear_database():
    db.reference('trucks').delete()

# --- 4. ระบบ Login ---
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
        else:
            st.error("❌ รหัสผ่านไม่ถูกต้อง")

# --- 5. เมื่อ Login สำเร็จแล้ว ---
else:
    st_autorefresh(interval=5000, key="datarefresh")
    st.sidebar.title(f"👤 {st.session_state.role}")
    if st.sidebar.button("Log out"):
        st.session_state.logged_in = False
        st.rerun()

    if st.session_state.role == "Driver (คนขับรถ)":
        st.title("🚛 แผงควบคุมคนขับ (Smart Driver)")
        truck_id = st.sidebar.selectbox("เลือกหมายเลขรถ", ["Truck_01", "Truck_02", "Truck_03"])
        auto_on = st.toggle("🔄 เปิดระบบ Auto Tracking")
        st.write("---")
        col1, col2 = st.columns(2)
        with col1: lat_in = st.number_input("Lat", value=14.882, format="%.6f")
        with col2: lon_in = st.number_input("Lon", value=102.021, format="%.6f")
        
        if auto_on:
            update_location(truck_id, lat_in, lon_in)
            st.info(f"📡 กำลังส่งข้อมูล {truck_id}...")
            st.markdown('<i class="fa fa-gear gear-icon"></i> ระบบกำลังทำงาน...', unsafe_allow_html=True)
        else:
            if st.button("📍 ส่งตำแหน่งปัจจุบัน"):
                with st.spinner("กำลังบันทึก..."):
                    update_location(truck_id, lat_in, lon_in)
                st.success("สำเร็จ!")

    else:
        h1, h2, h3 = st.columns([3, 1, 1])
        with h1: st.title("👨‍💼 ระบบติดตามรถขยะรวม")
        with h2: 
            if st.button("🔄 อัปเดต"): st.rerun()
        with h3:
            if st.button("🗑️ ล้างข้อมูล"): st.session_state.confirm_delete = True
        
        if st.session_state.get('confirm_delete', False):
            if st.button("✅ ยืนยันลบ"):
                clear_database()
                st.session_state.confirm_delete = False
                st.rerun()
            if st.button("❌ ยกเลิก"):
                st.session_state.confirm_delete = False
                st.rerun()

        all_data = get_all_trucks()
        if all_data:
            m = folium.Map(location=[14.882, 102.021], zoom_start=15)
            colors = {"Truck_01": "green", "Truck_02": "blue", "Truck_03": "orange"}
            for t_id, t_data in all_data.items():
                color = colors.get(t_id, "red")
                if 'path' in t_data:
                    pts = [[p['lat'], p['lon']] for p in t_data['path'].values()]
                    if len(pts) > 1: folium.PolyLine(pts, color=color, weight=4).add_to(m)
                if 'current' in t_data:
                    curr = t_data['current']
                    folium.Marker([curr['lat'], curr['lon']], popup=t_id,
                                  icon=folium.Icon(color=color, icon='truck', prefix='fa')).add_to(m)
            st_folium(m, width="100%", height=550, key="path_map")