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

# ヘッダーバナー
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

# セッション状態の初期化
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# ----------------------------------------------------
# 補助関数：タイプ判定とシビアなスコア計算
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
    bad_keywords = ["セックス", "オナニー", "ブルマー", "スケベ", "暴れ", "死ね", "殺す", "風俗"]
    if any(k in text for k in bad_keywords) or len(text) < 15:
        base = 25
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
    
    for k in scores:
        scores[k] = max(10, min(95, scores[k]))
    return scores

# Gemini安全生成関数（当日用：独立した選考評価＆適正配置・労務管理レポート）
def generate_gemini_report_day_actual(name, text):
    prompt = f"""【最重要命令】
出力テキストには英語を一切使用せず、すべて日本語のみで出力してください。「面接」という単語や面接前提の観察指示は一切含めないでください。

あなたは人事・労務管理および組織適性判定の厳格な専門家です。
以下の応募者のアンケート記述内容を徹底的に分析し、面接を前提としない独立した「選考評価＆適正配置・労務管理レポート」を作成してください。

【応募者氏名】: {name}
【記述内容】:
"{text}"

【評価・分析ガイドライン】
1. 独立した選考判定: 記述内容の論理性、具体性、倫理観、組織適合リスクを評価し、本システム単体での採否判定軸を提示してください。
2. 配置および労務管理上の留意点: 採用した場合の適正な配置先、トラブル防止のための労務管理・マネジメント上の具体的な注意点を明記してください。
3. 厳格なリスク指摘: 単なる抽象論や感情論に偏っている点、業務上のボトルネックとなり得る短所を忖度なく指摘してください。

以下の見出し構成に従って、すべて日本語で作成してください。

【AI選考評価＆配属活用レポート】
■ 思考傾向・特性（長所と短所分析）:
・長所・評価できる点: （記述から読み取れる強みや意欲）
・短所・リスク・懸念点: （具体性の欠如や組織上の懸念リスク）

■ 採否判定にあたっての評価軸:
（本判定結果に基づく採用の可否判断および重要リスク）

■ 採用後の適正配置・労務管理アプローチ:
・適正配属: （強みが活きる具体的な部署、またはリスク回避のための配置制限）
・労務管理・マネジメントの留意点: （トラブルを防ぎ、安定的なパフォーマンスを発揮させるための具体的な管理アプローチ）

■ 最終選考評価メモ:
"""

    try:
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        for model_name in available_models:
            try:
                model = genai.GenerativeModel(model_name)
                res = model.generate_content(prompt, generation_config={"temperature": 0.1})
                if res and hasattr(res, 'text') and res.text:
                    if any(eng in res.text for eng in ["Applicant", "Goal", "Constraints", "Role:", "Description:", "Content:"]):
                        continue
                    return res.text
            except Exception:
                continue
    except Exception:
        pass

    # フォールバックエンジン（独立判定・労務管理特化）
    bad_keywords = ["セックス", "オナニー", "ブルマー", "スケベ", "暴れ", "死ね", "殺す", "風俗"]
    if any(k in text for k in bad_keywords):
        return (
            "【AI選考評価＆配属活用レポート】\n"
            "■ 思考傾向・特性（長所と短所分析）:\n"
            "・長所・評価できる点: なし\n"
            "・短所・リスク・懸念点: 【🚨 重大警告・不採用推奨】公序良俗に反する表現および就労目的から著しく逸脱した記述が含まれています。\n"
            "■ 採否判定にあたっての評価軸:\n"
            "・社会的適合性・倫理観に重大な欠陥があり、採用リスクが極めて高いため【不採用】と判定します。\n"
            "■ 採用後の適正配置・労務管理アプローチ:\n"
            "・適性配属: なし（採用不可）\n"
            "・労務管理・マネジメントの留意点: 採用不可のため該当なし。\n"
            "■ 最終選考評価メモ:\n"
            "・コンプライアンス上の重大なリスクがあるため採用不可。"
        )
    elif len(text) < 30:
        return (
            "【AI選考評価＆配属活用レポート】\n"
            "■ 思考傾向・特性（長所と短所分析）:\n"
            "・長所・評価できる点: 他者への配慮や姿勢を示そうとする点。\n"
            "・短所・リスク・懸念点: 記述が極めて短く抽象的であり、具体的にどのような行動をとるのか根拠が欠如している点。口先だけの理想論に終わるリスクがある。\n"
            "■ 採否判定にあたっての評価軸:\n"
            "・行動の具体性や論理性が欠如しているため、慎重な採否判断が必要です。\n"
            "■ 採用後の適正配置・労務管理アプローチ:\n"
            "・適性配属: 明確な指示体系と定型業務が整備されたポジション\n"
            "・労務管理・マネジメントの留意点: 曖昧な指示を避け、業務プロセスの可視化と定期的チェックによる進捗管理を徹底すること。\n"
            "■ 最終選考評価メモ:\n"
            "・表層的な表現に終始しているため、業務実行時の論理性と達成意欲に課題あり。"
        )
    else:
        return (
            "【AI選考評価＆配属活用レポート】\n"
            "■ 思考傾向・特性（長所と短所分析）:\n"
            "・長所・評価できる点: 他者への共感性や対人配慮の意向が強く伺える点。\n"
            "・短所・リスク・懸念点: 感情面への配慮に偏るあまり、客観的判断や業務効率を重視すべき場面での判断力に課題が残る点。\n"
            "■ 採否判定にあたっての評価軸:\n"
            "・組織の規律遵守と客観的思考が求められる職種においては適性に懸念が残るため、総合的な慎重判定を推奨。\n"
            "■ 採用後の適正配置・労務管理アプローチ:\n"
            "・適性配属: チーム間連携やサポート業務を中心とする調整ポジション\n"
            "・労務管理・マネジメントの留意点: 感情的判断に流されないようルール遵守を教育し、客観的な成果基準に基づいた評価管理を行うこと。\n"
            "■ 最終選考評価メモ:\n"
            "・対人配慮は高いが、客観的判断力およびプレッシャー耐性のマネジメントが不可欠。"
        )

