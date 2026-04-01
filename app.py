import streamlit as st
import folium
from streamlit_folium import st_folium
import firebase_admin
from firebase_admin import credentials, db
import time
from streamlit_autorefresh import st_autorefresh

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="SUT Waste Smart Tracking", page_icon="⚙️", layout="wide")

# CSS สำหรับไอคอนเกียร์หมุน และความสวยงาม
st.markdown(
    """
    <style>
    .stSpinner i { color: #FF4B4B !important; }
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    .gear-icon { display: inline-block; animation: spin 2s infinite linear; font-size: 24px; color: #FF4B4B; }
    /* ปรับปุ่มลบให้เป็นสีแดง */
    div.stButton > button:first-child { border-radius: 5px; }
    .clear-btn { color: white; background-color: #FF4B4B; }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
    """,
    unsafe_allow_html=True
)

# --- 2. เชื่อมต่อ Firebase ---
if not firebase_admin._apps:
    databaseURL = "https://sut-waste-tracker-default-rtdb.asia-southeast1.firebasedatabase.app/"
    try:
        cred = credentials.Certificate("key.json")
        firebase_admin.initialize_app(cred, {'databaseURL': databaseURL})
    except Exception as e:
        st.error(f"⚠️ Firebase Connection Error: {e}")

# --- 3. ฟังก์ชันจัดการข้อมูล ---
def update_location(truck_id, lat, lon):
    ref_current = db.reference(f'trucks/{truck_id}/current')
    ref_current.set({
        'lat': lat, 'lon': lon, 
        'timestamp': time.strftime("%H:%M:%S", time.localtime())
    })
    ref_path = db.reference(f'trucks/{truck_id}/path')
    ref_path.push({'lat': lat, 'lon': lon, 'time': time.time()})

def get_all_trucks():
    ref = db.reference('trucks')
    return ref.get()

def clear_database():
    ref = db.reference('trucks')
    ref.delete()

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
    # Auto-refresh ทุก 5 วินาที
    st_autorefresh(interval=5000, key="datarefresh")

    st.sidebar.title(f"👤 {st.session_state.role}")
    if st.sidebar.button("ออกจากระบบ (Log out)"):
        st.session_state.logged_in = False
        st.rerun()

    # --- [หน้าสำหรับ DRIVER] ---
    if st.session_state.role == "Driver (คนขับรถ)":
        st.title("🚛 แผงควบคุมคนขับ (Smart Driver)")
        truck_id = st.sidebar.selectbox("เลือกหมายเลขรถ", ["Truck_01", "Truck_02", "Truck_03"])
        
        auto_on = st.toggle("🔄 เปิดระบบ Auto Tracking (ส่งพิกัดทุก 5 วินาที)")
        
        st.write("---")
        col1, col2 = st.columns(2)
        with col1: lat_in = st.number_input("ละติจูด (Lat)", value=14.882, format="%.6f")
        with col2: lon_in = st.number_input("ลองจิจูด (Lon)", value=102.021, format="%.6f")
        
        if auto_on:
            update_location(truck_id, lat_in, lon_in)
            st.info(f"📡 กำลังส่งข้อมูล {truck_id} อัตโนมัติ...")
            st.markdown('<i class="fa fa-gear gear-icon"></i> ระบบกำลังทำงาน...', unsafe_allow_html=True)
        else:
            if st.button("📍 ส่งตำแหน่งปัจจุบัน (Manual)"):
                with st.spinner("กำลังบันทึก..."):
                    update_location(truck_id, lat_in, lon_in)
                st.success(f"บันทึกตำแหน่ง {truck_id} สำเร็จ!")

    # --- [หน้าสำหรับ MANAGER] ---
    else:
        # ส่วนหัว Manager พร้อมปุ่มจัดการข้อมูล
        h1, h2, h3 = st.columns([3, 1, 1])
        with h1: 
            st.title("👨‍💼 ระบบติดตามรถขยะรวม")
        with h2:
            st.write("") # เว้นระยะ
            if st.button("🔄 อัปเดต"): 
                st.rerun()
        with h3:
            st.write("") # เว้นระยะ
            # ปุ่มเคลียร์ข้อมูลพร้อมระบบยืนยัน
            if st.button("🗑️ ล้างข้อมูลทั้งหมด"):
                st.session_state.confirm_delete = True
        
        # ส่วนกดยืนยันการลบ
        if st.session_state.get('confirm_delete', False):
            st.warning("⚠️ คุณแน่ใจใช่ไหมว่าจะลบพิกัดและเส้นทางทั้งหมด?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ ใช่, ลบเลย"):
                    clear_database()
                    st.session_state.confirm_delete = False
                    st.success("ล้างข้อมูลเรียบร้อยแล้ว!")
                    time.sleep(1)
                    st.rerun()
            with c2:
                if st.button("❌ ยกเลิก"):
                    st.session_state.confirm_delete = False
                    st.rerun()

        with st.spinner("กำลังโหลดข้อมูลพิกัดล่าสุด..."):
            all_data = get_all_trucks()
        
        if all_data:
            m = folium.Map(location=[14.882, 102.021], zoom_start=15)
            colors = {"Truck_01": "green", "Truck_02": "blue", "Truck_03": "orange"}
            
            for t_id, t_data in all_data.items():
                color = colors.get(t_id, "red")
                if 'path' in t_data:
                    points = [[p['lat'], p['lon']] for p in t_data['path'].values()]
                    if len(points) > 1:
                        folium.PolyLine(points, color=color, weight=4, opacity=0.6).add_to(m)
                if 'current' in t_data:
                    curr = t_data['current']
                    folium.Marker([curr['lat'], curr['lon']], 
                                  popup=f"{t_id}: {curr['timestamp']}",
                                  icon=folium.Icon(color=color, icon='truck', prefix='fa')).add_to(m)
            st_folium(m, width="100%", height=550, key="path_map")
        else:
            st.warning("⏳ ยังไม่มีข้อมูลรถในระบบ (หรือเพิ่งถูกล้างข้อมูล)")