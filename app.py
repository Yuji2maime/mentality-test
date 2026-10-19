import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 1. ページ基本設定
st.set_page_config(
    page_title="【当日用】面接・思考性評価システム",
    page_icon="🔴",
    layout="wide"
)

# 2. デザイン・CSS設定（赤系テーマ）
st.markdown("""
<style>
    .day-banner {
        background-color: #8B0000;
        color: #FFFFFF;
        padding: 12px 20px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 1.1rem;
        margin-bottom: 20px;
    }
    .day-title {
        color: #8B0000;
        border-bottom: 3px solid #8B0000;
        padding-bottom: 8px;
        margin-bottom: 15px;
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

# 常時表示バナー
st.markdown('<div class="day-banner">🔴 【当日用・面接評価モード】 思考・表現力セッション</div>', unsafe_allow_html=True)

# Supabaseの初期化
@st.cache_resource
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"Supabase接続エラー: {e}")

# Gemini APIの初期化（エラーハンドリング付き）
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"].strip())
    except Exception:
        pass

st.markdown('<h1 class="day-title">【当日用】面接・思考性評価システム</h1>', unsafe_allow_html=True)
st.write("※こちらは当日実施用の評価・入力画面です。事前に提出されたデータを確認し、面接メモやAI分析を行えます。")

# データ取得・表示ロジック
try:
    response = supabase.table("candidate_responses").select("*").execute()
    data = response.data
    
    if data:
        # サイドバーまたはセレクトボックスで応募者選択
        names = [item.get("name", "無名") for item in data]
        selected_name = st.selectbox("📌 評価する応募者を選択してください", names)
        
        selected_candidate = next((item for item in data if item.get("name") == selected_name), None)
        
        if selected_candidate:
            record_id = selected_candidate.get("id")
            
            # 2カラムレイアウトで整理
            col_left, col_right = st.columns([1, 1])
            
            with col_left:
                st.markdown(f"### 👤 応募者氏名: {selected_candidate.get('name')}")
                st.markdown("#### 【事前記述内容】")
                st.info(selected_candidate.get("text", "記述内容がありません。"))
                
                # 判定されたタイプ等
                types_info = selected_candidate.get("types", "情報なし")
                st.markdown(f"**判定タイプ / 補助特性:** `{types_info}`")

            with col_right:
                st.markdown("#### 【思考特性レーダーチャート】")
                # 文字化け防止のため英語ラベルを使用しつつコンパクトに描画
                labels = ['Te (Efficiency)', 'Ti (Logic)', 'Fe (Harmony)', 'Fi (Reflection)', 'Se (Execution)', 'Ni (Intuition)']
                
                # デフォルトスコア（データがない場合のフォールバック）
                scores = [50, 50, 50, 50, 50, 50]
                
                angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
                scores += scores[:1]
                angles += angles[:1]
                
                fig, ax = plt.subplots(figsize=(3.5, 3.5), subplot_kw=dict(polar=True))
                ax.plot(angles, scores, linewidth=2, linestyle='solid', color='#8B0000')
                ax.fill(angles, scores, color='#A52A2A', alpha=0.3)
                ax.set_xticks(angles[:-1])
                ax.set_xticklabels(labels, fontsize=8)
                ax.set_yticks([20, 40, 60, 80, 100])
                ax.grid(True)
                
                st.pyplot(fig)

            st.markdown("---")
            st.markdown("### 📝 面接評価・AI分析メモ")
            
            # 既存のメモ（もしデータベースにあれば読み込む。なければ空欄）
            current_memo = selected_candidate.get("ai_memo", "")
            memo_input = st.text_area("面接中のメモ・AI分析結果", value=current_memo, height=120)
            
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            
            with col_btn1:
                if st.button("🔴 AI分析を実行する"):
                    if "GEMINI_API_KEY" in st.secrets:
                        try:
                            model = genai.GenerativeModel("gemini-1.5-flash")
                            prompt = f"応募者名: {selected_name}\n記述内容: {selected_candidate.get('text')}\nこの応募者の思考特性や面接時に確認すべきポイントについて簡潔に分析してください。"
                            res = model.generate_content(prompt)
                            st.success("AI分析が完了しました！")
                            st.write(res.text)
                        except Exception as e:
                            st.error(f"AIエラー: APIキーまたは通信に問題があります（{e}）。SecretsのGEMINI_API_KEYをご確認ください。")
                    else:
                        st.warning("※GEMINI_API_KEYが設定されていません。")
            
            with col_btn2:
                if st.button("💾 メモを保存する"):
                    try:
                        supabase.table("candidate_responses").update({"ai_memo": memo_input}).eq("id", record_id).execute()
                        st.success("メモを保存しました！")
                    except Exception as e:
                        st.error(f"保存に失敗しました（テーブルに 'ai_memo' 列がない可能性があります）: {e}")

            with col_btn3:
                if st.button("🗑️ データを削除する"):
                    try:
                        supabase.table("candidate_responses").delete().eq("id", record_id).execute()
                        st.success("データを削除しました。ページを更新してください。")
                        st.rerun()
                    except Exception as e:
                        st.error(f"削除に失敗しました: {e}")
                        
    else:
        st.info("登録されている応募者データがありません。")
except Exception as e:
    st.error(f"データの取得に失敗しました: {e}")
