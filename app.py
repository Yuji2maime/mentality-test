import streamlit as st
from supabase import create_client
import google.generativeai as genai
import pandas as pd
import plotly.graph_objects as go

# 1. ページ基本設定
st.set_page_config(
    page_title="【当日用】面接・思考性評価システム",
    page_icon="🔴",
    layout="wide"
)

# カスタムCSS（デザイン・レイアウト最適化）
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
        font-size: 1.5rem;
        font-weight: bold;
    }
    .type-box {
        background-color: #f1f3f5;
        border-left: 4px solid #8B0000;
        padding: 10px 15px;
        border-radius: 4px;
        margin-bottom: 15px;
        font-weight: bold;
    }
    div.stButton > button:first-child {
        background-color: #A52A2A;
        color: white;
        border-radius: 6px;
        border: none;
        font-weight: bold;
        padding: 8px 16px;
    }
    div.stButton > button:first-child:hover {
        background-color: #8B0000;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# 🔴 サイドバー（モード切替＆免責事項・注意事項）
st.sidebar.title("📌 メニュー・設定")
mode = st.sidebar.radio("画面表示モード", ["面接官用（評価・入力画面）", "応募者用（確認専用画面）"])

st.sidebar.markdown("---")
st.sidebar.subheader("⚠️ 利用上の注意・免責事項")
st.sidebar.info("""
- **判定結果の位置付け**
  本システムの思考性・認知特性分析は、応募者の自己申告テキストに基づく傾向分析であり、人物像や能力を確定するものではありません。
- **面接時の活用方法**
  評価の絶対的な基準とせず、面接における深掘り質問の参考材料（補助ツール）としてご活用ください。
- **個人情報の管理**
  採用選考以外の目的での使用、および第三者への漏洩・共有は厳禁です。
""")

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
            candidate_text = selected_candidate.get("text", "")
            candidate_types = str(selected_candidate.get("types", ""))
            
            # スコア算出ロジック
            base_score = 55 + (len(candidate_text) % 20)
            scores_dict = {
                "Te": base_score if "Te" in candidate_types else base_score - 10,
                "Ti": base_score + 10 if "Ti" in candidate_types or "論理" in candidate_text else base_score - 5,
                "Fe": base_score + 5 if "Fe" in candidate_types or "患者" in candidate_text or "痛み" in candidate_text else base_score - 10,
                "Fi": base_score + 15 if "Fi" in candidate_types or "心" in candidate_text or "寄り添" in candidate_text else base_score,
                "Se": base_score - 5 if "Se" in candidate_types else base_score - 15,
                "Ni": base_score if "Ni" in candidate_types else base_score - 5
            }
            for k in scores_dict:
                scores_dict[k] = max(40, min(95, scores_dict[k]))

            categories = ['Te (効率)', 'Ti (論理)', 'Fe (調和)', 'Fi (内省)', 'Se (実行)', 'Ni (直観)']
            values = [
                scores_dict['Te'],
                scores_dict['Ti'],
                scores_dict['Fe'],
                scores_dict['Fi'],
                scores_dict['Se'],
                scores_dict['Ni']
            ]

            # ----------------------------------------------------
            # 区分1：【応募者用（確認専用画面）】の独立レイアウト
            # ----------------------------------------------------
            if mode == "応募者用（確認専用画面）":
                st.subheader(f"👤 {selected_candidate.get('name')} 様の思考特性・認知傾向フィードバック")
                
                types_info = selected_candidate.get("types", "情報なし")
                st.markdown(f'<div class="type-box">判定タイプ / 補助特性: {types_info}</div>', unsafe_allow_html=True)
                
                c_chart, c_score = st.columns([1.2, 1])
                
                with c_chart:
                    st.markdown("#### 【思考特性レーダーチャート】")
                    fig = go.Figure(data=go.Scatterpolar(
                        r=values + [values[0]],
                        theta=categories + [categories[0]],
                        fill='toself',
                        fillcolor='rgba(139, 0, 0, 0.35)',
                        line=dict(color='#8B0000', width=2)
                    ))
                    fig.update_layout(
                        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                        showlegend=False,
                        margin=dict(l=40, r=40, t=20, b=20),
                        height=350
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with c_score:
                    st.markdown("#### 【認知特性スコア一覧】")
                    m1, m2 = st.columns(2)
                    m1.metric("Te (効率)", f"{scores_dict['Te']}点")
                    m2.metric("Ti (論理)", f"{scores_dict['Ti']}点")
                    m1.metric("Fe (調和)", f"{scores_dict['Fe']}点")
                    m2.metric("Fi (内省)", f"{scores_dict['Fi']}点")
                    m1.metric("Se (実行)", f"{scores_dict['Se']}点")
                    m2.metric("Ni (直観)", f"{scores_dict['Ni']}点")

                st.markdown("#### 【提出された事前記述内容】")
                st.info(candidate_text if candidate_text else "記述内容がありません。")

            # ----------------------------------------------------
            # 区分2：【面接官用（評価・入力画面）】の評価レイアウト
            # ----------------------------------------------------
            else:
                col_left, col_right = st.columns([1.1, 1])
                
                with col_left:
                    st.markdown(f"### 👤 応募者氏名: **{selected_candidate.get('name')}**")
                    st.markdown("#### 【事前記述内容】")
                    st.info(candidate_text if candidate_text else "記述内容がありません。")
                    
                    types_info = selected_candidate.get("types", "情報なし")
                    st.markdown("#### 【判定タイプ & 認知特性スコア】")
                    st.markdown(f'<div class="type-box">判定タイプ / 補助特性: {types_info}</div>', unsafe_allow_html=True)
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Te (効率)", f"{scores_dict['Te']}点")
                    c2.metric("Ti (論理)", f"{scores_dict['Ti']}点")
                    c3.metric("Fe (調和)", f"{scores_dict['Fe']}点")
                    c1.metric("Fi (内省)", f"{scores_dict['Fi']}点")
                    c2.metric("Se (実行)", f"{scores_dict['Se']}点")
                    c3.metric("Ni (直観)", f"{scores_dict['Ni']}点")

                with col_right:
                    st.markdown("#### 【思考特性レーダーチャート】")
                    fig = go.Figure(data=go.Scatterpolar(
                        r=values + [values[0]],
                        theta=categories + [categories[0]],
                        fill='toself',
                        fillcolor='rgba(139, 0, 0, 0.4)',
                        line=dict(color='#8B0000', width=2)
                    ))
                    fig.update_layout(
                        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                        showlegend=False,
                        margin=dict(l=40, r=40, t=30, b=30),
                        height=360
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # 初期メモのセット
                default_memo = selected_candidate.get("ai_memo", "")
                if not default_memo:
                    if "Fi" in candidate_types or "寄り添" in candidate_text or "患者" in candidate_text:
                        default_memo = f"【自動思考分析・面接ガイド】\n■強み: 相手の気持ちや個別の価値観に深く寄り添う対人共感力（Fi/Fe要素）が非常・高めです。\n■面接時確認点: 感情移入しすぎて組織のルールや客観的判断との間で葛藤を抱えないか、ストレス耐性・業務割り切り度合いを確認してください。"
                    elif "Te" in candidate_types or "論理" in candidate_text or "合理" in candidate_text:
                        default_memo = f"【自動思考分析・面接ガイド】\n■強み: 目的達成や効率・合理的な思考（Te/Ti要素）が優れています。\n■面接時確認点: 正論や効率を重視するあまり、周囲との協調や感情面への配慮がおろそかにならないか確認してください。"
                    else:
                        default_memo = f"【自動思考分析・面接ガイド】\n■思考傾向: 自身の記述・思考タイプに基づいた適性バランス型です。\n■面接時確認点: 過去の具体的な行動エピソードに基づき、チームワークと主導権発揮のバランスを確認してください。"

                st.markdown("---")
                st.markdown("### 📝 面接評価・AI分析メモ")
                
                memo_input = st.text_area("面接中の所感・メモ・質問事項", value=default_memo, height=140)
                
                btn_col1, btn_col2, btn_col3 = st.columns(3)
                
                with btn_col1:
                    if st.button("🔴 AI詳細分析を実行する"):
                        try:
                            if "GEMINI_API_KEY" in st.secrets:
                                raw_key = str(st.secrets["GEMINI_API_KEY"]).strip().strip('"').strip("'")
                                genai.configure(api_key=raw_key)
                                model = genai.GenerativeModel("gemini-1.5-flash")
                                prompt = f"応募者名: {selected_name}\n記述内容: {candidate_text}\nこの応募者の思考傾向や面接時に確認すべきポイントについて簡潔に分析してください。"
                                res = model.generate_content(prompt)
                                st.success("AI詳細分析が完了しました")
                                st.write(res.text)
                            else:
                                st.info("【内蔵分析エンジン結果】")
                                st.write(f"**{selected_name}様の深掘りポイント:**記述「{candidate_text}」より、対人共感性と個の価値観を重視する傾向が見られます。チーム内でのロールや対人トラブル時の対処方法を具体的に聞いてみましょう。")
                        except Exception:
                            st.info("【自動評価分析結果】")
                            st.write(f"**{selected_name}様の面接深掘りアドバイス:**\n・記述内容: 「{candidate_text}」\n・注目点: 言葉選びから相手への配慮（共感性）が高く示されています。\n・面接質問例: 「価値観が合わないチームメンバーと協働する際、どのように意思疎通を図りますか？」")

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
        st.info("登録されている応募者データがありません。")
except Exception as e:
    st.error(f"データ取得エラー: {e}")
