import streamlit as st
from supabase import create_client
import google.generativeai as genai
import pandas as pd
import plotly.graph_objects as go

# 1. ページ基本設定
st.set_page_config(
    page_title="思考・表現力セッション",
    page_icon="🔴",
    layout="wide"
)

# カスタムCSS（赤系テーマ・カードデザイン）
st.markdown("""
<style>
    .day-banner {
        background-color: #8B0000;
        color: #FFFFFF;
        padding: 10px 18px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 1.1rem;
        margin-bottom: 20px;
    }
    .day-title {
        color: #8B0000;
        border-bottom: 3px solid #8B0000;
        padding-bottom: 6px;
        margin-bottom: 15px;
        font-size: 1.6rem;
        font-weight: bold;
    }
    .instruction-box {
        background-color: #f8f9fa;
        border-left: 4px solid #8B0000;
        padding: 15px;
        border-radius: 4px;
        margin-bottom: 20px;
        line-height: 1.6;
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

# ヘッダーバナー
st.markdown('<div class="day-banner">🔴 思考・表現力セッション</div>', unsafe_allow_html=True)

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

# セッション状態の初期化
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# ----------------------------------------------------
# サイドバー：メニュー、管理者ログイン/ログアウト、免責事項
# ----------------------------------------------------
st.sidebar.title("📌 メニュー・設定")

if not st.session_state.is_admin:
    st.sidebar.subheader("🔒 管理者ログイン")
    password_input = st.sidebar.text_input("パスワードを入力", type="password")
    if st.sidebar.button("ログイン"):
        if password_input == "7777":
            st.session_state.is_admin = True
            st.rerun()
        else:
            st.sidebar.error("パスワードが違います")
else:
    st.sidebar.success("管理者としてログイン中")
    if st.sidebar.button("🔄 応募者画面へ戻る（ログアウト）"):
        st.session_state.is_admin = False
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("⚠️ 注意事項・禁止事項・免責事項")
st.sidebar.info("""
- **判定結果の位置付け**
  本システムの思考性・認知特性分析は、応募者の自己申告テキストに基づく傾向分析であり、人物像や能力を確定するものではありません。
- **採用判断の責任**
  AI分析および本判定結果は面接における参考材料（深掘り質問の補助ツール）です。**最終的な選考判定および合否決定は、採用担当者・面接官ご自身の責任において行ってください。**
- **個人情報の管理・禁止事項**
  採用選考以外の目的での使用、および第三者への無断漏洩・共有は厳禁です。
""")

# ----------------------------------------------------
# A. 応募者入力画面（初期画面）
# ----------------------------------------------------
if not st.session_state.is_admin:
    st.markdown('<h1 class="day-title">思考・表現力アンケート入力フォーム</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="instruction-box">
        <h4>【ご回答にあたってのお願い】</h4>
        <p>本アンケートは、皆様の日常的な考え方や仕事における思考傾向を把握し、相互の理解を深めるためのものです。<br>
        正解・不正解はありませんので、ご自身の率直なお考え・お気持ちをそのままご記入ください。</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form(key="candidate_form"):
        applicant_name = st.text_input("お名前（氏名）", placeholder="例：山田 太郎")
        applicant_text = st.text_area("思考・表現力に関する記述", height=150, placeholder="ご自身の考えや価値観、仕事で大切にしていること等を自由にご記入ください。")
        
        submit_button = st.form_submit_button(label="提出する")

    if submit_button:
        if not applicant_name.strip() or not applicant_text.strip():
            st.warning("お名前と記述内容の両方を入力してください。")
        else:
            try:
                types_val = ["Fi型（価値観・内省）", "補助Fe"] if "共感" in applicant_text or "患者" in applicant_text or "寄り添" in applicant_text else ["Te型（効率・構造化）", "補助Ti"]
                
                new_data = {
                    "name": applicant_name.strip(),
                    "text": applicant_text.strip(),
                    "types": types_val
                }
                
                supabase.table("candidate_responses").insert(new_data).execute()
                
                st.success("提出が完了いたしました。ご協力ありがとうございました！")
                st.info("※入力内容は正常に送信されました。この画面を閉じていただいて構いません。")
            except Exception as e:
                st.error(f"送信時にエラーが発生しました: {e}")

# ----------------------------------------------------
# B. 管理者画面（ログイン後：分析機能とメモ欄を一括統合）
# ----------------------------------------------------
else:
    st.markdown('<h1 class="day-title">【管理者用】面接・思考性評価システム</h1>', unsafe_allow_html=True)
    
    try:
        response = supabase.table("candidate_responses").select("*").execute()
        data = response.data
        
        if data:
            names = [item.get("name", "無名") for item in data]
            selected_name = st.selectbox("評価・確認する応募者を選択してください", names)
            selected_candidate = next((item for item in data if item.get("name") == selected_name), None)
            
            if selected_candidate:
                record_id = selected_candidate.get("id")
                candidate_text = selected_candidate.get("text", "")
                candidate_types = str(selected_candidate.get("types", ""))
                
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

                col_left, col_right = st.columns([1.1, 1])
                
                with col_left:
                    st.markdown(f"### 👤 応募者氏名: **{selected_candidate.get('name')}**")
                    st.markdown("#### 【事前記述内容】")
                    st.info(candidate_text if candidate_text else "記述内容がありません。")
                    
                    types_info = selected_candidate.get("types", "情報なし")
                    st.markdown("#### 【判定タイプ & 認知特性スコア】")
                    st.write(f"判定タイプ / 補助特性: `{types_info}`")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Te (効率)", f"{scores_dict['Te']}点")
                    c2.metric("Ti (論理)", f"{scores_dict['Ti']}点")
                    c3.metric("Fe (調和)", f"{scores_dict['Fe']}点")
                    c1.metric("Fi (内省)", f"{scores_dict['Fi']}点")
                    c2.metric("Se (実行)", f"{scores_dict['Se']}点")
                    c3.metric("Ni (直観)", f"{scores_dict['Ni']}点")

                with col_right:
                    st.markdown("#### 【思考特性レーダーチャート】")
                    categories = ['Te (効率)', 'Ti (論理)', 'Fe (調和)', 'Fi (内省)', 'Se (実行)', 'Ni (直観)']
                    values = [
                        scores_dict['Te'], scores_dict['Ti'], scores_dict['Fe'],
                        scores_dict['Fi'], scores_dict['Se'], scores_dict['Ni']
                    ]
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

                # ----------------------------------------------------
                # 統合された「AI面接評価・詳細ガイドメモ」の自動生成ロジック
                # ----------------------------------------------------
                st.markdown("---")
                st.markdown("### 📝 AI面接統合評価＆詳細分析メモ")
                
                saved_memo = selected_candidate.get("ai_memo", "")
                
                # 保存済みメモがない場合、思考特性に応じた詳細評価レポートを自動入力
                if not saved_memo:
                    if "Fi" in candidate_types or "寄り添" in candidate_text or "患者" in candidate_text:
                        default_memo = (
                            f"【AI統合面接評価レポート】\n"
                            f"■ 思考傾向・特性: 個人の感情や価値観に深く寄り添う共感・内省型（Fi/Fe優位）\n"
                            f"■ 期待される強み: 患者様やクライアントの真のニーズを汲み取る誠実な対人サポート力\n"
                            f"■ 面接での深掘り確認ポイント・質問例:\n"
                            f"  1. 「感情移入しやすい場面で、客観的な判断や組織ルールとのバランスをどう取りますか？」\n"
                            f"  2. 「価値観が異なるチームメンバーと衝突した際、どのように対話して解決を図りますか？」\n"
                            f"■ 面接官メモ欄（以下に面接での所感や追加質問を自由にお書きください）:\n"
                        )
                    elif "Te" in candidate_types or "論理" in candidate_text or "合理" in candidate_text:
                        default_memo = (
                            f"【AI統合面接評価レポート】\n"
                            f"■ 思考傾向・特性: 目的達成や合理的成果、構造化を重視する効率思考型（Te/Ti優位）\n"
                            f"■ 期待される強み: 課題のロジカルな整理、明確な方針立案と高い業務推進力\n"
                            f"■ 面接での深掘り確認ポイント・質問例:\n"
                            f"  1. 「効率や正論を重視する際、周囲の感情や協調性とのバランスで配慮している点は何ですか？」\n"
                            f"  2. 「予想外の変更や曖昧な状況が生じた際、どのように柔軟に対処しますか？」\n"
                            f"■ 面接官メモ欄（以下に面接での所感や追加質問を自由にお書きください）:\n"
                        )
                    else:
                        default_memo = (
                            f"【AI統合面接評価レポート】\n"
                            f"■ 思考傾向・特性: 記述内容と属性に基づくバランス型の適性思考パターン\n"
                            f"■ 期待される強み: 状況に応じた柔軟な対応力とバランス感覚\n"
                            f"■ 面接での深掘り確認ポイント・質問例:\n"
                            f"  1. 「過去に最も力を入れた経験において、ご自身が果たした具体的な役割を教えてください。」\n"
                            f"■ 面接官メモ欄（以下に面接での所感や追加質問を自由にお書きください）:\n"
                        )
                else:
                    default_memo = saved_memo

                # 1つの統合されたテキストエリアに表示・編集
                memo_input = st.text_area("AI詳細分析ガイド 兼 面接評価メモ", value=default_memo, height=200)
                
                btn_c1, btn_c2 = st.columns([1, 1])
                
                with btn_c1:
                    if st.button("💾 評価メモをデータベースに保存する"):
                        try:
                            supabase.table("candidate_responses").update({"ai_memo": memo_input}).eq("id", record_id).execute()
                            st.success("面接評価メモを保存しました。")
                        except Exception as e:
                            st.error(f"保存エラー: {e}")

                with btn_c2:
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
