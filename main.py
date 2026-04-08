import streamlit as st
import requests
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# --- A. 基礎配置 ---
st.set_page_config(page_title="Trump Monitor 2026", page_icon="🦅", layout="wide")

# 設定 Secrets (請在 Streamlit Cloud 後台 Settings > Secrets 填入)
# APIFY_TOKEN = "..."
# DISCORD_WEBHOOK = "..."

try:
    APIFY_TOKEN = st.secrets["APIFY_TOKEN"]
    DISCORD_WEBHOOK = st.secrets["DISCORD_WEBHOOK"]
except Exception:
    st.error("❌ 找不到 Secrets 設定，請在 Streamlit 後台填入 APIFY_TOKEN 與 DISCORD_WEBHOOK")
    st.stop()

# 自動重新整理：每 10 分鐘 (600,000 毫秒) 執行一次
count = st_autorefresh(interval=600000, key="fizzbuzzcounter")

st.title("🦅 川普 Truth Social 即時監控儀表板")
st.caption(f"最後檢查時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (每 10 分鐘自動更新)")

# --- B. 抓取資料函數 ---
def fetch_data():
    # 使用 2026 推薦的 Apify Actor (muhammetakkurtt/truth-social-scraper)
    url = f"https://api.apify.com/v2/acts/muhammetakkurtt~truth-social-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    payload = {
        "username": "realDonaldTrump",
        "maxPosts": 10,
        "includeReplies": False
    }
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API 請求失敗，狀態碼: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"連線發生錯誤: {e}")
        return []

# --- C. 核心處理邏輯 ---
posts_data = fetch_data()

if not posts_data:
    st.info("⌛ 目前沒有新資料或正在等待 API 回應...")
else:
    # 將資料轉為 DataFrame
    df_raw = pd.DataFrame(posts_data)
    
    # 【修復 KeyError】: 自動尋找可能的欄位名稱
    # 2026 年常見的欄位變體
    time_keys = ['createdAt', 'created_at', 'timestamp', 'time']
    text_keys = ['content', 'text', 'caption', 'body']
    id_keys = ['id', 'post_id', 'id_str']

    # 找出當前 JSON 中存在的 key
    col_time = next((k for k in time_keys if k in df_raw.columns), None)
    col_text = next((k for k in text_keys if k in df_raw.columns), None)
    col_id = next((k for k in id_keys if k in df_raw.columns), None)

    if col_time and col_text:
        # 整理後的乾淨資料
        clean_df = df_raw[[col_time, col_text]].copy()
        
        # --- D. 檢查更新並推播 ---
        latest_post_id = str(df_raw.iloc[0][col_id]) if col_id else ""
        
        # 使用 st.cache_resource 儲存上一次推播過的 ID
        if "last_notified_id" not in st.session_state:
            st.session_state.last_notified_id = latest_post_id
        
        # 如果最新 ID 與紀錄的不符，發送 Discord
        if latest_post_id and latest_post_id != st.session_state.last_notified_id:
            content = df_raw.iloc[0][col_text]
            post_url = f"https://truthsocial.com/@realDonaldTrump/posts/{latest_post_id}"
            
            discord_data = {
                "embeds": [{
                    "title": "🚨 川普新發文通知",
                    "description": content[:1000], # Discord 限制描述長度
                    "url": post_url,
                    "color": 15548997, # 烈焰紅
                    "timestamp": datetime.utcnow().isoformat()
                }]
            }
            requests.post(DISCORD_WEBHOOK, json=discord_data)
            st.session_state.last_notified_id = latest_post_id
            st.toast("✅ 新貼文已推播至 Discord!")

        # --- E. 網頁介面顯示 ---
        st.subheader("📋 最近貼文列表")
        st.dataframe(clean_df, use_container_width=True)
        
        for index, row in clean_df.iterrows():
            with st.expander(f"💬 貼文時間: {row[col_time]}"):
                st.write(row[col_text])
    else:
        st.error("❌ 無法解析資料欄位。請檢查 API 回傳內容。")
        st.write("目前 API 回傳的欄位有：", df_raw.columns.tolist())
