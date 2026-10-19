import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 1. ページ基本設定（タイトル＆ファビコン）
st.set_page_config(
    page_title="【当日用】思考・表現力セッション",
    page_icon="🔴",
    layout="wide"
)

# 🎨 当日用専用のカスタムCSS（エンジ・赤系テーマ＆ヘッダーの強調）
st.markdown("""
<style>
    /* メインヘッダー・アクセント設定 */
    .day-banner {
        background-color: #8B0000;
        color: #FFFFFF;
        padding: 12px 20px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 1.1rem;
        margin-bottom: 25px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.15);
    }
    
    /* 当日用メインタイトルのデザイン */
    .day-title {
        color: #8B0000;
        border-bottom: 3px solid #8B0000;
        padding-bottom: 10px;
        margin-bottom: 20px;
        font-weight: bold;
    }

    /* 強調ボタン等のカスタマイズ（赤系） */
    div.stButton > button:first-child {
        background-color: #A52A2A;
        color: white;
        border-radius: 6px;
        border: none;
        font-weight: bold;
    }
    div.stButton > button:first-child:hover {
        background-color: #8B0000;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# 🔴 一目で分かる「当日用」バナーの常時表示
st.markdown('<div class="day-banner">🔴 【当日用・面接評価モード】 思考・表現力セッション</div>', unsafe_allow_html=True)

# Supabaseの初期化
@st.cache_resource
def init_supabase():
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"Supabase接続エラー: {e}")

# Gemini APIの初期化
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# メインタイトル
st.markdown('<h1 class="day-title">【当日用】面接・思考性評価システム</h1>', unsafe_allow_html=True)
st.write("※こちらは当日実施用の評価・入力画面です。事前に提出されたデータを確認の上、面接評価・AI分析を行ってください。")

# 応募者データの取得・表示ロジック（※テーブル名を 'candidate_responses' に修正済み）
try:
    response = supabase.table("candidate_responses").select("*").execute()
    data = response.data
    
    if data:
        names = [item.get("name", "無名") for item in data]
        selected_name = st.selectbox("応募者を選択してください", names)
        
        # 選択された応募者のデータを抽出
        selected_candidate = next((item for item in data if item.get("name") == selected_name), None)
        
        if selected_candidate:
            st.markdown(f"### 【応募者氏名】 {selected_candidate.get('name')}")
            st.markdown("### 【事前記述内容】")
            st.info(selected_candidate.get("text", "記述内容がありません。"))
            
            # スコアの取得（存在しない場合はデフォルト値）
            scores = selected_candidate.get("scores", {"Te": 35, "Ti": 35, "Fe": 35, "Fi": 35, "Se": 35, "Ni": 35})
            if not isinstance(scores, dict):
                scores = {"Te": 35, "Ti": 35, "Fe": 35, "Fi": 35, "Se": 35, "Ni": 35}
            
            st.markdown("### 【認知特性・思考傾向分析】")
            cols = st.columns(6)
            metrics = [("Te (効率)", scores.get("Te", 35)), 
                       ("Ti (論理)", scores.get("Ti", 35)), 
                       ("Fe (調和)", scores.get("Fe", 35)), 
                       ("Fi (内省)", scores.get("Fi", 35)), 
                       ("Se (実行)", scores.get("Se", 35)), 
                       ("Ni (直観)", scores.get("Ni", 35))]
            
            for i, (label, val) in enumerate(metrics):
                cols[i].metric(label, f"{val}点")
                
            # レーダーチャートの描画
            st.markdown(f"#### {selected_name} 様 事前思考特性レーダーチャート")
            labels = ['Te (効率)', 'Ti (論理)', 'Fe (調和)', 'Fi (内省)', 'Se (実行)', 'Ni (直観)']
            values = [scores.get("Te", 35), scores.get("Ti", 35), scores.get("Fe", 35), 
                      scores.get("Fi", 35), scores.get("Se", 35), scores.get("Ni", 35)]
            
            fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
            angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
            values += values[:1]
            angles += angles[:1]
            
            ax.plot(angles, values, linewidth=2, linestyle='solid', color='#8B0000')
            ax.fill(angles, values, color='#A52A2A', alpha=0.4)
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(labels, fontsize=10)
            ax.set_yticks([20, 40, 60, 80, 100])
            ax.grid(True)
            
            st.pyplot(fig)
            
            # AI分析セクション
            st.markdown("### 採用・面接評価メモ（思考の癖、リスク、面接時確認事項など）")
            ai_memo = st.text_area("AI分析結果・面接メモ", value=selected_candidate.get("ai_memo", ""), height=150)
            
            if st.button("🔴 【当日用】AI分析を実行する"):
                if "GEMINI_API_KEY" in st.secrets:
                    try:
                        model = genai.GenerativeModel("gemini-1.5-flash")
                        prompt = f"応募者名: {selected_name}\n記述内容: {selected_candidate.get('text')}\nスコア: {scores}\nこの応募者の思考特性や面接時に確認すべきリスクについて簡潔に分析してください。"
                        res = model.generate_content(prompt)
                        st.success("AI分析が完了しました！")
                        st.write(res.text)
                    except Exception as e:
                        st.error(f"AI分析中にエラーが発生しました: {e}")
                else:
                    st.warning("※GEMINI_API_KEYが設定されていないため分析できません。")
                    
    else:
        st.info("登録されている応募者データがありません。")
except Exception as e:
    st.error(f"データの取得に失敗しました: {e}")
