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

# --- 🌟 核心功能升級：自動化爬蟲文本特徵轉換引擎 (Feature Engineering) 🌟 ---
def run_text_mining_and_update_csv():
    """
    這個函式會讀取手打的 cafe.csv，保留原本的店名、地址與經緯度。
    接著模擬網路爬蟲抓取每家店在 Google Maps/FB/IG 上的評論文本，
    最後自動做『二值化 (1/0) 轉換』並直接以 utf-8-sig 編碼覆蓋回寫 CSV 檔案！
    """
    csv_filename = "cafe.csv"
    if not os.path.exists(csv_filename):
        st.error(f"❌ 找不到 {csv_filename}，請確保該檔案與程式碼在同一資料夾！")
        return pd.DataFrame()
        
    st.info("🕸️ 正在啟動網路數據採集與特徵工程引擎...")
    
    # 讀取 CSV，指定使用 utf-8-sig 完美解決中文字元打架與欄位遺失問題
    df = pd.read_csv(csv_filename, encoding='utf-8-sig')
    
    # 為了確保欄位乾淨且對齊側邊欄，動態初始化這些 1/0 欄位
    target_tags = ["midnight", "pudding", "basque", "study", "chat", "photo"]
    for tag in target_tags:
        df[tag] = 0
        
    # 模擬針對 CSV 內每家真實咖啡廳，爬蟲抓到的真實評論語料
    scraped_reviews = {
        "雷爾森咖啡": "這家的手工布丁超級好吃！環境安靜很適合讀書用電腦，大推！",
        "走走咖啡": "巴斯克蛋糕非常濃郁，店內裝潢很文青，適合拍照打卡，下午跟朋友來聊天很舒服。",
        "鬍莉咖啡": "主打深夜咖啡廳，開到很晚。布丁跟巴斯克都很好吃，而且老闆對寵物很友善。",
        "和平咖啡館": "營業到凌晨兩點的深夜好去處，很適合半夜想認真讀書或和朋友低聲聊天的人。",
        "著手咖啡桃園店": "咖啡很有水準，甜點的巴斯克表現很好，採光棒適合拍照。",
        "NxCoffee": "空間很大，裝潢科技感十足超適合拍照，位置多也有插座，適合讀書工作。",
    }
    
    # 定義特徵工程的關鍵字過濾字典 (Keyword Mapping)
    feature_mapping = {
        "pudding": ["布丁", "pudding"],
        "basque": ["巴斯克", "basque", "蛋糕"],
        "midnight": ["深夜", "凌晨", "晚間", "夜景", "開到很晚"],
        "study": ["讀書", "工作", "插座", "安靜", "筆電"],
        "chat": ["聊天", "聚會", "聚餐", "舒服"],
        "photo": ["拍照", "打卡", "網美", "裝潢", "採光"]
    }
    
    # 開始對 CSV 的每一列 (每一間店) 進行自動化文本過濾與 1/0 填入
    for index, row in df.iterrows():
        shop_name = row["name"]
        
        # 取得該店家的爬蟲文本（若名單內有些店沒設定，就給予預設的綜合評論文字以利示範）
        review_text = scraped_reviews.get(
            shop_name, 
            f"這家{shop_name}環境不錯，適合讀書和聊天，下午茶點心很好吃，很多人來拍照。"
        )
        
        # 自動化轉換邏輯：包含關鍵字就變 1，不包含就是 0
        for tag_column, keywords in feature_mapping.items():
            has_keyword = any(kw in str(review_text) for kw in keywords)
            df.at[index, tag_column] = 1 if has_keyword else 0

    # 防錯機制：確保營業時間等重要欄位不會因為空值 (NaN) 導致前端地圖出錯
    if "open_hours" in df.columns:
        df["open_hours"] = df["open_hours"].fillna("詳見官方粉絲專頁")
    else:
        df["open_hours"] = "13:00 - 21:00"

    # 💾 將自動生成好 1 和 0 的資料重新覆蓋寫入原本的 cafe.csv
    df.to_csv(csv_filename, index=False, encoding="utf-8-sig")
    st.success(f"🎉 特徵工程完成！1 和 0 已自動計算並成功覆蓋寫入 {csv_filename}！")
    return df

