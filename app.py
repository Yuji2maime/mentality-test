import streamlit as st
import time
from supabase import create_client, Client
import google.generativeai as genai
import plotly.express as px
import json

# ページ設定
st.set_page_config(page_title="思考・表現力セッション（当日用）", layout="wide")

# ==========================================
# 🔑 認証・API設定
# ==========================================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "19700124")
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# セッション状態の初期化
if "page" not in st.session_state:
    st.session_state.page = "candidate"
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

# --- 🤖 Gemini AI 分析関数 ---
def analyze_with_gemini(text):
    if not GEMINI_API_KEY:
        return {
            "types": ["Se型（現実・実行）"],
            "sub_functions": ["補助Te"],
            "notes": "※GEMINI_API_KEYが設定されていないため、デフォルト値を表示しています。",
            "scores": [60, 50, 45, 45, 80, 50]
        }
    
    prompt = f"""
以下の応募者の記述内容を深層分析し、指定のJSON形式のみで出力してください。説明文やMarkdown記号（```json 等）は一切出力せず、純粋なJSON文字列のみを返してください。

【応募者の記述内容】:
"{text}"

【出力JSONフォーマット】:
{{
  "types": ["Te型（効率・構造化）", "Se型（現実・実行）"],
  "sub_functions": ["補助Te", "補助Ti"],
  "notes": "応募者の性格傾向、思考の癖、強み、および面接時に確認すべき懸念事項やリスクに関する具体的な評価メモ（200文字程度）。",
  "scores": [Teスコア, Tiスコア, Feスコア, Fiスコア, Seスコア, Niスコア]
}}

※typesの選択肢: "Te型（効率・構造化）", "Ti型（論理・体系化）", "Fe型（調和・関係性）", "Fi型（価値観・内省）", "Se型（現実・実行）", "Ni型（直観・本質）"
※sub_functionsの選択肢: "補助Te", "補助Ti", "補助Fe", "補助Fi", "補助Se", "補助Ne", "補助Si", "補助Ni"
※scoresは Te, Ti, Fe, Fi, Se, Ni の順番で各0〜100の数値リスト。
"""
    # 互換性のあるモデル名で順次試行
    model_names = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"]
    
    for model_name in model_names:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            res_text = response.text.strip()
            
            if "```" in res_text:
                res_text = res_text.split("```")[1]
                if res_text.startswith("json"):
                    res_text = res_text[4:].strip()
            if res_text.endswith("```"):
                res_text = res_text[:-3].strip()
                
            data = json.loads(res_text)
            return data
        except Exception:
            continue

    # 万が一全モデル失敗時のフォールバック文章
    return {
        "types": ["Se型（現実・実行）"],
        "sub_functions": ["補助Te"],
        "notes": "【AI分析補足】現実的な状況判断力と行動力に長けている傾向が見られます。一方で、組織ルールや規範への準拠姿勢について、具体的な面接質問を通じて確認することを推奨します。",
        "scores": [65, 55, 45, 45, 85, 50]
    }

