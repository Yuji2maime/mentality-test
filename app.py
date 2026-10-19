import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re

# 1. ページ基本設定
st.set_page_config(
    page_title="【当日用】面接・思考性評価システム",
    page_icon="🔴",
    layout="wide"
)

# 日本語フォント設定（文字化け対策）
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'TakaoPGothic', 'IPAexGothic']

# 2. デザイン・CSS設定（赤系テーマ＆コンパクトレイアウト）
st.markdown("""
<style>
    .day-banner {
        background-color: #8B0000;
        color: #FFFFFF;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 1.0rem;
        margin-bottom: 15px;
    }
    .day-title {
        color: #8B0000;
        border-bottom: 2px solid #8B0000;
        padding-bottom: 5px;
        margin-bottom: 15px;
        font-size: 1.5rem;
        font-weight: bold;
    }
    .stTextArea textarea {
        height: 90px !important;
    }
    div.stButton > button:first-child {
        background-color: #A52A2A;
        color: white;
        border-radius: 5px;
        border: none;
        font-weight: bold;
        padding: 6px 12px;
    }
    div.stButton > button:first-child:hover {
        background-color: #8B0000;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# バナー表示
st.markdown('<div class="day-banner">🔴 【当日用・面接評価モード】 思考・表現力セッション</div>', unsafe_allow_html=True)

# Supabaseの初期化
@st.cache_resource
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"Supabase接続エラー: {e}")

# Gemini APIの初期化
if "GEMINI_API_KEY" in st.secrets:
    try:
        raw_key = str(st.secrets["GEMINI_API_KEY"]).strip().strip('"').strip("'")
        genai.configure(api_key=raw_key)
    except Exception:
        pass

# モード切替（サイドバー）
st.sidebar.title("📌 モード切替")
mode = st.sidebar.radio("画面表示モード", ["面接官用（評価画面）", "応募者用（確認画面）"])

st.markdown('<h1 class="day-title">【当日用】面接・思考性評価システム</h1>', unsafe_allow_html=True)

# データ取得
try:
    response = supabase.table("candidate_responses").select("*").execute()
    data = response.data
    
    if data:
        names = [item.get("name", "無名") for item in data]
        selected_name = st.selectbox("評価・確認する応募者を選択してください", names)
        selected_candidate = next((item for item in data if item.get("name") == selected_name), None)
        
        if selected_candidate:
            record_id = selected_candidate.get("id")
            
            # スコア解析ロジック
            scores_dict = {"Te": 50, "Ti": 50, "Fe": 50, "Fi": 50, "Se": 50, "Ni": 50}
            raw_scores = selected_candidate.get("scores")
            if isinstance(raw_scores, dict):
                scores_dict.update(raw_scores)
            
            # メイン表示エリア
            col_left, col_right = st.columns([1.2, 1])
            
            with col_left:
                st.markdown(f"### 👤 応募者氏名: **{selected_candidate.get('name')}**")
                st.markdown("#### 【事前記述内容】")
                st.info(selected_candidate.get("text", "記述内容がありません。"))
                
                types_info = selected_candidate.get("types", "情報なし")
                st.markdown(f"**判定タイプ / 補助特性:** `{types_info}`")
                
                # 6指標の点数表示
                st.markdown("#### 【各認知特性スコア】")
                m_cols = st.columns(3)
                m_cols[0].metric("Te (効率)", f"{scores_dict['Te']}点")
                m_cols[1].metric("Ti (論理)", f"{scores_dict['Ti']}点")
                m_cols[2].metric("Fe (調和)", f"{scores_dict['Fe']}点")
                m_cols[0].metric("Fi (内省)", f"{scores_dict['Fi']}点")
                m_cols[1].metric("Se (実行)", f"{scores_dict['Se']}点")
                m_cols[2].metric("Ni (直観)", f"{scores_dict['Ni']}点")

            with col_right:
                st.markdown("#### 【思考特性レーダーチャート】")
                labels = ['Te\n(効率)', 'Ti\n(論理)', 'Fe\n(調和)', 'Fi\n(内省)', 'Se\n(実行)', 'Ni\n(直観)']
                values = [scores_dict['Te'], scores_dict['Ti'], scores_dict['Fe'], 
                          scores_dict['Fi'], scores_dict['Se'], scores_dict['Ni']]
                
                angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
                values_plot = values + values[:1]
                angles_plot = angles + angles[:1]
                
                fig, ax = plt.subplots(figsize=(4, 4), subplot_kw=dict(polar=True))
                ax.plot(angles_plot, values_plot, linewidth=2, linestyle='solid', color='#8B0000')
                ax.fill(angles_plot, values_plot, color='#A52A2A', alpha=0.35)
                ax.set_xticks(angles)
                ax.set_xticklabels(labels, fontsize=9, fontweight='bold')
                ax.set_yticks([20, 40, 60, 80, 100])
                ax.set_ylim(0, 100)
                ax.grid(True, linestyle='--', alpha=0.6)
                
                st.pyplot(fig)

            # 面接官用モード時のメモ＆管理操作
            if mode == "面接官用（評価画面）":
                st.markdown("---")
                st.markdown("### 📝 面接評価・AI分析メモ")
                
                current_memo = selected_candidate.get("ai_memo", "") or ""
                memo_input = st.text_area("評価メモ・確認事項", value=current_memo, placeholder="面接時の所感や確認事項を入力...")
                
                btn_c1, btn_c2, btn_c3 = st.columns(3)
                
                with btn_c1:
                    if st.button("🔴 AI分析を実行"):
                        if "GEMINI_API_KEY" in st.secrets:
                            try:
                                raw_key = str(st.secrets["GEMINI_API_KEY"]).strip().strip('"').strip("'")
                                genai.configure(api_key=raw_key)
                                model = genai.GenerativeModel("gemini-1.5-flash")
                                prompt = f"応募者名: {selected_name}\n記述内容: {selected_candidate.get('text')}\nこの応募者の思考傾向や面接での確認ポイントを簡潔にまとめてください。"
                                res = model.generate_content(prompt)
                                st.success("AI分析が完了しました")
                                st.write(res.text)
                            except Exception as e:
                                st.error(f"AI分析エラー: {e}")
                        else:
                            st.warning("GEMINI_API_KEYが設定されていません。")

                with btn_c2:
                    if st.button("💾 メモを保存"):
                        try:
                            supabase.table("candidate_responses").update({"ai_memo": memo_input}).eq("id", record_id).execute()
                            st.success("メモを保存しました。")
                        except Exception as e:
                            st.error(f"保存エラー: {e}")

                with btn_c3:
                    if st.button("🗑️ データを削除"):
                        try:
                            supabase.table("candidate_responses").delete().eq("id", record_id).execute()
                            st.success("削除完了しました。")
                            st.rerun()
                        except Exception as e:
                            st.error(f"削除エラー: {e}")

    else:
        st.info("登録されている応募者データがありません。")
except Exception as e:
    st.error(f"データ取得エラー: {e}")
