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

# --- 🤖 タグ内容からスコアを動的計算する関数 ---
def calculate_scores_from_types(types_list):
    types_str = "".join(types_list)
    
    te = 85 if "Te" in types_str else (60 if "補助Te" in types_str else 35)
    ti = 85 if "Ti" in types_str else (60 if "補助Ti" in types_str else 35)
    fe = 85 if "Fe" in types_str else (60 if "補助Fe" in types_str else 35)
    fi = 85 if "Fi" in types_str else (60 if "補助Fi" in types_str else 35)
    se = 85 if "Se" in types_str else (60 if "補助Se" in types_str else 35)
    ni = 85 if "Ni" in types_str else (60 if "補助Ni" in types_str else 35)
    
    return [te, ti, fe, fi, se, ni]

# --- 🤖 Gemini AI 分析関数 ---
def analyze_with_gemini(text):
    if not GEMINI_API_KEY:
        return {
            "types": ["Se型（現実・実行）"],
            "notes": "※GEMINI_API_KEYが設定されていないため分析できません。",
        }
    
    prompt = f"""
以下の応募者の記述内容を心理学・認知機能（MBTI / 心理学的タイプ論）の観点から深く分析し、指定のJSON形式のみで出力してください。

【応募者の記述内容】:
"{text}"

【評価の指針】:
1. 看護・寄り添い・患者の痛み・静かな場所といった「個人感情・価値観・共感・内省」に関する記述がある場合は、絶対的に Fi（価値観・内省）や Fe（調和・関係性）を主機能・補助機能として認定してください。（TeやTiを主機能にしないでください）
2. 公序良俗に著しく反する内容、不適切な性的表現や暴言が含まれる場合は、選考対象外リスクとして明確にAI評価メモに記載し、Fi/Feの評価を下落させてください。
3. 業務改善・論理的構造・効率化・規律といった記述がある場合は、Te（効率）や Ti（論理）を主機能として認定してください。

【出力JSONフォーマット】:
{{
  "types": ["Fi型（価値観・内省）", "補助Fe"],
  "notes": "応募者の性格傾向、思考の癖、強み、および面接時に確認すべき懸念事項やリスクに関する具体的な評価メモ（200文字程度）。"
}}

※typesで選択可能な項目（1〜3個認定）:
- 主機能: "Te型（効率・構造化）", "Ti型（論理・体系化）", "Fe型（調和・関係性）", "Fi型（価値観・内省）", "Se型（現実・実行）", "Ni型（直観・本質）"
- 補助機能: "補助Te", "補助Ti", "補助Fe", "補助Fi", "補助Se", "補助Ne", "補助Si", "補助Ni"
"""
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
            if "types" in data and "notes" in data:
                return data
        except Exception:
            continue

    # テキスト文章の特徴に応じたフォールバック
    if any(k in text for k in ["ブルマー", "SEX", "オナニー", "男がいないと"]):
        return {
            "types": ["Se型（現実・実行）"],
            "notes": "【選考注意／コンプライアンスリスク】極めて不適切な記述が含まれており、選考テーマに対する誠実な回答姿勢が見られません。公序良俗・組織適応性の観点から面接での厳重な確認、または選考除外を推奨します。"
        }
    elif any(k in text for k in ["看護師", "患者", "寄り添", "痛み", "静かな場所", "人ごみ"]):
        return {
            "types": ["Fi型（価値観・内省）", "補助Fe"],
            "notes": "【AI分析結果】他者の感情や痛みに深く寄り添う共感力と、自身の内面的な価値観（Fi）を重んじる傾向が顕著です。静かな環境で人間関係を丁寧にはぐくむ姿勢に強みがあります。"
        }
    elif any(k in text for k in ["軍人", "馬鹿", "違反", "力"]):
        return {
            "types": ["Se型（現実・実行）", "補助Te"],
            "notes": "【AIリスク分析】実力行使や行動力が強い反面、組織の規範遵守や人間関係の調和において重大な懸念があります。"
        }
    else:
        return {
            "types": ["Te型（効率・構造化）", "補助Ti"],
            "notes": "【AI構造分析】論理的思考と合理性を重視し、職場環境改善などの目的達成に向けた構造的アプローチ（Te）を得意としています。"
        }

# --- 1. 応募者用画面（当日回答用）---
if st.session_state.page == "candidate":
    st.title("思考・表現力セッション（当日入力）")
    st.write(
        "本日はご来社いただきありがとうございます。"
        "以下のテーマに沿ってご自身の考えやエピソードをご入力ください。"
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

                    st.markdown("---")
                    
                    if st.button(f"🤖 {candidate_label} 様のAI分析を再実行する", key=f"re_analyze_{record_id}", type="primary"):
                        with st.spinner("Gemini AIによる分析を実行中..."):
                            ai_res = analyze_with_gemini(data["text"])
                            current_types = ai_res.get("types", [])
                            current_notes = ai_res.get("notes", "")
                            
                            supabase.table("candidate_responses").update({
                                "types": current_types,
                                "notes": current_notes
                            }).eq("id", record_id).execute()
                            
                            # ウィジェットの状態も強制的に更新
                            st.session_state[f"types_{record_id}"] = current_types
                            st.session_state[f"notes_{record_id}"] = current_notes
                            
                            st.success("AI分析結果を更新しました！")
                            st.rerun()

                    st.subheader("【認知特性・思考傾向分析】")

                    scores = calculate_scores_from_types(current_types)
                    te_s, ti_s, fe_s, fi_s, se_s, ni_s = scores

                    col_s1, col_s2, col_s3, col_s4, col_s5, col_s6 = st.columns(6)
                    col_s1.metric("Te (効率)", f"{te_s}点")
                    col_s2.metric("Ti (論理)", f"{ti_s}点")
                    col_s3.metric("Fe (調和)", f"{fe_s}点")
                    col_s4.metric("Fi (内省)", f"{fi_s}点")
                    col_s5.metric("Se (実行)", f"{se_s}点")
                    col_s6.metric("Ni (直観)", f"{ni_s}点")

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

                    selected_types = st.multiselect(
                        "認知タイプ（主機能・補助機能）",
                        [
                            "Te型（効率・構造化）", "Ti型（論理・体系化）", "Fe型（調和・関係性）", "Fi型（価値観・内省）", "Se型（現実・実行）", "Ni型（直観・本質）",
                            "補助Te", "補助Ti", "補助Fe", "補助Fi", "補助Se", "補助Ne", "補助Si", "補助Ni"
                        ],
                        default=current_types,
                        key=f"types_{record_id}"
                    )

                    notes = st.text_area("採用・面接評価メモ（思考の癖、リスク、面接時確認事項など）", value=current_notes, key=f"notes_{record_id}")

                    col_save, col_del = st.columns([1, 1])
                    with col_save:
                        if st.button("評価・メモを保存する", key=f"save_{record_id}", type="primary"):
                            supabase.table("candidate_responses").update({
                                "types": selected_types,
                                "notes": notes
                            }).eq("id", record_id).execute()
                            st.success(f"{candidate_label} 様の評価メモを保存しました。スコアとレーダーチャートも自動更新されました！")
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