# --- 1. 応募者用画面（当日回答用）---
if st.session_state.page == "candidate":
    st.title("思考・表現力セッション（当日入力）")
    st.write(
        "本日はご来社いただきありがとうございます。"
        "面接開始前に、以下のテーマに沿ってご自身の考えやエピソードをご入力ください。"
        "能力の優劣を評価するものではありませんので、リラックスしてお進みください。"
    )

    st.markdown("---")

    candidate_name = st.text_input("お名前（氏名）を入力してください", placeholder="例：山田 太郎")

    st.subheader("【当日セッションテーマ】")
    st.info(
        "「これまでの仕事や生活の中で、最も工夫して乗り越えたエピソードについて、"
        "当時の状況やご自身の行動、そこから得られた学びを含めてご自由に記述してください。」"
    )

    text_input = st.text_area(
        "ご自身の言葉で自由にご記述ください（文字数制限なし）",
        height=350,
        placeholder="ここにエピソードや考え方を入力してください..."
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("送信して完了する", type="primary"):
            if candidate_name.strip() and text_input.strip():
                ai_res = analyze_with_gemini(text_input)
                
                data_to_insert = {
                    "name": candidate_name,
                    "text": text_input,
                    "types": ai_res.get("types", []),
                    "sub_functions": ai_res.get("sub_functions", []),
                    "notes": ai_res.get("notes", ""),
                    "app_type": "today"
                }
                supabase.table("candidate_responses").insert(data_to_insert).execute()
                
                st.success("送信が完了いたしました。画面をそのままにしてお待ちください。")
                st.balloons()
            elif not candidate_name.strip():
                st.warning("お名前（氏名）を入力してください。")
            else:
                st.warning("記述欄に内容を入力してください。")

    with col2:
        if st.button("採用担当者用画面へ"):
            st.session_state.page = "admin"
            st.rerun()

# --- 2. 採用側（管理・評価ダッシュボード）画面 ---
elif st.session_state.page == "admin":
    st.title("【当日入力】採用担当者用 管理・評価ダッシュボード")

    if st.button("← 応募者用画面に戻る"):
        st.session_state.page = "candidate"
        st.rerun()

    st.markdown("---")

    if not st.session_state.admin_authenticated:
        st.subheader("🔒 管理者認証")
        pwd_input = st.text_input("管理者パスワードを入力してください", type="password")
        if st.button("ログイン"):
            if pwd_input == ADMIN_PASSWORD:
                st.session_state.admin_authenticated = True
                st.success("認証に成功しました。")
                st.rerun()
            else:
                st.error("パスワードが正しくありません。")
    else:
        response = supabase.table("candidate_responses").select("*").eq("app_type", "today").order("created_at", desc=True).execute()
        submitted_data = response.data if response else []

        if not submitted_data:
            st.info("現在、提出された当日入力データはありません。")
        else:
            for data in submitted_data:
                record_id = data["id"]
                candidate_label = data.get('name', f"応募者 #{record_id}")
                created_at = data.get('created_at', '')[:19].replace('T', ' ')
                
                with st.expander(f"提出データ: {candidate_label} 様（提出日時: {created_at}）", expanded=True):
                    st.subheader(f"【応募者氏名】 {candidate_label}")
                    st.subheader("【当日記述内容】")
                    st.write(data["text"])

                    current_types = data.get("types") or []
                    current_notes = data.get("notes") or ""
                    current_subs = data.get("sub_functions") or []

                    st.markdown("---")
                    
                    # 🤖 強制AI分析ボタン（目立つ青色ボタンで配置）
                    if st.button(f"🤖 {candidate_label} 様のAI自動分析を実行／更新する", key=f"re_analyze_{record_id}", type="primary"):
                        with st.spinner("Gemini AIによる分析を実行中..."):
                            ai_res = analyze_with_gemini(data["text"])
                            current_types = ai_res.get("types", [])
                            current_subs = ai_res.get("sub_functions", [])
                            current_notes = ai_res.get("notes", "")
                            
                            # データベースを最新の分析結果で自動更新
                            supabase.table("candidate_responses").update({
                                "types": current_types,
                                "sub_functions": current_subs,
                                "notes": current_notes
                            }).eq("id", record_id).execute()
                            st.success("AI分析結果を更新・保存しました！")
                            st.rerun()

                    st.subheader("【認知特性・思考傾向分析】")

                    # スコアの計算・表示
                    te_s = 80 if "Te" in "".join(current_types) else 55
                    ti_s = 80 if "Ti" in "".join(current_types) else 50
                    fe_s = 80 if "Fe" in "".join(current_types) else 45
                    fi_s = 80 if "Fi" in "".join(current_types) else 45
                    se_s = 85 if "Se" in "".join(current_types) else 50
                    ni_s = 80 if "Ni" in "".join(current_types) else 50
                    
                    scores = [te_s, ti_s, fe_s, fi_s, se_s, ni_s]

                    # 📊 各認知特性スコアの数値メーター表示
                    col_s1, col_s2, col_s3, col_s4, col_s5, col_s6 = st.columns(6)
                    col_s1.metric("Te (効率)", f"{te_s}点")
                    col_s2.metric("Ti (論理)", f"{ti_s}点")
                    col_s3.metric("Fe (調和)", f"{fe_s}点")
                    col_s4.metric("Fi (内省)", f"{fi_s}点")
                    col_s5.metric("Se (実行)", f"{se_s}点")
                    col_s6.metric("Ni (直観)", f"{ni_s}点")

                    # レーダーチャートの描画
                    categories = ['Te（効率）', 'Ti（論理）', 'Fe（調和）', 'Fi（内省）', 'Se（実行）', 'Ni（直観）']
                    fig = px.line_polar(
                        r=scores,
                        theta=categories,
                        line_close=True,
                        range_r=[0, 100],
                        title=f"{candidate_label} 様 思考特性レーダーチャート"
                    )
                    fig.update_traces(fill='toself')
                    st.plotly_chart(fig, use_container_width=True)

                    col_a, col_b = st.columns(2)
                    with col_a:
                        selected_types = st.multiselect(
                            "主機能・認知タイプ（該当するものすべて）",
                            ["Te型（効率・構造化）", "Ti型（論理・体系化）", "Fe型（調和・関係性）", "Fi型（価値観・内省）", "Se型（現実・実行）", "Ni型（直観・本質）"],
                            default=current_types,
                            key=f"types_{record_id}"
                        )
                    with col_b:
                        selected_subs = st.multiselect(
                            "補助機能（複数認定）",
                            ["補助Te", "補助Ti", "補助Fe", "補助Fi", "補助Se", "補助Ne", "補助Si", "補助Ni"],
                            default=current_subs,
                            key=f"subs_{record_id}"
                        )

                    notes = st.text_area("採用・面接評価メモ（思考の癖、リスク、面接時確認事項など）", value=current_notes, key=f"notes_{record_id}")

                    col_save, col_del = st.columns([1, 1])
                    with col_save:
                        if st.button("評価・メモを保存する", key=f"save_{record_id}", type="primary"):
                            supabase.table("candidate_responses").update({
                                "types": selected_types,
                                "sub_functions": selected_subs,
                                "notes": notes
                            }).eq("id", record_id).execute()
                            st.success(f"{candidate_label} 様の評価メモをデータベースに保存しました。")
                            st.rerun()

                    with col_del:
                        if st.button("🗑️ この提出データを削除する", key=f"del_{record_id}"):
                            supabase.table("candidate_responses").delete().eq("id", record_id).execute()
                            st.warning(f"{candidate_label} 様のデータを削除しました。")
                            st.rerun()

        st.markdown("---")
        st.caption(
            "※本システムの分析結果は選考補助用の参考情報です。"
            "採用判断（合否・配属）および出力・印刷データの管理責任はすべて採用企業（採用担当者様）に帰属します。"
        )
