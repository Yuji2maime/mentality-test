import streamlit as st
import google.generativeai as genai
import datetime
import json
import os
import pandas as pd
st.set_page_config(page_title="AI統合型 認知特性テスト", layout="wide")

# セッション状態の初期化
if "submissions" not in st.session_state:
    st.session_state.submissions = []
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "applicant"

# SecretsからAPIキーを自動読み込み
api_key = st.secrets["GEMINI_API_KEY"]
# --- サイドバー機能：ホーム画面追加案内 & データ削除 ---
with st.sidebar:
    st.header("⚙️ アプリ機能")

    # 1. ホーム画面・デスクトップ追加案内
    with st.expander("📱 ホーム画面・デスクトップに追加"):
        st.markdown("""
        次回からワンタップで開けるよう、追加しておくと便利です。
        
        **【iPhone (Safari)】**
        1. 画面下の **共有ボタン（□に↑）** をタップ
        2. **「ホーム画面に追加」** を選択
        
        **【Android (Chrome)】**
        1. 画面右上の **「3点リーダー（⋮）」** をタップ
        2. **「ホーム画面に追加」** または **「アプリをインストール」** を選択
        
        **【パソコン (Chrome / Edge)】**
        1. 画面右上の **「3点リーダー（︙ または …）」** をクリック
        2. Chrome: **「保存して共有」** ＞ **「ショートカットを作成」**
        3. Edge: **「アプリ」** ＞ **「このサイトをアプリとしてインストール」**
        """)

    # 2. 保存データの削除機能
    st.subheader("🗑️ データ管理")
    if st.button("保存された履歴データをすべて削除", use_container_width=True):
        st.session_state.submissions = []
        st.success("すべての履歴データを削除しました！")
        st.rerun()
# --- データ管理エリアへのCSVダウンロード機能追加 ---
st.sidebar.markdown("---")
st.sidebar.subheader("📥 データダウンロード")

if "submissions" in st.session_state and st.session_state.submissions:
    # データをPandasのDataFrameに変換
    df = pd.DataFrame(st.session_state.submissions)

    # すべての列のカッコ [ ] や引用符 ' ' を綺麗に外す処理
    for col in df.columns:
        df[col] = df[col].apply(lambda x: ', '.join(x) if isinstance(x, list) else x)
        df[col] = df[col].apply(lambda x: str(x).replace("['", "").replace("']", "") if isinstance(x, str) and str(x).startswith("['") else x)

    # 綺麗にしたデータをCSVにエクスポート
    csv_data = df.to_csv(index=False).encode("utf-8-sig")
    st.sidebar.download_button(
        label="📄 履歴をCSVでダウンロード",
        data=csv_data,
        file_name="cognitive_test_submissions.csv",
        mime="text/csv",
    )# === ▼ ここから追加：検索メニューと表の表示 ▼ ===
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 データの検索・絞り込み")
    
    # サイドバー：キーワード検索
    search_query = st.sidebar.text_input("キーワード検索 (名前やメモなど)")
    
    # サイドバー：主タイプの絞り込み
    type_options = ["Fe-Si", "Se-Ti", "Ne-Fi", "Ni-Te", "Si-Fe", "Ti-Ne", "Fi-Ne", "Te-Ni", "その他"]
    selected_types = st.sidebar.multiselect("主タイプで絞り込み", type_options)
    
    # 絞り込みの実行
    filtered_df = df.copy()
    if search_query:
        mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_query, case=False, na=False)).any(axis=1)
        filtered_df = filtered_df[mask]
    if selected_types:
        if "主タイプ" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["主タイプ"].isin(selected_types)]
            
    # メイン画面：絞り込まれたデータを表として表示
    st.write("### 📋 提出データ一覧")
    st.dataframe(filtered_df, use_container_width=True)
    # === ▲ 追加ここまで ▲ ===
else:
    st.sidebar.info("ダウンロード可能なデータはありません。 ")
st.sidebar.markdown("---")
# 選択肢の定義
MAIN_TYPE_OPTIONS = ["Fe-Si", "Se-Ti", "Ne-Fi", "Ni-Te", "Si-Fe", "Ti-Ne", "Fi-Ne", "Te-Ni", "その他"]
AUX_FUNC_OPTIONS = ["外向感情(Fe)", "内向感覚(Si)", "外向直観(Ne)", "内向思考(Ti)", "外向感覚(Se)", "内向感情(Fi)", "外向思考(Te)", "内向直観(Ni)"]

def analyze_text_with_ai(text, key):
    """応募者の文章をGemini APIで自動解析する関数"""
    if not key:
        return [], [], "※APIキー未設定のため自動解析スキップ。手動で入力してください。"
    
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-3.6-flash")
        
        prompt = f"""
以下の応募者の記述文章を、プロの労務・人事評価者の視点から客観的かつ厳格に分析してください。

【応募者記述文章】
{text}

【分析指示】
1. 主タイプ（該当するもの）：{MAIN_TYPE_OPTIONS}の中から選んでください。
2. 補助機能（複数認定）：{AUX_FUNC_OPTIONS}の中から選んでください。
3. 採用・評価メモ：以下の観点を含め、客観的・事実ベースのトーン（150〜250文字程度）でまとめてください。
・組織適応性および規律・コンプライアンス意識
・認知の癖と職場における潜在リスク（対人・業務面の懸念点）
・面接時に深掘り・確認すべき具体的なポイント

【回答形式】
必ず以下のJSON形式のみで出力してください（余計な解説は不要です）：
{{
"main_types": ["選択したタイプ"],
"aux_funcs": ["選択した補助機能"],
"eval_memo": "生成された評価メモ文章"
}}
"""
        
        response = model.generate_content(prompt)
        res_text = response.text.strip()
        
        if "```json" in res_text:
            res_text = res_text.split("```json")[1].split("```")[0].strip()
        elif "```" in res_text:
            res_text = res_text.split("```")[1].split("```")[0].strip()
            
        data = json.loads(res_text)
        
        # 選択肢に存在する値のみフィルタリング
        valid_mains = [m for m in data.get("main_types", []) if m in MAIN_TYPE_OPTIONS]
        valid_auxs = [a for a in data.get("aux_funcs", []) if a in AUX_FUNC_OPTIONS]
        
        return valid_mains, valid_auxs, data.get("eval_memo", "")
    except Exception as e:
        return [], [], f"AI自動解析エラー: {str(e)}"

