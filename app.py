import streamlit as st
from supabase import create_client
import google.generativeai as genai
import pandas as pd
import plotly.graph_objects as go

# 1. ページ基本設定
st.set_page_config(
    page_title="思考・表現力セッション（自分用・当日用）",
    page_icon="🔴",
    layout="wide"
)

# カスタムCSS（赤系テーマ）
st.markdown("""
<style>
    .day-banner {
        background-color: #8B0000;
        color: #FFFFFF !important;
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
        color: #212529 !important;
        border-left: 5px solid #8B0000;
        padding: 15px;
        border-radius: 4px;
        margin-bottom: 20px;
        line-height: 1.6;
    }
    .instruction-box h4 {
        color: #8B0000 !important;
        margin-top: 0;
        margin-bottom: 10px;
        font-weight: bold;
    }
    .instruction-box p {
        color: #212529 !important;
        margin-bottom: 0;
    }
    div.stButton > button:first-child {
        background-color: #A52A2A;
        color: white !important;
        border-radius: 6px;
        border: none;
        font-weight: bold;
        padding: 8px 16px;
    }
    div.stButton > button:first-child:hover {
        background-color: #8B0000;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="day-banner">🔴 思考・表現力セッション（自分用・当日用）</div>', unsafe_allow_html=True)

# Supabase初期化
@st.cache_resource
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"Supabase接続エラー: {e}")

# Gemini API初期化
gemini_ready = False
if "GEMINI_API_KEY" in st.secrets:
    try:
        raw_key = str(st.secrets["GEMINI_API_KEY"]).strip().strip('"').strip("'")
        genai.configure(api_key=raw_key)
        gemini_ready = True
    except Exception:
        gemini_ready = False

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# ----------------------------------------------------
# 補助関数（シンプル・全職種共通ロジック）
# ----------------------------------------------------
def analyze_text_simple(text):
    judging = "Te型（効率・構造化）" if any(w in text for w in ["効率", "計画", "目標", "構造", "成果", "システム"]) else \
              "Ti型（論理・分析）" if any(w in text for w in ["論理", "分析", "仕組み", "本質", "理由"]) else \
              "Fe型（調和・配慮）" if any(w in text for w in ["調和", "チーム", "協力", "感謝", "配慮"]) else \
              "Fi型（価値観・内省）"
    
    perceiving = "Se（現場・実行）" if any(w in text for w in ["行動", "現場", "実践", "体験", "スピード"]) else \
                 "Si（経験・確実）" if any(w in text for w in ["経験", "規則", "確実", "継続", "積み重ね"]) else \
                 "Ne（アイデア・可能性）" if any(w in text for w in ["発想", "アイデア", "挑戦", "可能性", "変化"]) else \
                 "Ni（本質・洞察）"
                 
    return [judging, f"補助{perceiving}"]

def calculate_scores(text, types_list):
    types_str = " ".join(types_list)
    risk_keywords = ["違反", "不正", "力こそが正義", "馬鹿", "軍人", "SEX", "オナニー", "ブルマー", "いびっ"]
    has_risk = any(k in text for k in risk_keywords)
    
    if len(text) < 30 or has_risk:
        base = 20
    else:
        base = 45 + (len(text) % 25)
    
    scores = {
        "Te": base + 15 if "Te" in types_str or any(w in text for w in ["効率", "目標", "計画"]) else base - 10,
        "Ti": base + 10 if "Ti" in types_str or any(w in text for w in ["論理", "分析", "仕組み"]) else base - 5,
        "Fe": base + 10 if "Fe" in types_str or any(w in text for w in ["調和", "協力", "感謝"]) else base - 10,
        "Fi": base + 15 if "Fi" in types_str or any(w in text for w in ["価値観", "想い", "寄り添"]) else base - 5,
        "Se": base + 10 if "Se" in types_str or any(w in text for w in ["行動", "現場", "実践"]) else base - 10,
        "Si": base + 10 if "Si" in types_str or any(w in text for w in ["経験", "規則", "確実"]) else base - 10,
        "Ne": base + 10 if "Ne" in types_str or any(w in text for w in ["発想", "挑戦", "変化"]) else base - 10,
        "Ni": base + 10 if "Ni" in types_str or any(w in text for w in ["洞察", "未来", "ビジョン"]) else base - 10,
    }
    
    if len(text) < 30 or has_risk:
        for k in scores:
            scores[k] = min(scores[k], 25)
            
    for k in scores:
        scores[k] = max(10, min(95, scores[k]))
    return scores

def get_default_self_day_report(text):
    risk_keywords = ["違反", "不正", "力こそが正義", "馬鹿", "軍人", "SEX", "オナニー", "ブルマー", "いびっ"]
    if any(k in text for k in risk_keywords):
        return (
            "【AI選考評価＆配属活用レポート】\n"
            "■ 思考傾向・特性（長所と短所分析）:\n"
            "・長所・評価できる点: 特になし\n"
            "・短所・リスク・懸念点: 【🚨 重大コンプライアンスリスク】組織の規範や法令を軽視する懸念があり、ガバナンス上の問題を引き起こすリスクが高い状態です。\n"
            "■ 採否判定にあたっての評価軸:\n"
            "・企業のガバナンスおよび社会的信用を損なう危険性が高いため【不採用】を推奨します。\n"
            "■ 採用後の適正配置・労務管理アプローチ:\n"
            "・適性配属: 採用不可\n"
            "・労務管理・マネジメントの留意点: 採用不可のため該当なし。\n"
            "■ 最終選考評価メモ:\n"
            "・コンプライアンス上の重大リスクのため採用不可。"
        )
    elif len(text) < 30:
        return (
            "【AI選考評価＆配属活用レポート】\n"
            "■ 思考傾向・特性（長所と短所分析）:\n"
            "・長所・評価できる点: 簡潔に回答しようとする姿勢。\n"
            "・短所・リスク・懸念点: 記述が極めて抽象的であり、具体性や客観的な論理根拠が不足している点。\n"
            "■ 採否判定にあたっての評価軸:\n"
            "・業務遂行に必要な論理的思考力と具体性に課題があるため慎重判定を推奨。\n"
            "■ 採用後の適正配置・労務管理アプローチ:\n"
            "・適性配属: 明確な手順書（SOP）が整備された定型ポジション\n"
            "・労務管理・マネジメントの留意点: 業務プロセスの可視化と定期的チェックを徹底すること。\n"
            "■ 最終選考評価メモ:\n"
            "・表層的記述のため業務実行時の論理的根拠と達成力に検証が必要。"
        )
    else:
        return (
            "【AI選考評価＆配属活用レポート】\n"
            "■ 思考傾向・特性（長所と短所分析）:\n"
            "・長所・評価できる点: 自身の考えや意向を一定の表現力で記述できている点。\n"
            "・短所・リスク・懸念点: 主観的な思考に偏る場合があり、組織ルール遵守や客観的判断のバランス確認が必要な点。\n"
            "■ 採否判定にあたっての評価軸:\n"
            "・組織の規律遵守および客観的成果基準に適合できるか総合判定を推奨。\n"
            "■ 採用後の適正配置・労務管理アプローチ:\n"
            "・適性配属: チーム間連携やサポート・調整を中心とするポジション\n"
            "・労務管理・マネジメントの留意点: 客観的な成果指標に基づいた評価管理を行うこと。\n"
            "■ 最終選考評価メモ:\n"
            "・客観的判断力および組織適合性のマネジメントが不可欠。"
        )

# ----------------------------------------------------
# サイドバー
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
  本システムの思考性・認知特性分析は傾向分析であり、人物像を確定するものではありません。
- **採用判断の責任**
  最終的な選考判定および合否決定の責任は選考責任者に帰属します。
""")

