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
            if col not in df.columns: df[col] = 0
        df = df.fillna({"open_hours": "詳見官方粉絲專頁"})
        return df
    except Exception as e:
        st.error(f"讀取 cafe.csv 失敗: {e}")
        return pd.DataFrame()

# 哈維辛公式
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# 地理編碼
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

# ─── 前端介面 ───
st.title("☕ 桃憩時光 (Tao-Café Finder)")

# 側邊欄控制
st.sidebar.header("🔍 搜尋設定")
user_keyword = st.sidebar.text_input("店名關鍵字")
transport_mode = st.sidebar.selectbox("代步工具", ("🚶 步行", "🛵 機車", "🚗 汽車"))
speed = {"🚶 步行": 0.07, "🛵 機車": 0.50, "🚗 汽車": 0.66}[transport_mode]
minutes = st.sidebar.slider("最大移動時間 (分鐘)", 5, 90, 15, 5)

active_tags = [col for col, label in {
    "limited_time": "⏳ 限時", "midnight": "🌙 深夜", "pudding": "🍮 布丁",
    "basque": "🍰 巴斯克", "tiramisu": "🍫 提拉米蘇", "dessert": "🧁 甜點",
    "salty_food": "🥪 鹹食", "café": "☕ 咖啡", "study": "💻 讀書",
    "chat": "💬 聊天", "photo": "📷 拍照", "pet": "🐾 寵物", "wifi": "🌐 WiFi"
}.items() if st.sidebar.checkbox(label)]

# 定位
loc_type = st.radio("定位方式：", ("GPS 定位", "手動輸入地址"), horizontal=True)
my_lat, my_lng = (24.9537, 121.2256)
if loc_type == "GPS 定位":
    geo = streamlit_geolocation()
    if geo and geo.get('latitude'): my_lat, my_lng = geo['latitude'], geo['longitude']
else:
    addr = st.text_input("🏠 輸入地址：", value="中壢火車站")
    my_lat, my_lng = geocode_address(addr)

# 搜尋邏輯
df = load_data()
df["distance"] = df.apply(lambda row: haversine(my_lat, my_lng, row["lat"], row["lng"]), axis=1)
results = df[df["distance"] <= (minutes * speed)].copy()
for tag in active_tags: results = results[results[tag] == 1]
if user_keyword.strip(): results = results[results["name"].str.contains(user_keyword, na=False, case=False)]

# 地圖顯示與互動
st.write(f"### 📍 地圖搜尋結果 ({len(results)} 間)")
mymap = folium.Map(location=[my_lat, my_lng], zoom_start=14)
folium.Marker([my_lat, my_lng], popup="起點", icon=folium.Icon(color="red", icon="user", prefix="fa")).add_to(mymap)

for _, row in results.iterrows():
    folium.Marker([row["lat"], row["lng"]], popup=row["name"], tooltip=row["name"], icon=folium.Icon(color="blue", icon="coffee", prefix="fa")).add_to(mymap)

map_data = st_folium(mymap, width=850, height=500)

# 友善資訊顯示與互動聚焦
selected_name = map_data['last_object_clicked_tooltip']
if selected_name:
    st.success(f"👆 已鎖定店家：**{selected_name}**")
    display_results = results[results["name"] == selected_name]
else:
    display_results = results

# 表格轉換
label_map = {
    "limited_time": {1: "⏳ 限時", 0: "不限時"}, "midnight": {1: "🌙 深夜", 0: "無"},
    "pudding": {1: "🍮 提供布丁", 0: "無提供布丁"}, "basque": {1: "🍰 提供巴斯克", 0: "無巴斯克"},
    "tiramisu": {1: "🍫 提供提拉米蘇", 0: "無提拉米蘇"}, "dessert": {1: "🧁 提供甜點", 0: "無提供甜點"},
    "salty_food": {1: "🥪 提供鹹食、正餐", 0: "無鹹食、正餐"}, "café": {1: "☕ 提供咖啡", 0: "無提供咖啡"},
    "study": {1: "💻 適合讀書", 0: "不適合讀書"}, "chat": {1: "💬 適合聊天", 0: "不適合聊天"},
    "photo": {1: "📷 適合拍照", 0: "不適合拍照"}, "pet": {1: "🐾 可攜寵物", 0: "禁止寵物入內"},
    "wifi": {1: "🌐 提供 WiFi", 0: "無提供 WiFi"}
}
display_df = display_results.copy()
for col, mapping in label_map.items():
    if col in display_df.columns: display_df[col] = display_df[col].map(mapping)

st.dataframe(display_df, use_container_width=True)
