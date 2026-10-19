import streamlit as st
from supabase import create_client
import google.generativeai as genai
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json

# 1. ページ基本設定
st.set_page_config(
    page_title="【当日用】面接・思考性評価システム",
    page_icon="🔴",
    layout="wide"
)

# カスタムCSS（デザイン調整）
st.markdown("""
<style>
    .day-banner {
        background-color: #8B0000;
        color: #FFFFFF;
        padding: 10px 18px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 1.1rem;
        margin-bottom: 15px;
    }
    .day-title {
        color: #8B0000;
        border-bottom: 3px solid #8B0000;
        padding-bottom: 6px;
        margin-bottom: 15px;
        font-size: 1.6rem;
        font-weight: bold;
    }
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

# ヘッダーバナー
st.markdown('<div class="day-banner">🔴 【当日用・面接評価モード】 思考・表現力セッション</div>', unsafe_allow_html=True)

# Supabase初期化
@st.cache_resource
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"Supabase接続エラー: {e}")

# Gemini API初期化
if "GEMINI_API_KEY" in st.secrets:
    try:
        raw_key = str(st.secrets["GEMINI_API_KEY"]).strip().strip('"').strip("'")
        genai.configure(api_key=raw_key)
    except Exception:
        pass

# モード切替（サイドバー）
st.sidebar.title("📌 モード切替")
mode = st.sidebar.radio("表示モードを選択", ["面接官用（評価・入力画面）", "応募者用（確認専用画面）"])

st.markdown('<h1 class="day-title">【当日用】面接・思考性評価システム</h1>', unsafe_allow_html=True)

# データ取得
try:
    response = supabase.table("candidate_responses").select("*").execute()
    data = response.data
    
    if data:
        names = [item.get("name", "無名") for item in data]
        selected_name = st.selectbox("対象の応募者を選択してください", names)
        selected_candidate = next((item for item in data if item.get("name") == selected_name), None)
        
        if selected_candidate:
            record_id = selected_candidate.get("id")
            
            # --- スコアデータの解析・抽出 ---
            scores_dict = {"Te": 50, "Ti": 50, "Fe": 50, "Fi": 50, "Se": 50, "Ni": 50}
            raw_scores = selected_candidate.get("scores")
            
            if isinstance(raw_scores, dict):
                scores_dict.update(raw_scores)
            elif isinstance(raw_scores, str):
                try:
                    parsed = json.loads(raw_scores)
                    if isinstance(parsed, dict):
                        scores_dict.update(parsed)
                except Exception:
                    pass

            # --- メインレイアウト（2カラム） ---
            col_left, col_right = st.columns([1, 1])
            
            with col_left:
                st.markdown(f"### 👤 応募者氏名: **{selected_candidate.get('name')}**")
                st.markdown("#### 【事前記述内容】")
                st.info(selected_candidate.get("text", "記述内容がありません。"))
                
                types_info = selected_candidate.get("types", "情報なし")
                st.markdown(f"**判定タイプ / 補助特性:** `{types_info}`")
                
                st.markdown("#### 【各認知特性スコア】")
                c1, c2, c3 = st.columns(3)
                c1.metric("Te (効率)", f"{scores_dict.get('Te', 50)}点")
                c2.metric("Ti (論理)", f"{scores_dict.get('Ti', 50)}点")
                c3.metric("Fe (調和)", f"{scores_dict.get('Fe', 50)}点")
                c1.metric("Fi (内省)", f"{scores_dict.get('Fi', 50)}点")
                c2.metric("Se (実行)", f"{scores_dict.get('Se', 50)}点")
                c3.metric("Ni (直観)", f"{scores_dict.get('Ni', 50)}点")

            with col_right:
                st.markdown("#### 【思考特性レーダーチャート】")
                
                # Plotlyによる高精度レーダーチャート（文字化けが一切発生しません）
                categories = ['Te (効率)', 'Ti (論理)', 'Fe (調和)', 'Fi (内省)', 'Se (実行)', 'Ni (直観)']
                values = [
                    scores_dict.get('Te', 50),
                    scores_dict.get('Ti', 50),
                    scores_dict.get('Fe', 50),
                    scores_dict.get('Fi', 50),
                    scores_dict.get('Se', 50),
                    scores_dict.get('Ni', 50)
                ]
                
                fig = go.Figure(data=go.Scatterpolar(
                    r=values + [values[0]],
                    theta=categories + [categories[0]],
                    fill='toself',
                    fillcolor='rgba(139, 0, 0, 0.4)',
                    line=dict(color='#8B0000', width=2)
                ))
                
                fig.update_layout(
                    polar=dict(
                        radialaxis=dict(visible=True, range=[0, 100])
                    ),
                    showlegend=False,
                    margin=dict(l=40, r=40, t=30, b=30),
                    height=380
                )
                
                st.plotly_chart(fig, use_container_width=True)

            # --- モード別の表示制御 ---
            if mode == "面接官用（評価・入力画面）":
                st.markdown("---")
                st.markdown("### 📝 面接評価・AI分析メモ")
                
                current_memo = selected_candidate.get("ai_memo", "") or ""
                memo_input = st.text_area("面接中の所感・メモ・質問事項", value=current_memo, height=130)
                
                btn_col1, btn_col2, btn_col3 = st.columns(3)
                
                with btn_col1:
                    if st.button("🔴 AI分析を実行する"):
                        if "GEMINI_API_KEY" in st.secrets:
                            try:
                                raw_key = str(st.secrets["GEMINI_API_KEY"]).strip().strip('"').strip("'")
                                genai.configure(api_key=raw_key)
                                model = genai.GenerativeModel("gemini-1.5-flash")
                                prompt = f"応募者名: {selected_name}\n記述内容: {selected_candidate.get('text')}\nこの応募者の思考特性や面接時に確認すべきポイントについて簡潔に分析してください。"
                                res = model.generate_content(prompt)
                                st.success("AI分析が完了しました")
                                st.write(res.text)
                            except Exception as e:
                                st.error(f"AI分析エラー: {e}")
                        else:
                            st.warning("※GEMINI_API_KEYが設定されていません。")

                with btn_col2:
                    if st.button("💾 メモを保存する"):
                        try:
                            supabase.table("candidate_responses").update({"ai_memo": memo_input}).eq("id", record_id).execute()
                            st.success("メモをデータベースに保存しました。")
                        except Exception as e:
                            st.error(f"保存エラー: {e}")

                with btn_col3:
                    if st.button("🗑️ データを削除する"):
                        try:
                            supabase.table("candidate_responses").delete().eq("id", record_id).execute()
                            st.success("データを削除しました。")
                            st.rerun()
                        except Exception as e:
                            st.error(f"削除エラー: {e}")
            else:
                # 応募者用（確認専用画面）の場合
                st.markdown("---")
                st.info("💡 こちらは応募者確認用画面です。入力フォームや操作ボタンは非表示になっています。")

    else:
        st.info("登録されている応募者データがありません。")
except Exception as e:
    st.error(f"データ取得エラー: {e}")