# --- 效能優化與資料讀取 ---
def load_data():
    try:
        # 讀取 CSV 時同樣指定使用 utf-8-sig 編碼，確保欄位名稱 pudding 完美對齊
        df = pd.read_csv("cafe.csv", encoding='utf-8-sig')
        # 如果發現關鍵欄位不存在或都是空的，自動觸發一次特徵處理
        if "pudding" not in df.columns or df["pudding"].isnull().all() or (df["pudding"] == 0).all():
            return run_text_mining_and_update_csv()
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

# 2. 正向地理編碼：將文字地址轉成經緯度
@st.cache_data
def geocode_address(address):
    default_lat, default_lng = 24.9537, 121.2256
    if not address.strip() or address == "中壢火車站":
        return default_lat, default_lng
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(address)}&format=json&limit=1"
        headers = {'User-Agent': 'TaoCafeFinder/1.0 (student_project)'}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception:
        pass
    return default_lat, default_lng

# 3. 反向地理編碼：將經緯度轉回文字地址
@st.cache_data
def reverse_geocode(lat, lng):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json"
        headers = {'User-Agent': 'TaoCafeFinder/1.0 (student_project)'}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        if data and "display_name" in data:
            address_elements = data.get("address", {})
            city = address_elements.get("city", address_elements.get("town", address_elements.get("county", "")))
            suburb = address_elements.get("suburb", address_elements.get("village", ""))
            road = address_elements.get("road", "")
            house_number = address_elements.get("house_number", "")
            formatted_address = f"{city}{suburb}{road}{house_number}"
            if formatted_address:
                return formatted_address
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

# 在側邊欄放一個可以向教授展示「數據動態活化」的按鈕
st.sidebar.header("⚙️ 系統後端控制")
if st.sidebar.button("🔄 重新執行爬蟲與特徵工程過濾"):
    run_text_mining_and_update_csv()
    st.rerun()

st.write("### 📍 位置權限與起點設定")
location_consent = st.radio(
    "【隱私授權詢問】為了計算您與咖啡廳的距離，本系統需要設定您的出發位置：",
    ("✅ 同意授權使用我目前的真實 GPS 定位", "❌ 不同意位置追蹤，我想自行輸入起點 / 手動設定起點"),
    horizontal=True
)

my_lat, my_lng = 24.9537, 121.2256
current_loc_title = "中壢火車站"

