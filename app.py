import math
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
import urllib.parse
import requests
from streamlit_geolocation import streamlit_geolocation

# 設定網頁標題與圖標
st.set_page_config(page_title="桃憩時光 - 桃園智慧咖啡廳搜尋", page_icon="☕", layout="wide")

# --- 讀取並處理資料 ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("cafe.csv", encoding='utf-8-sig')
        tag_cols = ["limited_time", "midnight", "pudding", "basque", "tiramisu", 
                    "dessert", "salty_food", "café", "study", "chat", "photo", "pet", "wifi"]
        for col in tag_cols:
            if col not in df.columns:
                df[col] = 0
        df = df.fillna({"open_hours": "詳見官方粉絲專頁"})
        return df
    except Exception as e:
        st.error(f"讀取 cafe.csv 失敗: {e}")
        return pd.DataFrame()

# 1. 哈維辛公式
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# 2. 地理編碼功能
@st.cache_data
def geocode_address(address):
    default_lat, default_lng = 24.9537, 121.2256
    if not address.strip() or address == "中壢火車站": return default_lat, default_lng
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(address)}&format=json&limit=1"
        res = requests.get(url, headers={'User-Agent': 'TaoCafeFinder'}, timeout=5).json()
        if res: return float(res[0]['lat']), float(res[0]['lon'])
    except: pass
    return default_lat, default_lng

def search_cafes(user_lat, user_lng, selected_tags, keyword="", max_distance_km=1.0):
    df = load_data()
    if df.empty: return df
    df["distance"] = df.apply(lambda row: haversine(user_lat, user_lng, row["lat"], row["lng"]), axis=1)
    filtered_df = df[df["distance"] <= max_distance_km].copy()
    for tag in selected_tags:
        filtered_df = filtered_df[filtered_df[tag] == 1]
    if keyword.strip():
        filtered_df = filtered_df[filtered_df["name"].str.contains(keyword, na=False, case=False)]
    return filtered_df

# ─── 前端介面 ───
st.title("☕ 桃憩時光 (Tao-Café Finder)")

# 側邊欄控制
st.sidebar.header("🔍 搜尋設定")
user_keyword = st.sidebar.text_input("店名關鍵字")
transport_mode = st.sidebar.selectbox("代步工具", ("🚶 步行", "🛵 機車", "🚗 汽車"))
speed = {"🚶 步行": 0.07, "🛵 機車": 0.50, "🚗 汽車": 0.66}[transport_mode]
minutes = st.sidebar.slider("最大移動時間 (分鐘)", 5, 90, 15, 5)

st.sidebar.write("📌 空間與氛圍標籤：")
tag_map = {
    "limited_time": "⏳ 限時", "midnight": "🌙 深夜", "pudding": "🍮 布丁",
    "basque": "🍰 巴斯克", "tiramisu": "🍫 提拉米蘇", "dessert": "🧁 甜點",
    "salty_food": "🥪 鹹食", "café": "☕ 咖啡", "study": "💻 讀書",
    "chat": "💬 聊天", "photo": "📷 拍照", "pet": "🐾 寵物", "wifi": "🌐 WiFi"
}
active_tags = [col for col, label in tag_map.items() if st.sidebar.checkbox(label)]

# --- 定位方式區塊 ---
st.write("### 📍 位置權限與起點設定")
loc_type = st.radio("請選擇定位方式：", ("GPS 定位", "手動輸入地址"), horizontal=True)

my_lat, my_lng = 24.9537, 121.2256
if loc_type == "GPS 定位":
    st.info("💡 **定位小提醒：** 為了確保定位準確，請點擊下方出現的 **「Get Location」** 按鈕，並在瀏覽器權限視窗選擇 **「允許」**。")
    geo = streamlit_geolocation()
    if geo and geo.get('latitude'):
        my_lat, my_lng = geo['latitude'], geo['longitude']
        st.success("✅ 定位成功！系統已抓取您的當前位置。")
    else:
        st.warning("⚠️ 尚未定位，請點擊上方按鈕開始定位。")
else:
    addr = st.text_input("🏠 輸入地址：", value="中壢火車站")
    my_lat, my_lng = geocode_address(addr)

# 執行搜尋與顯示
results = search_cafes(my_lat, my_lng, active_tags, user_keyword, minutes * speed)

st.write(f"### 📍 地圖搜尋結果 ({len(results)} 間)")
mymap = folium.Map(location=[my_lat, my_lng], zoom_start=14)

# 使用 user 圖示標記起點，避免出現數字
folium.Marker([my_lat, my_lng], popup="您的起點", icon=folium.Icon(color="red", icon="user", prefix="fa")).add_to(mymap)

for _, row in results.iterrows():
    # 使用 coffee 圖示標記咖啡廳
    folium.Marker([row["lat"], row["lng"]], popup=row["name"], icon=folium.Icon(color="blue", icon="coffee", prefix="fa")).add_to(mymap)

st_folium(mymap, width=850, height=500)
st.dataframe(results, use_container_width=True)