# ----------------------------------------------------
# A. 応募者入力画面
# ----------------------------------------------------
if not st.session_state.is_admin:
    st.markdown('<h1 class="day-title">思考・表現力アンケート入力フォーム</h1>', unsafe_allow_html=True)
    
    with st.form(key="candidate_form_day"):
        applicant_name = st.text_input("お名前（氏名）", placeholder="例：山田 太郎")
        applicant_text = st.text_area("思考・表現力に関する記述", height=150)
        submit_button = st.form_submit_button(label="提出する")

    if submit_button:
        if not applicant_name.strip() or not applicant_text.strip():
            st.warning("お名前と記述内容の両方を入力してください。")
        else:
            try:
                types_val = analyze_text_simple(applicant_text.strip())
                new_data = {
                    "name": applicant_name.strip(),
                    "text": applicant_text.strip(),
                    "types": types_val,
                    "app_type": "day"
                }
                supabase.table("candidate_responses").insert(new_data).execute()
                st.success("提出が完了いたしました。")
            except Exception as e:
                st.error(f"送信時にエラーが発生しました: {e}")

# ----------------------------------------------------
# B. 管理者画面（ai_memo_self_day カラムを使用）
# ----------------------------------------------------
else:
    st.markdown('<h1 class="day-title">【管理者用】選考判定・適正配置＆労務管理システム</h1>', unsafe_allow_html=True)
    
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
                candidate_types = selected_candidate.get("types", [])
                
                scores_dict = calculate_scores(candidate_text, candidate_types)

                col_left, col_right = st.columns([1.1, 1])
                
                with col_left:
                    st.markdown(f"### 👤 応募者氏名: **{selected_candidate.get('name')}**")
                    st.markdown("#### 【事前記述内容】")
                    st.info(candidate_text if candidate_text else "記述内容がありません。")
                    
                    st.markdown("#### 【判定タイプ & 認知特性スコア】")
                    st.write(f"判定タイプ / 認知特性: `{candidate_types}`")
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Te (効率)", f"{scores_dict['Te']}点")
                    c2.metric("Ti (論理)", f"{scores_dict['Ti']}点")
                    c3.metric("Fe (調和)", f"{scores_dict['Fe']}点")
                    c4.metric("Fi (内省)", f"{scores_dict['Fi']}点")
                    
                    c1.metric("Se (実行)", f"{scores_dict['Se']}点")
                    c2.metric("Si (確実)", f"{scores_dict['Si']}点")
                    c3.metric("Ne (発想)", f"{scores_dict['Ne']}点")
                    c4.metric("Ni (洞察)", f"{scores_dict['Ni']}点")

                with col_right:
                    st.markdown("#### 【思考・認知特性レーダーチャート】")
                    categories = ['Te', 'Ti', 'Fe', 'Fi', 'Se', 'Si', 'Ne', 'Ni']
                    values = [scores_dict[k] for k in categories]
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
                        height=380
                    )
                    st.plotly_chart(fig, use_container_width=True)

                st.markdown("---")
                st.markdown("### 📝 AI選考評価・採否＆適性配置・労務管理レポート")
                
                saved_memo = selected_candidate.get("ai_memo_self_day", "")
                
                if not saved_memo:
                    default_memo = get_default_self_day_report(candidate_text.strip())
                    try:
                        supabase.table("candidate_responses").update({"ai_memo_self_day": default_memo}).eq("id", record_id).execute()
                    except Exception:
                        pass
                else:
                    default_memo = saved_memo

                memo_input = st.text_area("AI詳細レポート 兼 選考・配属・労務メモ", value=default_memo, height=260)
                
                btn_c1, btn_c2 = st.columns([1, 1])
                
                with btn_c1:
                    if st.button("💾 評価メモをデータベースに保存する"):
                        try:
                            supabase.table("candidate_responses").update({"ai_memo_self_day": memo_input}).eq("id", record_id).execute()
                            st.success("評価メモを保存しました。")
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