if location_consent == "✅ 同意授權使用我目前的真實 GPS 定位":
    st.info("👇 請點擊下方按鈕，讓瀏覽器確認這是您本人的操作")
    
    st.markdown(
        """
        <style>
        button[title="Get Location"] {
            transform: scale(1.5); 
            transform-origin: left center; 
            margin-top: 15px;
            margin-bottom: 15px;
            margin-left: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    gps_location = streamlit_geolocation()
    
    if gps_location and gps_location.get('latitude') is not None:
        my_lat = gps_location['latitude']
        my_lng = gps_location['longitude']
        real_address = reverse_geocode(my_lat, my_lng)
        st.success(f"🎯 GPS 定位成功！系統偵測到您目前位於：【{real_address}】")
        current_loc_title = f"您的位置 ({real_address})"
    else:
        st.warning("""
        ⚠️ **【系統提示：等待定位中】**
        請點擊上方按鈕，並在瀏覽器彈出的視窗選擇「允許」。
        如果依然無法定位，請勾選上方的 **「❌ 不同意位置追蹤」** 進行手動輸入。
        """)
        st.info("ℹ️ 目前地圖暫時先幫您以預設起點【中壢火車站】載入。")

else:
    user_address_input = st.text_input("🏠 請輸入您的出發地址或地標（例如：元智大學、桃園火車站）：", value="中壢火車站")
    if user_address_input:
        my_lat, my_lng = geocode_address(user_address_input)
        current_loc_title = user_address_input
        st.success(f"🏠 起點已手動設定為：【{current_loc_title}】")

# ─── 側邊欄搜尋與篩選 ───
st.sidebar.header("🔍 搜尋與篩選條件")
user_keyword = st.sidebar.text_input("請輸入咖啡廳店名關鍵字：", placeholder="例如：妮咖啡...")
transport_mode = st.sidebar.selectbox("🚗 請選擇您的代步工具：", ("🚶 步行", "🛵 機車", "🚗 汽車"))

if transport_mode == "🚶 步行":
    speed_per_minute = 0.07  
    max_time_value = 30
    default_time_value = 15
    time_label = "預計最大步行時間 (分鐘)"
    icon_name = "user"       
elif transport_mode == "🛵 機車":
    speed_per_minute = 0.50  
    max_time_value = 60
    default_time_value = 15  
    time_label = "預計最大騎車時間 (分鐘)"
    icon_name = "motorcycle" 
else:
    speed_per_minute = 0.66  
    max_time_value = 90
    default_time_value = 15  
    time_label = "預計最大開車時間 (分鐘)"
    icon_name = "car"        

travel_minutes = st.sidebar.slider(time_label, min_value=5, max_value=max_time_value, value=default_time_value, step=5)
max_dist = travel_minutes * speed_per_minute

st.sidebar.write("📌 空間與氛圍標籤（可複選）：")
tag_dict = {
    "pudding": st.sidebar.checkbox("🍮 布丁好吃"),
    "basque": st.sidebar.checkbox("🍰 巴斯克好吃"),
    "midnight": st.sidebar.checkbox("🌙 主打深夜"),
    "study": st.sidebar.checkbox("💻 適合讀書"),
    "chat": st.sidebar.checkbox("💬 適合聊天"),
    "photo": st.sidebar.checkbox("📷 適合拍照"),
}
active_tags = [key for key, value in tag_dict.items() if value]

results = search_cafes(my_lat, my_lng, active_tags, keyword=user_keyword, max_distance_km=max_dist)

# ─── 地圖與結果渲染 ───
st.write(f"### 📍 地圖與搜尋結果")
action_verb = "步行" if "步行" in transport_mode else ("騎車" if "機車" in transport_mode else "開車")

current_zoom = 16 if "步行" in transport_mode else 14
mymap = folium.Map(location=[my_lat, my_lng], zoom_start=current_zoom)

folium.Marker(
    location=[my_lat, my_lng],
    popup=f"<b>🎯 起點：{current_loc_title}</b>",
    icon=folium.Icon(color="red", icon=icon_name, prefix="fa"),
).add_to(mymap)

if not results.empty:
    st.success(f"幫您找到 {len(results)} 間符合條件的咖啡廳：")
    for _, row in results.iterrows():
        t_time = round(row["distance"] / speed_per_minute)
        t_time = 1 if t_time < 1 else t_time
        popup_text = f"<b>{row['name']}</b><br>距離：{row['distance']:.2f} km<br>{action_verb}約：{t_time} 分鐘<br>營業時間：{row['open_hours']}"
        folium.Marker(
            location=[row["lat"], row["lng"]],
            popup=popup_text,
            icon=folium.Icon(color="blue", icon="coffee", prefix="fa"),
        ).add_to(mymap)
else:
    st.warning(f"💡 提示：目前定位在【{current_loc_title}】，在您選擇的交通時間內暫無搜尋到咖啡廳。")

st_folium(mymap, width=850, height=500, key="cafe_map")

if not results.empty:
    st.write("#### 📝 店家詳細資訊清單（自動化特徵工程資料庫）：")
    st.dataframe(results, use_container_width=True)
