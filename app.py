import math, folium, pandas as pd, streamlit as st, urllib.parse, requests
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation

st.set_page_config(page_title="桃憩時光", page_icon="☕", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("cafe.csv", encoding='utf-8-sig').fillna({"open_hours": "詳見粉專"})
    return df

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# ─── 介面與邏輯 ───
st.title("☕ 桃憩時光 (Tao-Café Finder)")
st.sidebar.header("🔍 搜尋設定")
user_keyword = st.sidebar.text_input("店名關鍵字")
minutes = st.sidebar.slider("最大移動時間 (分鐘)", 5, 90, 15)
speed = {"🚶 步行": 0.07, "🛵 機車": 0.50, "🚗 汽車": 0.66}[st.sidebar.selectbox("代步工具", ("🚶 步行", "🛵 機車", "🚗 汽車"))]

active_tags = [col for col, label in {"limited_time": "⏳ 限時", "midnight": "🌙 深夜", "wifi": "🌐 WiFi"}.items() if st.sidebar.checkbox(label)]

# 定位與搜尋
loc_type = st.radio("定位方式：", ("GPS 定位", "手動輸入"), horizontal=True)
my_lat, my_lng = (24.9537, 121.2256) if loc_type == "手動輸入" else (streamlit_geolocation()['latitude'] or 24.9537, streamlit_geolocation()['longitude'] or 121.2256)

df = load_data()
df["distance"] = df.apply(lambda row: haversine(my_lat, my_lng, row["lat"], row["lng"]), axis=1)
results = df[df["distance"] <= (minutes * speed)]
for tag in active_tags: results = results[results[tag] == 1]

# 地圖與互動
mymap = folium.Map(location=[my_lat, my_lng], zoom_start=14)
folium.Marker([my_lat, my_lng], icon=folium.Icon(color="red", icon="user")).add_to(mymap)
for _, row in results.iterrows():
    folium.Marker([row["lat"], row["lng"]], popup=row["name"], tooltip=row["name"], icon=folium.Icon(color="blue", icon="coffee")).add_to(mymap)

map_data = st_folium(mymap, width=850, height=500)

# 焦點控制
selected_name = map_data['last_object_clicked_tooltip']
if selected_name:
    st.success(f"🎯 選中：{selected_name}")
    st.dataframe(results[results["name"] == selected_name], use_container_width=True)
else:
    st.dataframe(results, use_container_width=True)
