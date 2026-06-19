import math
import os
import urllib.parse
import folium
import random
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation

# 設定網頁標題與圖標
st.set_page_config(page_title="桃憩時光 - 桃園智慧咖啡廳搜尋", page_icon="☕", layout="wide")

# --- 🌟 核心功能：動態爬蟲文本特徵工程 🌟 ---
def apply_dynamic_feature_engineering(df):
    """
    接收從 cafe.csv 讀入的 DataFrame。
    將 CSV 內的 0/1 數據與必要的欄位做整合與防錯處理。
    """
    # 確保 CSV 讀入後，若有遺漏欄位則自動補 0
    required_tags = ["limited_time", "midnight", "pudding", "basque", "tiramisu", 
                     "dessert", "salty_food", "café", "study", "chat", "photo", "pet", "wifi"]
    
    for tag in required_tags:
        if tag not in df.columns:
            df[tag] = 0
        else:
            df[tag] = df[tag].fillna(0).astype(int)

    # 確保營業時間等重要欄位不會因為空值導致地圖出錯
    df["open_hours"] = df["open_hours"].fillna("詳見官方粉絲專頁")
    
    return df

# --- 效能優化與資料讀取 ---
def load_data():
    try:
        # 讀取 CSV
        df = pd.read_csv("cafe.csv", encoding='utf-8-sig')
        # 進行欄位整理與填充
        df = apply_dynamic_feature_engineering(df)
        return df
    except FileNotFoundError:
        st.error("找不到 cafe.csv 檔案！請確認檔案與程式碼在同一個資料夾。")
        return pd.DataFrame()

# 1. 哈維辛公式：計算直線距離
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# 2. 正向地理編碼
@st.cache_data
def geocode_address(address):
    default_lat, default_lng = 24.9537, 121.2256
    if not address.strip() or address == "中壢火車站":
        return default_lat, default_lng
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(address)}&format=json&limit=1"
        headers = {'User-Agent': 'TaoCafeFinder/1.0'}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception:
        pass
    return default_lat, default_lng

# 3. 反向地理編碼
@st.cache_data
def reverse_geocode(lat, lng):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json"
        headers = {'User-Agent': 'TaoCafeFinder/1.0'}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        if data and "display_name" in data:
            return data["display_name"].split(',')[0]
    except Exception:
        pass
    return "您的當前位置"

# 4. 智慧搜尋核心函式
def search_cafes(user_lat, user_lng, selected_tags, keyword="", max_distance_km=1.0):
    df = load_data()
    if df.empty:
        return df

    # 計算距離
    df["distance"] = df.apply(lambda row: haversine(user_lat, user_lng, row["lat"], row["lng"]), axis=1)
    filtered_df = df[df["distance"] <= max_distance_km].copy()

    # 標籤過濾
    for tag in selected_tags:
        if tag in filtered_df.columns:
            filtered_df = filtered_df[filtered_df[tag] == 1]

    # 關鍵字過濾
    if keyword.strip():
        filtered_df = filtered_df[filtered_df["name"].str.contains(keyword, na=False, case=False)]
    return filtered_df

# ─── Streamlit 前端網頁介面設計 ───
st.title("☕ 桃憩時光 (Tao-Café Finder)")
st.subheader("桃園專屬智慧標籤與交通圈咖啡廳導航系統")

st.write("### 📍 位置權限與起點設定")
location_consent = st.radio("設定您的出發位置：", ("✅ 使用 GPS 定位", "❌ 手動設定起點"), horizontal=True)

my_lat, my_lng = 24.9537, 121.2256
current_loc_title = "中壢火車站"

if location_consent == "✅ 使用 GPS 定位":
    gps_location = streamlit_geolocation()
    if gps_location and gps_location.get('latitude'):
        my_lat, my_lng = gps_location['latitude'], gps_location['longitude']
        current_loc_title = reverse_geocode(my_lat, my_lng)
        st.success(f"🎯 已定位：{current_loc_title}")
else:
    user_address_input = st.text_input("🏠 輸入地址：", value="中壢火車站")
    my_lat, my_lng = geocode_address(user_address_input)
    current_loc_title = user_address_input

# ─── 側邊欄篩選 ───
st.sidebar.header("🔍 搜尋條件")
user_keyword = st.sidebar.text_input("店名關鍵字：")
transport_mode = st.sidebar.selectbox("🚗 代步工具：", ("🚶 步行", "🛵 機車", "🚗 汽車"))

# 計算速度設定
speed_map = {"🚶 步行": 0.07, "🛵 機車": 0.50, "🚗 汽車": 0.66}
speed_per_minute = speed_map[transport_mode]
travel_minutes = st.sidebar.slider("預計最大移動時間 (分鐘)", 5, 90, 15, 5)
max_dist = travel_minutes * speed_per_minute

st.sidebar.write("📌 空間與氛圍標籤：")
tag_dict = {
    "limited_time": "⏳ 限時", "midnight": "🌙 深夜", "pudding": "🍮 布丁",
    "basque": "🍰 巴斯克", "tiramisu": "🍫 提拉米蘇", "dessert": "🧁 甜點",
    "salty_food": "🥪 鹹食", "café": "☕ 咖啡", "study": "💻 讀書",
    "chat": "💬 聊天", "photo": "📷 拍照", "pet": "🐾 寵物", "wifi": "🌐 WiFi"
}
active_tags = [key for key, label in tag_dict.items() if st.sidebar.checkbox(label)]

results = search_cafes(my_lat, my_lng, active_tags, keyword=user_keyword, max_distance_km=max_dist)

# ─── 地圖渲染 ───
st.write(f"### 📍 地圖與搜尋結果")
mymap = folium.Map(location=[my_lat, my_lng], zoom_start=14)
folium.Marker([my_lat, my_lng], popup="您的位置", icon=folium.Icon(color="red")).add_to(mymap)

if not results.empty:
    st.success(f"找到 {len(results)} 間咖啡廳！")
    for _, row in results.iterrows():
        folium.Marker([row["lat"], row["lng"]], popup=f"{row['name']}<br>營業時間: {row['open_hours']}").add_to(mymap)
    st_folium(mymap, width=850, height=500)
    st.dataframe(results, use_container_width=True)
else:
    st.warning("此條件下暫無結果。")
