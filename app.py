import streamlit as st
import folium
from streamlit_folium import st_folium
import firebase_admin
from firebase_admin import credentials, db
import time
from streamlit_autorefresh import st_autorefresh

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="SUT Waste Smart Tracking", page_icon="🚛", layout="wide")

# --- 2. เชื่อมต่อ Firebase ผ่าน Secrets (บรรทัดที่ 22 ที่แก้ไขแล้ว) ---
if not firebase_admin._apps:
    try:
        # ดึงข้อมูลจากตู้เซฟ Secrets
        fb_creds = dict(st.secrets["firebase"])
        
        # บรรทัดที่ 22: แก้ไขให้รองรับการอ่านรหัสลับทุกรูปแบบ (ป้องกัน Invalid JWT Signature)
        fb_creds["private_key"] = fb_creds["private_key"].replace("\\n", "\n")
        
        cred = credentials.Certificate(fb_creds)
        db_url = "https://sut-waste-tracker-default-rtdb.asia-southeast1.firebasedatabase.app/"
        firebase_admin.initialize_app(cred, {'databaseURL': db_url})
    except Exception as e:
        st.error(f"❌ Firebase Connection Error: {e}")

# --- 3. ฟังก์ชันจัดการข้อมูล ---
def update_location(truck_id, lat, lon):
    try:
        ref_current = db.reference(f'trucks/{truck_id}/current')
        ref_current.set({
            'lat': lat, 
            'lon': lon, 
            'timestamp': time.strftime("%H:%M:%S")
        })
        # บันทึกประวัติเส้นทาง (Path)
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

def clear_data():
    try:
        db.reference('trucks').delete()
        return True
    except:
        return False

# --- 4. ระบบ UI และ Login ---
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
    
    st.sidebar.title(f"👤 {st.session_state.role}")
    if st.sidebar.button("ออกจากระบบ"):
        st.session_state.logged_in = False
        st.rerun()

    # --- [หน้าคนขับรถ] ---
    if st.session_state.role == "Driver (คนขับรถ)":
        st.title("🚛 ระบบส่งตำแหน่งรถขยะ (Driver)")
        truck_id = st.selectbox("เลือกหมายเลขรถ", ["Truck_01", "Truck_02", "Truck_03"])
        
        col1, col2 = st.columns(2)
        lat = col1.number_input("Latitude", value=14.882000, format="%.6f")
        lon = col2.number_input("Longitude", value=102.021000, format="%.6f")
        
        auto_send = st.toggle("🔄 ส่งข้อมูลอัตโนมัติ (ทุก 5 วินาที)")
        
        if auto_send or st.button("📍 ส่งตำแหน่งเดี๋ยวนี้"):
            success, msg = update_location(truck_id, lat, lon)
            if success:
                st.success(f"✅ บันทึกตำแหน่ง {truck_id} แล้ว ({time.strftime('%H:%M:%S')})")
            else:
                st.error(f"❌ ส่งไม่สำเร็จ: {msg}")

    # --- [หน้าผู้ดูแล (Manager)] ---
    else:
        h1, h2 = st.columns([4, 1])
        with h1: st.title("👨‍💼 ติดตามรถขยะแบบ Real-time")
        with h2: 
            if st.button("🗑️ ล้างข้อมูล"):
                if clear_data(): st.success("ล้างข้อมูลแล้ว")
                st.rerun()

        data = get_all_trucks()
        if data:
            # สร้างแผนที่
            m = folium.Map(location=[14.882, 102.021], zoom_start=15)
            colors = {"Truck_01": "green", "Truck_02": "blue", "Truck_03": "orange"}
            
            for tid, info in data.items():
                c = colors.get(tid, "red")
                # วาดเส้นทาง
                if 'path' in info:
                    points = [[p['lat'], p['lon']] for p in info['path'].values()]
                    folium.PolyLine(points, color=c, weight=4, opacity=0.6).add_to(m)
                # ปักหมุดตำแหน่งล่าสุด
                if 'current' in info:
                    curr = info['current']
                    folium.Marker(
                        [curr['lat'], curr['lon']],
                        popup=f"รถ: {tid}<br>เวลา: {curr['timestamp']}",
                        icon=folium.Icon(color=c, icon='truck', prefix='fa')
                    ).add_to(m)
            
            st_folium(m, width="100%", height=600)
            st.subheader("📊 ข้อมูลดิบจากฐานข้อมูล")
            st.json(data)
        else:
            st.info("ℹ️ ยังไม่มีข้อมูลรถขยะในระบบ")
