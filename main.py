import streamlit as st
import requests
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import google.generativeai as genai
from datetime import datetime

# --- A. 核心配置 ---
st.set_page_config(page_title="川普即時翻譯監控", page_icon="🇺🇸", layout="wide")

# CSS 美化：調整字體與卡片樣式
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .post-card { background-color: white; padding: 20px; border-radius: 12px; border-left: 5px solid #E01E35; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .time-label { color: #666; font-size: 0.85rem; }
    .trans-text { color: #1a73e8; font-weight: 500; margin-top: 10px; }
    </style>
    """, unsafe_allow_stdio=True)

# 讀取 Secrets
try:
    APIFY_TOKEN = st.secrets["APIFY_TOKEN"]
    DISCORD_WEBHOOK = st.secrets["DISCORD_WEBHOOK"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"❌ 缺少必要設定: {e}")
    st.stop()

# 自動刷新 (10分鐘)
st_autorefresh(interval=600000, key="auto_refresh")

# --- B. 翻譯函數 (快取處理，節省 Token) ---
@st.cache_data(show_spinner=False)
def translate_text(text):
    if not text: return ""
    prompt = f"請將這段川普在 Truth Social 的發文翻譯成流暢的繁體中文，保持原有的語氣與重點：\n\n{text}"
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return "⚠️ 翻譯暫時無法使用"

# --- C. 資料抓取 ---
def fetch_data():
    url = f"https://api.apify.com/v2/acts/muhammetakkurtt~truth-social-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    payload = {"username": "realDonaldTrump", "maxPosts": 8}
    try:
        res = requests.post(url, json=payload, timeout=60)
        return res.json() if res.status_code in [200, 201] else []
    except:
        return []

# --- D. 主頁面介面 ---
col1, col2 = st.columns([2, 1])
with col1:
    st.title("🇺🇸 川普發言即時翻譯儀表板")
with col2:
    st.write(f"最後更新：{datetime.now().strftime('%H:%M:%S')}")
    if st.button("🔄 立即強制刷新"):
        st.cache_data.clear()
        st.rerun()

posts = fetch_data()

if posts:
    # 統一欄位名稱
    df = pd.DataFrame(posts)
    t_key = next((k for k in ['createdAt', 'created_at', 'time'] if k in df.columns), 'time')
    c_key = next((k for k in ['text', 'content', 'caption'] if k in df.columns), 'text')
    i_key = next((k for k in ['id', 'post_id'] if k in df.columns), 'id')

    # 第一則：最新動態亮點
    latest = posts[0]
    with st.container():
        st.markdown("### 🚨 最新動態")
        trans = translate_text(latest.get(c_key, ""))
        
        st.markdown(f"""
            <div class="post-card">
                <div class="time-label">發布時間：{latest.get(t_key)}</div>
                <p style='font-size: 1.1rem; margin-top:10px;'>{latest.get(c_key)}</p>
                <div class="trans-text">💡 中文翻譯：<br>{trans}</div>
            </div>
        """, unsafe_allow_stdio=True)

    # 推播邏輯 (僅針對最新的一則)
    if "last_id" not in st.session_state:
        st.session_state.last_id = latest.get(i_key)

    if latest.get(i_key) != st.session_state.last_id:
        discord_msg = {
            "embeds": [{
                "title": "🇺🇸 川普新發文 (中文翻譯)",
                "description": f"**原文：**\n{latest.get(c_key)}\n\n**翻譯：**\n{trans}",
                "color": 15548997,
                "url": f"https://truthsocial.com/@realDonaldTrump"
            }]
        }
        requests.post(DISCORD_WEBHOOK, json=discord_msg)
        st.session_state.last_id = latest.get(i_key)
        st.toast("新貼文已推送至 Discord！")

    st.divider()

    # 歷史列表
    st.subheader("📜 歷史發文回顧")
    for p in posts[1:]:
        with st.expander(f"🕒 {p.get(t_key)}"):
            st.write("**原文：**")
            st.write(p.get(c_key))
            st.write("**中文翻譯：**")
            st.info(translate_text(p.get(c_key)))

else:
    st.warning("暫時抓不到資料，請檢查 API 設定。")
