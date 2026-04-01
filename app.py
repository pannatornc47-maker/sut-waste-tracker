import streamlit as st
import folium
from streamlit_folium import st_folium
import firebase_admin
from firebase_admin import credentials, db
import time
from streamlit_autorefresh import st_autorefresh

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="SUT Waste Tracker", page_icon="🚛", layout="wide")

# --- 2. เชื่อมต่อ Firebase ผ่าน Secrets ---
if not firebase_admin._apps:
    try:
        # ดึงข้อมูลจาก Secrets ที่คุณตั้งไว้ใน Streamlit Cloud
        fb_creds = dict(st.secrets["firebase"])
        fb_creds["private_key"] = fb_creds["private_key"].replace("\\n", "\n")
        
        cred = credentials.Certificate(fb_creds)
        
        # *** ตรวจสอบ URL นี้ให้ตรงกับหน้า Realtime Database ของคุณ ***
        db_url = "https://sut-waste-tracker-default-rtdb.asia-southeast1.firebasedatabase.app/"
        
        firebase_admin.initialize_app(cred, {'databaseURL': db_url})
    except Exception as e:
        st.error(f"❌ Firebase Connection Error: {e}")

# --- 3. ฟังก์ชันจัดการข้อมูล (พร้อมระบบดักจับ Error) ---
def update_location(truck_id, lat, lon):
    try:
        # 1. อัปเดตตำแหน่งปัจจุบัน
        ref_current = db.reference(f'trucks/{truck_id}/current')
        ref_current.set({
            'lat': lat, 
            'lon': lon, 
            'timestamp': time.strftime("%H:%M:%S")
        })
        
        # 2. บันทึกประวัติเส้นทาง
        ref_path = db.reference(f'trucks/{truck_id}/path')
        ref_path.push({
            'lat': lat, 
            'lon': lon, 
            'time': time.time()
        })
        
        return True, "สำเร็จ"
    except Exception as e:
        # คืนค่า Error กลับไปแสดงบนหน้าจอ
        return False, str(e)

def get_all_trucks():
    try:
        return db.reference('trucks').get()
    except:
        return None

# --- 4. ส่วนของ UI และ Logic ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 SUT Waste Tracker Login")
    role = st.selectbox("เลือกสถานะ", ["Driver (คนขับรถ)", "Manager (ผู้ดูแล)"])
    pw = st.text_input("รหัสผ่าน", type="password")
    if st.button("เข้าสู่ระบบ"):
        if pw == "1234":
            st.session_state.logged_in = True
            st.session_state.role = role
            st.rerun()
        else:
            st.error("รหัสผ่านไม่ถูกต้อง")
else:
    # รีเฟรชหน้าจอทุก 5 วินาที
    st_autorefresh(interval=5000, key="datarefresh")
    
    st.sidebar.title(f"ผู้ใช้: {st.session_state.role}")
    if st.sidebar.button("ออกจากระบบ"):
        st.session_state.logged_in = False
        st.rerun()

    # --- หน้าคนขับรถ ---
    if st.session_state.role == "Driver (คนขับรถ)":
        st.title("🚛 ส่งพิกัดตำแหน่งรถขยะ")
        truck_id = st.selectbox("เลือกหมายเลขรถ", ["Truck_01", "Truck_02", "Truck_03"])
        
        col1, col2 = st.columns(2)
        lat = col1.number_input("Latitude", value=14.882000, format="%.6f")
        lon = col2.number_input("Longitude", value=102.021000, format="%.6f")
        
        auto_send = st.toggle("ส่งข้อมูลอัตโนมัติ (ทุก 5 วินาที)")
        
        if auto_send or st.button("📍 ส่งตำแหน่งเดี๋ยวนี้"):
            success, message = update_location(truck_id, lat, lon)
            if success:
                st.success(f"✅ บันทึกตำแหน่ง {truck_id} แล้วตอน {time.strftime('%H:%M:%S')}")
            else:
                # ถ้าไม่สำเร็จ จะโชว์สาเหตุที่แท้จริงจาก Firebase
                st.error(f"❌ ส่งไม่สำเร็จ: {message}")
                st.info("คำแนะนำ: ตรวจสอบว่าใน Firebase Rules ตั้งค่าเป็น .read: true และ .write: true หรือยัง")

    # --- หน้าผู้ดูแล ---
    else:
        st.title("👨‍💼 แผนที่ติดตามรถขยะ (Manager)")
        data = get_all_trucks()
        
        if data:
            m = folium.Map(location=[14.882, 102.021], zoom_start=15)
            colors = {"Truck_01": "green", "Truck_02": "blue", "Truck_03": "orange"}
            
            for tid, info in data.items():
                c = colors.get(tid, "red")
                if 'path' in info:
                    pts = [[p['lat'], p['lon']] for p in info['path'].values()]
                    folium.PolyLine(pts, color=c, weight=4).add_to(m)
                
                if 'current' in info:
                    curr = info['current']
                    folium.Marker(
                        [curr['lat'], curr['lon']],
                        popup=f"{tid} ({curr['timestamp']})",
                        icon=folium.Icon(color=c, icon='truck', prefix='fa')
                    ).add_to(m)
            
            st_folium(m, width="100%", height=600)
            st.subheader("ข้อมูลดิบจากระบบ")
            st.write(data)
        else:
            st.info("ℹ️ ยังไม่มีข้อมูลรถออนไลน์")