# 画面切り替えボタン
col_nav1, col_nav2 = st.columns([1, 1])
with col_nav1:
    if st.button("応募者用画面を表示"):
        st.session_state.view_mode = "applicant"
        st.rerun()
with col_nav2:
    if st.button("採用側（管理）画面へ切り替え"):
        st.session_state.view_mode = "admin"
        st.rerun()

st.divider()

# 1. 応募者画面
if st.session_state.view_mode == "applicant":
    st.title("思考・表現力セッション")
    st.write("政治・経済、趣味、恋愛など、あなたが今最も関心のあることや語りたいテーマについて、制限時間内に自由に記述してください。納得した時点でいつでも終了できます。")
    
    user_input = st.text_area("記述欄", height=200, key="applicant_text")
    
    if st.button("これで完了する（終了）", type="primary"):
        if user_input.strip():
            with st.spinner("AIが回答内容を事前解析中..."):
                mains, auxs, memo = analyze_text_with_ai(user_input, api_key)
            
            new_data = {
                "id": len(st.session_state.submissions) + 1,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "text": user_input,
                "selected_mains": mains,
                "selected_auxs": auxs,
                "memo": memo
            }
            st.session_state.submissions.append(new_data)
            st.success("送信が完了しました。ご協力ありがとうございました。")
        else:
            st.warning("文章を入力してから送信してください。")

# 2. 管理者画面
else:
    st.title("採用管理画面")
    
    # ★ 免責・運用原則テキスト
    st.warning("※本解析結果は思考傾向の示唆に留まる補助情報であり、適正な採用・配属を保証するものではありません。最終的な採用・配属決定は面接や総合評価に基づき、担当者ご自身の責任で行ってください。")
    
    if not st.session_state.submissions:
        st.info("まだ提出されたデータはありません。")
    else:
       for idx, sub in enumerate(st.session_state.submissions):
        with st.expander(f"提出データ #{sub['id']} (日時: {sub['timestamp']})", expanded=True):
            # --- 追加：個別削除ボタン ---
            if st.button("🗑️ このデータを削除", key=f"del_btn_{sub['id']}"):
                st.session_state.submissions.pop(idx)
                st.rerun()
            # ----------------------------
            
            st.subheader("【応募者の記述内容】")
            st.write(sub["text"])
            
            st.subheader("【AI拡張解析・ラベリングエリア】")
            col1, col2 = st.columns(2)
            
            with col1:
                selected_mains = st.multiselect(
                    "主タイプ (該当するものすべて) ",
                    options=MAIN_TYPE_OPTIONS,
                    default=sub["selected_mains"],
                    key=f"main_{sub['id']}"
                )
            with col2:
                selected_auxs = st.multiselect(
                    "補助機能 (複数認定) ",
                    options=AUX_FUNC_OPTIONS,
                    default=sub["selected_auxs"],
                    key=f"aux_{sub['id']}"
                )
                
                memo = st.text_area(
                    "採用・評価メモ（認知の癖、リスク、矛盾点など）",
                    value=sub["memo"],
                    height=120,
                    key=f"memo_{sub['id']}"
                )
                
            if st.button("💾 評価を保存する", key=f'save_{sub["id"]}', type="primary"):
                    # 画面中央に風船を飛ばす！🎈
                    st.balloons()
                    
                    # 保存データを更新
                    st.session_state.submissions[idx]["selected_mains"] = selected_mains
                    st.session_state.submissions[idx]["selected_auxs"] = selected_auxs
                    st.session_state.submissions[idx]["memo"] = memo
                    
                    # 成功メッセージを表示
                    st.success(f"🎉 提出データ #{sub['id']} の評価を保存・更新しました！")              
# === ここから下を新しく追加 ===
st.markdown("---")
st.subheader("💾 データのダウンロード")

# ダウンロード用のCSVデータを作成
csv_data = "応募者ID,主タイプ,補助機能,採用・評価メモ\n"
for sub in st.session_state.submissions:
    sub_id = str(sub.get('id', ''))
    mains = "、".join(sub.get('selected_mains', []))
    auxs = "、".join(sub.get('selected_auxs', []))
    memo = str(sub.get('memo', '')).replace('"', '""')
    csv_data += f'"{sub_id}","{mains}","{auxs}","{memo}"\n'

st.download_button(
    label="📥 評価結果をCSVでダウンロード",
    data=csv_data.encode("utf-8-sig"),
    file_name="evaluation_results.csv",
    mime="text/csv"
)
# === ここまで ===
st.markdown("---")
if st.button("🔄 次の人のテストを始める（画面リセット）"):
    # 保存済みのCSVデータ(submissions)以外をクリアする
    for key in list(st.session_state.keys()):
        if key != "submissions":
            del st.session_state[key]
    st.rerun()
