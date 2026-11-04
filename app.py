import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
import pandas as pd
import plotly.graph_objects as go

# 1. ページ基本設定（自分用・当日用）
st.set_page_config(
    page_title="思考・表現力セッション（自分用・当日用）",
    page_icon="🔴",
    layout="wide"
)

# カスタムCSS（当日用：赤系デザイン）
st.markdown("""
<style>
    .day-banner {
        background-color: #8B0000;
        color: #FFFFFF !important;
        padding: 16px 18px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 1.15rem;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .day-banner-dot {
        height: 14px;
        width: 14px;
        background-color: #FF4500;
        border-radius: 50%;
        display: inline-block;
    }
    .guide-box-day {
        background-color: #FFF5F5;
        border-left: 5px solid #E53E3E;
        padding: 15px 20px;
        border-radius: 4px;
        margin-bottom: 20px;
    }
    .guide-box-day h4 {
        color: #C53030;
        margin-top: 0;
        margin-bottom: 8px;
        font-size: 1.1rem;
    }
    .guide-box-day p {
        color: #2D3748;
        font-size: 0.95rem;
        line-height: 1.6;
        margin: 0;
    }
</style>
""", unsafe_allow_html=True)

# 2. Supabase初期化
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"].strip()
        key = st.secrets["SUPABASE_KEY"].strip()
        return create_client(url, key)
    except Exception as e:
        st.error(f"Supabase接続設定エラー: {e}")
        return None

supabase = init_supabase()

# 3. Gemini API設定
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"].strip())
    gemini_ready = True
except Exception as e:
    gemini_ready = False

# 4. サイドバー構成
st.sidebar.title("📌 メニュー・設定")
st.sidebar.markdown("---")

st.sidebar.subheader("🔒 管理者ログイン")
admin_password = st.sidebar.text_input("パスワードを入力", type="password", key="admin_pass_input")

if st.sidebar.button("ログイン", key="login_btn"):
    if admin_password == "7777":
        st.session_state["is_admin"] = True
        st.sidebar.success("管理者としてログインしました")
        st.rerun()
    else:
        st.sidebar.error("パスワードが正しくありません")

if st.session_state.get("is_admin", False):
    st.sidebar.success("管理者としてログイン中")
    if st.sidebar.button("応募者画面へ戻る（ログアウト）", key="logout_btn"):
        st.session_state["is_admin"] = False
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚠️ 注意事項・禁止事項・免責事項")
st.sidebar.warning(
    "**判定結果の位置付け**\n"
    "本システムの思考性・認知特性分析は傾向分析であり、人物像を確定するものではありません。\n\n"
    "**採用判断の責任**\n"
    "最終的な選考判定および合否決定の責任は選考責任者に帰属します。"
)

