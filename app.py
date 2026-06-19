import math
import os
import urllib.parse
import folium
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation

# 設定網頁標題與圖標
st.set_page_config(page_title="桃憩時光 - 桃園智慧咖啡廳搜尋", page_icon="☕", layout="wide")

# --- 核心功能：讀取並確保資料欄位對齊 ---
def load_data():
    try:
        # 讀取 CSV
        df = pd.read_csv("cafe.csv", encoding='utf-8-sig')
        
        # 定義正確的欄位名稱 (根據你最新要求的順序)
        expected_cols = [
            "name", "address", "lat", "lng", "open_hour", "rest_days", 
            "limited_time", "midnight", "pudding", "basque", "tiramisu", 
            "dessert", "salty_food", "café", "study", "chat", "photo", "pet", "wifi"
        ]
        
        # 確保所有需要的欄位都存在，若缺少的補為 0
        for col in expected_cols:
            if col not in df.columns:
                df[col] = 0
                
        # 確保營業時間與公休日欄位為字串
        df["open_hour"] = df["open_hour"].fillna("詳見粉絲專頁")
        df["rest_days"] = df["rest_days"].fillna("無")
        
        return df[expected_cols]
    except Exception as e:
        st.error(f"讀取 cafe.csv 失敗: {e}")
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

# 2. 地理編碼與搜尋
@st.cache_data
def geocode_address(address):
    default_lat, default_lng = 24.9537, 121.2256
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(address)}&format=json&limit=1"
        response = requests.get(url, headers={'User-Agent': 'TaoCafeFinder'}, timeout=5).json()
        if response: return float(response[0]['lat']), float(response[0]['lon'])
    except: pass
    return default_lat, default_lng

def search_cafes(user_lat, user_lng, selected_tags, keyword="", max_distance_km=1.0):
    df = load_data()
    if df.empty: return df
    df["distance"] = df.apply(lambda row: haversine(user_lat, user_lng, row["lat"], row["lng"]), axis=1)
    filtered_df = df[df["distance"] <= max_distance_km].copy()
    for tag in selected_tags:
        if tag in filtered_df.columns:
            filtered_df = filtered_df[filtered_df[tag] == 1]
    if keyword.strip():
        filtered_df = filtered_df[filtered_df["name"].str.contains(keyword, na=False, case=False)]
    return filtered_df

# ─── Streamlit 前端介面 ───
st.title("☕ 桃憩時光 (Tao-Café Finder)")

# 定義標籤 UI 對應
tag_map = {
    "limited_time": "⏳ 限時", "midnight": "🌙 深夜", "pudding": "🍮 布丁",
    "basque": "🍰 巴斯克", "tiramisu": "🍫 提拉米蘇", "dessert": "🧁 甜點",
    "salty_food": "🥪 鹹食", "café": "☕ 咖啡", "study": "💻 讀書",
    "chat": "💬 聊天", "photo": "📷 拍照", "pet": "🐾 寵物", "wifi": "🌐 WiFi"
}

st.sidebar.header("🔍 搜尋與篩選條件")
user_keyword = st.sidebar.text_input("店名關鍵字：")
active_tags = [col for col, label in tag_map.items() if st.sidebar.checkbox(label)]

# 位置設定 (簡易版)
st.sidebar.write("---")
user_address = st.sidebar.text_input("出發地：", value="中壢火車站")
my_lat, my_lng = geocode_address(user_address)

# 搜尋結果
results = search_cafes(my_lat, my_lng, active_tags, keyword=user_keyword, max_distance_km=5.0)

st.write(f"### 📍 搜尋結果 ({len(results)} 間)")
if not results.empty:
    mymap = folium.Map(location=[my_lat, my_lng], zoom_start=15)
    folium.Marker([my_lat, my_lng], popup="起點", icon=folium.Icon(color="red")).add_to(mymap)
    for _, row in results.iterrows():
        folium.Marker([row["lat"], row["lng"]], popup=f"{row['name']}<br>營業時間: {row['open_hour']}").add_to(mymap)
    st_folium(mymap, width=850, height=400)
    st.dataframe(results, use_container_width=True)
else:
    st.warning("暫無符合條件的店家。")
