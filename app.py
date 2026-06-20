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

# 初始化 session_state 用來儲存鎖定的店家
if 'selected_cafe' not in st.session_state:
    st.session_state['selected_cafe'] = None

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

# 地理編碼功能
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

# 側邊欄
st.sidebar.header("🔍 搜尋設定")
user_keyword = st.sidebar.text_input("店名關鍵字")
transport_mode = st.sidebar.selectbox("代步工具", ("🚶 步行", "🛵 機車", "🚗 汽車"))
speed = {"🚶 步行": 0.07, "🛵 機車": 0.50, "🚗 汽車": 0.66}[transport_mode]
minutes = st.sidebar.slider("最大移動時間 (分鐘)", 5, 90, 15, 5)

tag_map = {
    "limited_time": "⏳ 限時", "midnight": "🌙 深夜", "pudding": "🍮 布丁",
    "basque": "🍰 巴斯克", "tiramisu": "🍫 提拉米蘇", "dessert": "🧁 甜點",
    "salty_food": "🥪 鹹食", "café": "☕ 咖啡", "study": "💻 讀書",
    "chat": "💬 聊天", "photo": "📷 拍照", "pet": "🐾 寵物", "wifi": "🌐 WiFi"
}
active_tags = [col for col, label in tag_map.items() if st.sidebar.checkbox(label)]

# 定位
st.write("### 📍 位置權限與起點設定")
loc_type = st.radio("請選擇定位方式：", ("GPS 定位", "手動輸入地址"), horizontal=True)
my_lat, my_lng = 24.9537, 121.2256
if loc_type == "GPS 定位":
    st.info("💡 **定位小提醒：** 請點擊下方出現的 **「Get Location」** 按鈕，並選擇 **「允許」**。")
    geo = streamlit_geolocation()
    if geo and geo.get('latitude'):
        my_lat, my_lng = geo['latitude'], geo['longitude']
        st.success("✅ 定位成功！")
else:
    addr = st.text_input("🏠 輸入地址：", value="中壢火車站")
    my_lat, my_lng = geocode_address(addr)

# 搜尋
results = search_cafes(my_lat, my_lng, active_tags, user_keyword, minutes * speed)

# 地圖
st.write(f"### 📍 地圖搜尋結果 ({len(results)} 間)")
mymap = folium.Map(location=[my_lat, my_lng], zoom_start=14)
folium.Marker([my_lat, my_lng], popup="起點", icon=folium.Icon(color="red", icon="user", prefix="fa")).add_to(mymap)

for _, row in results.iterrows():
    folium.Marker([row["lat"], row["lng"]], popup=row["name"], tooltip=row["name"], icon=folium.Icon(color="blue", icon="coffee", prefix="fa")).add_to(mymap)

map_data = st_folium(mymap, width=850, height=500)

# 更新鎖定狀態
if map_data['last_object_clicked_tooltip']:
    st.session_state['selected_cafe'] = map_data['last_object_clicked_tooltip']

# 顯示結果與重置邏輯
if not results.empty:
    if st.session_state['selected_cafe']:
        # 檢查該店家是否還在目前的搜尋結果中
        if st.session_state['selected_cafe'] in results["name"].values:
            st.success(f"🎯 已鎖定店家：{st.session_state['selected_cafe']}")
            if st.button("❌ 取消鎖定，查看全部"):
                st.session_state['selected_cafe'] = None
                st.rerun()
            display_df = results[results["name"] == st.session_state['selected_cafe']]
        else:
            st.session_state['selected_cafe'] = None # 店家已消失，自動解鎖
            display_df = results
    else:
        display_df = results

    # 顯示 dataframe
    label_map = {
        "limited_time": {1: "⏳ 限時", 0: "不限時"}, "midnight": {1: "🌙 深夜", 0: "無"},
        "pudding": {1: "🍮 提供布丁", 0: "無提供布丁"}, "basque": {1: "🍰 提供巴斯克", 0: "無巴斯克"},
        "tiramisu": {1: "🍫 提供提拉米蘇", 0: "無提拉米蘇"}, "dessert": {1: "🧁 提供甜點", 0: "無提供甜點"},
        "salty_food": {1: "🥪 提供鹹食、正餐", 0: "無鹹食、正餐"}, "café": {1: "☕ 提供咖啡", 0: "無提供咖啡"},
        "study": {1: "💻 適合讀書", 0: "不適合讀書"}, "chat": {1: "💬 適合聊天", 0: "不適合聊天"},
        "photo": {1: "📷 適合拍照", 0: "不適合拍照"}, "pet": {1: "🐾 可攜寵物", 0: "禁止寵物入內"},
        "wifi": {1: "🌐 提供 WiFi", 0: "無提供 WiFi"}
    }
    
    display_df = display_df.copy()
    for col, mapping in label_map.items():
        if col in display_df.columns: display_df[col] = display_df[col].map(mapping)
    
    st.dataframe(display_df, use_container_width=True)