# ----------------------------------------------------
# サイドバー：メニュー、管理者ログイン（パスワード：7777）、免責事項
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
  AI分析および本判定結果は選考・採否決定における参考材料（判断の補助ツール）です。**最終的な選考判定および合否決定、配属判断は、選考責任者の責任において行ってください。**
- **個人情報の管理・禁止事項**
  採用選考および労務管理以外の目的での使用、ならびに第三者への無断漏洩・共有は厳禁です。
""")

# ----------------------------------------------------
# A. 応募者入力画面（当日提出用）
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

    with st.form(key="candidate_form_day"):
        applicant_name = st.text_input("お名前（氏名）", placeholder="例：山田 太郎")
        applicant_text = st.text_area("思考・表現力に関する記述", height=150, placeholder="ご自身の考えや価値観、仕事で大切にしていること等を自由にご記入ください。")
        
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
                
                st.success("提出が完了いたしました。ご協力ありがとうございました！")
                st.info("※入力内容は正常に送信されました。この画面を閉じていただいて構いません。")
            except Exception as e:
                st.error(f"送信時にエラーが発生しました: {e}")

# ----------------------------------------------------
# B. 管理者画面（最終選考・採否＆適正配置・労務管理用）
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

                # ----------------------------------------------------
                # 当日用：面接文面や前日用メモがある場合は即座に「選考評価＆配属活用レポート」に強制上書き
                # ----------------------------------------------------
                st.markdown("---")
                st.markdown("### 📝 AI選考評価・採否＆適性配置・労務管理レポート")
                
                saved_memo = selected_candidate.get("ai_memo", "")
                
                is_before_version = "AI面接事前準備レポート" in str(saved_memo)
                has_interview_word = "面接にて" in str(saved_memo) or "面接官" in str(saved_memo)
                is_invalid_english = any(eng in str(saved_memo) for eng in ["Applicant", "Goal", "Constraints", "Role:", "Description:", "Content:"])
                
                if not saved_memo or is_before_version or has_interview_word or is_invalid_english:
                    with st.spinner("当日用の採否判定＆労務管理レポートを作成中..."):
                        default_memo = generate_gemini_report_day_actual(selected_candidate.get('name'), candidate_text.strip())
                        try:
                            supabase.table("candidate_responses").update({"ai_memo": default_memo}).eq("id", record_id).execute()
                        except Exception:
                            pass
                else:
                    default_memo = saved_memo

                memo_input = st.text_area("AI詳細レポート 兼 選考・配属・労務メモ", value=default_memo, height=260)
                
                btn_c1, btn_c2 = st.columns([1, 1])
                
                with btn_c1:
                    if st.button("💾 評価メモをデータベースに保存する"):
                        try:
                            supabase.table("candidate_responses").update({"ai_memo": memo_input}).eq("id", record_id).execute()
                            st.success("評価・労務メモを保存しました。")
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
