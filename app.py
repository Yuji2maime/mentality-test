import streamlit as st
import time
from supabase import create_client, Client

# ページ設定
st.set_page_config(page_title="思考・表現力セッション（当日用）", layout="wide")

# ==========================================
# 🔑 Supabase & 管理者設定
# ==========================================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "19700124")

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# セッション状態の初期化
if "page" not in st.session_state:
    st.session_state.page = "candidate"  # "candidate" or "admin"
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

# --- 1. 応募者用画面（当日回答用）---
if st.session_state.page == "candidate":
    st.title("思考・表現力セッション（当日入力）")
    st.write(
        "本日はご来社いただきありがとうございます。"
        "面接開始前に、以下のテーマに沿ってご自身の考えやエピソードをご入力ください。"
        "能力の優劣を評価するものではありませんので、リラックスしてお進みください。"
    )

    st.markdown("---")

    # 氏名入力
    candidate_name = st.text_input("お名前（氏名）を入力してください", placeholder="例：山田 太郎")

    # 当日テーマの表示
    st.subheader("【当日セッションテーマ】")
    st.info(
        "「これまでの仕事や生活の中で、最も工夫して乗り越えたエピソードについて、"
        "当時の状況やご自身の行動、そこから得られた学びを含めてご自由に記述してください。」"
    )

    # 記述エリア
    text_input = st.text_area(
        "ご自身の言葉で自由にご記述ください（文字数制限なし）",
        height=350,
        placeholder="ここにエピソードや考え方を入力してください..."
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("送信して完了する", type="primary"):
            if candidate_name.strip() and text_input.strip():
                # Supabaseにリアルタイム送信・保存
                data_to_insert = {
                    "name": candidate_name,
                    "text": text_input,
                    "types": [],
                    "sub_functions": [],
                    "notes": "",
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

    # パスワード認証チェック
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
        # DBから最新データをリアルタイム取得
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

                    st.markdown("---")
                    st.subheader("【認知特性・思考傾向分析】")

                    col_a, col_b = st.columns(2)
                    with col_a:
                        selected_types = st.multiselect(
                            "主機能・認知タイプ（該当するものすべて）",
                            ["Te型（効率・構造化）", "Ti型（論理・体系化）", "Fe型（調和・関係性）", "Fi型（価値観・内省）", "Se型（現実・実行）", "Ni型（直観・本質）"],
                            default=data.get("types") or [],
                            key=f"types_{record_id}"
                        )
                    with col_b:
                        selected_subs = st.multiselect(
                            "補助機能（複数認定）",
                            ["補助Te", "補助Ti", "補助Fe", "補助Fi", "補助Se", "補助Ne", "補助Si", "補助Ni"],
                            default=data.get("sub_functions") or [],
                            key=f"subs_{record_id}"
                        )

                    notes = st.text_area("採用・面接評価メモ（思考の癖、リスク、面接時確認事項など）", value=data.get("notes") or "", key=f"notes_{record_id}")

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

        # ==========================================
        # 📜 管理画面フッター（免責・管理責任注記）
        # ==========================================
        st.markdown("---")
        st.caption(
            "※本システムの分析結果は選考補助用の参考情報です。"
            "採用判断（合否・配属）および出力・印刷データの管理責任はすべて採用企業（採用担当者様）に帰属します。"
        )
