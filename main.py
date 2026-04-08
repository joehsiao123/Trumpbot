import streamlit as st
import requests
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# --- 1. 初始化設定 ---
st.set_page_config(page_title="川普發言追蹤器", page_icon="🦅")
DISCORD_WEBHOOK = st.secrets["DISCORD_WEBHOOK"]
APIFY_TOKEN = st.secrets["APIFY_TOKEN"]

# 每 10 分鐘自動刷新頁面一次 (600,000 毫秒)
st_autorefresh(interval=600000, key="datarefresh")

st.title("🦅 川普 Truth Social 即時監控")

# --- 2. 抓取資料函數 ---
def fetch_trump_posts():
    # 呼叫 Apify API
    url = f"https://api.apify.com/v2/acts/muhammetakkurtt~truth-social-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    payload = {"username": "realDonaldTrump", "maxPosts": 5}
    response = requests.post(url, json=payload)
    return response.json() if response.status_code == 200 else []

# --- 3. 檢查與推播邏輯 ---
posts = fetch_trump_posts()

if posts:
    latest_post = posts[0]
    last_pushed_id = st.cache_resource.get("last_id", "")

    # 比對 ID 是否為新貼文
    if latest_post['id'] != last_pushed_id:
        # 發送 Discord 通知
        embed = {
            "title": "🚨 川普發文了！",
            "description": latest_post['text'],
            "url": f"https://truthsocial.com/@realDonaldTrump/posts/{latest_post['id']}",
            "color": 15158332, # 政治紅
            "footer": {"text": f"發布時間: {latest_post['createdAt']}"}
        }
        requests.post(DISCORD_WEBHOOK, json={"embeds": [embed]})
        
        # 更新快取中的 ID
        st.cache_resource["last_id"] = latest_post['id']
        st.toast("發現新貼文，已推播至 Discord！")

# --- 4. 儀表板界面 ---
st.subheader("📊 最近 5 則貼文摘要")
df = pd.DataFrame(posts)[['createdAt', 'text']]
st.dataframe(df, use_container_width=True)

for p in posts:
    with st.expander(f"🕒 {p['createdAt']}"):
        st.write(p['text'])