# 5. ヘルパー関数
def calculate_scores(text):
    length = len(text)
    scores = {
        "Te": 25, "Ti": 15, "Fe": 10, "Fi": 15,
        "Se": 10, "Si": 10, "Ne": 10, "Ni": 10
    }
    if length > 100:
        scores["Te"] = min(35, 25 + (length // 50))
        scores["Ti"] = min(30, 15 + (length // 60))
    return scores

def analyze_text_simple(text):
    if not gemini_ready:
        return get_default_law_day_report()
    
    prompt = f"""
以下の応募者の記述内容を分析し、本日の面接・選考で活用できる労務・採用評価レポートを作成してください。

【応募者の記述】
{text}

【出力フォーマット】
【AI選考評価＆配属活用レポート】
■ 思考傾向・特性（長所と短所分析）：
・長所・評価できる点：...
・短所・リスク・懸念点：...
■ 採否判定にあたっての評価軸：
・...
■ 採用後の適正配置・労務管理アプローチ：
・適正配置：...
・労務管理・マネジメントの留意点：...
■ 最終選考評価メモ：
・...
"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception:
        return get_default_law_day_report()

def get_default_law_day_report():
    return """【AI選考評価＆配属活用レポート】
■ 思考傾向・特性（長所と短所分析）：
・長所・評価できる点：簡潔に回答しようとする姿勢。
・短所・リスク・懸念点：記述が極めて抽象的であり、具体性や客観的な論理根拠が不足している点。
■ 採否判定にあたっての評価軸：
・業務遂行に必要な論理思考力と具体性に課題があるため慎重判定を推奨。
■ 採用後の適正配置・労務管理アプローチ：
・適正配置：明確な手順書（SOP）が整備された定型ポジション
・労務管理・マネジメントの留意点：業務プロセスの可視化と定期的なチェックを徹底すること。
■ 最終選考評価メモ：
・表面的な記述のため業務実行時の論理的根拠と達成力に検証が必要。"""

# 6. メイン画面制御
is_admin = st.session_state.get("is_admin", False)

if not is_admin:
    # --- 応募者・受検者画面 ---
    st.markdown('<div class="day-banner"><span class="day-banner-dot"></span>思考・表現力セッション</div>', unsafe_allow_html=True)
    st.title("思考・表現力アンケート入力フォーム")

    # 【ご案内ボックス（回答の目的・趣旨）】
    st.markdown("""
    <div class="guide-box-day">
        <h4>【当日セッションのご案内】</h4>
        <p>本アンケートは、本日のセッション・面接をより実りあるものにするため、事前に皆様の日常的なお考えや仕事観をお伺いするものです。正解・不正解はございませんので、リラックスしてご自身の率直なご意見をご回答ください。</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("applicant_form"):
        name = st.text_input("お名前（氏名）", placeholder="例：山田太郎")
        content = st.text_area("思考・表現力に関する記述", height=150, placeholder="ご自身の考えや仕事観についてご記入ください。")
        submit_btn = st.form_submit_button("提出する")

    if submit_btn:
        if not name or not content:
            st.error("お名前と記述内容の両方を入力してください。")
        else:
            with st.spinner("送信中..."):
                scores = calculate_scores(content)
                ai_report = analyze_text_simple(content)
                
                db_data = {
                    "name": name,
                    "email": "not_required@example.com",
                    "content": content,
                    "score_logical": scores["Te"],
                    "score_proactive": scores["Ti"],
                    "score_analysis": scores["Fe"],
                    "score_empathy": scores["Fi"],
                    "score_growth": scores["Se"],
                    "score_total": sum(scores.values()),
                    "ai_report": ai_report,
                    "interview_questions": "管理画面を参照",
                    "recommended_role": "管理画面を参照"
                }
                
                if supabase:
                    try:
                        supabase.table("candidate_responses").insert(db_data).execute()
                        st.success("回答を受け付けました。ご協力ありがとうございました。")
                    except Exception as e:
                        st.error(f"データベース保存エラー: {e}")
                else:
                    st.success("回答を受け付けました（デモモード）")

else:
    # --- 管理者画面 ---
    st.title("【管理者用】 選考判定・適性配置＆労務管理システム")
    st.markdown("---")

    if supabase:
        try:
            res = supabase.table("candidate_responses").select("*").execute()
            records = res.data
            
            if records:
                df = pd.DataFrame(records)
                applicant_names = df["name"].tolist()
                
                selected_name = st.selectbox("評価・確認する応募者を選択してください", applicant_names)
                
                if selected_name:
                    row = df[df["name"] == selected_name].iloc[0]
                    
                    col_left, col_right = st.columns([1, 1])
                    
                    with col_left:
                        st.markdown(f"### 👤 応募者氏名: {row['name']}")
                        st.markdown("#### 【事前記述内容】")
                        st.info(row['content'])
                        
                        st.markdown("#### 【判定タイプ＆認知特性スコア】")
                        st.write('判定タイプ / 認知特性: ["Te型（効率・構造化）", "補助Ni（本質・洞察）"]')
                        
                        scores = {
                            "Te(効率)": row.get('score_logical', 25),
                            "Ti(論理)": row.get('score_proactive', 15),
                            "Fe(調和)": row.get('score_analysis', 10),
                            "Fi(内省)": row.get('score_empathy', 15),
                            "Se(実行)": row.get('score_growth', 10),
                            "Si(確実)": 10,
                            "Ne(発想)": 10,
                            "Ni(洞察)": 10
                        }
                        
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Te(効率)", f"{scores['Te(効率)']}点")
                        c2.metric("Ti(論理)", f"{scores['Ti(論理)']}点")
                        c3.metric("Fe(調和)", f"{scores['Fe(調和)']}点")
                        c4.metric("Fi(内省)", f"{scores['Fi(内省)']}点")
                        
                        c5, c6, c7, c8 = st.columns(4)
                        c5.metric("Se(実行)", f"{scores['Se(実行)']}点")
                        c6.metric("Si(確実)", f"{scores['Si(確実)']}点")
                        c7.metric("Ne(発想)", f"{scores['Ne(発想)']}点")
                        c8.metric("Ni(洞察)", f"{scores['Ni(洞察)']}点")

                    with col_right:
                        st.markdown("#### 【思考・認知特性レーダーチャート】")
                        categories = ['Te', 'Ti', 'Fe', 'Fi', 'Se', 'Si', 'Ne', 'Ni']
                        values = [
                            scores['Te(効率)'], scores['Ti(論理)'], scores['Fe(調和)'], scores['Fi(内省)'],
                            scores['Se(実行)'], scores['Si(確実)'], scores['Ne(発想)'], scores['Ni(洞察)']
                        ]
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatterpolar(
                            r=values + [values[0]],
                            theta=categories + [categories[0]],
                            fill='toself',
                            name=row['name'],
                            fillcolor='rgba(180, 40, 40, 0.4)',
                            line=dict(color='#8B0000')
                        ))
                        fig.update_layout(
                            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                            showlegend=False,
                            margin=dict(l=40, r=40, t=20, b=20)
                        )
                        st.plotly_chart(fig, use_container_width=True)

                    st.markdown("---")
                    st.markdown("### 📑 AI選考評価・採否＆適性配置・労務管理レポート")
                    
                    report_text = st.text_area(
                        "AI詳細レポート 兼 選考・配置・労務メモ",
                        value=row.get('ai_report', get_default_law_day_report()),
                        height=250
                    )
                    
                    btn_col1, btn_col2 = st.columns([1, 1])
                    with btn_col1:
                        if st.button("評価メモをデータベースに保存する", type="primary"):
                            try:
                                supabase.table("candidate_responses").update({"ai_report": report_text}).eq("id", row["id"]).execute()
                                st.success("レポートを更新保存しました")
                            except Exception as e:
                                st.error(f"更新エラー: {e}")
                    with btn_col2:
                        if st.button("データを削除する"):
                            try:
                                supabase.table("candidate_responses").delete().eq("id", row["id"]).execute()
                                st.warning("データを削除しました")
                                st.rerun()
                            except Exception as e:
                                st.error(f"削除エラー: {e}")

            else:
                st.info("現在、データベースに保存された回答データはありません。")
        except Exception as e:
            st.error(f"データ取得エラー: {e}")
    else:
        st.warning("Supabaseへの接続が確立されていません。")
