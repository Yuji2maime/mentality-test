import streamlit as st
import google.generativeai as genai
import datetime
import json
import os

st.set_page_config(page_title="AI統合型 認知特性テスト", layout="wide")

# セッション状態の初期化
if "submissions" not in st.session_state:
    st.session_state.submissions = []
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "applicant"

# サイドバーでAPIキー設定
st.sidebar.title("設定")
api_key = st.sidebar.text_input("Gemini API Key", type="password", help="APIキーを入れるとAI自動解析が有効化されます")

# 選択肢の定義
MAIN_TYPE_OPTIONS = ["Fe-Si", "Se-Ti", "Ne-Fi", "Ni-Te", "Si-Fe", "Ti-Ne", "Fi-Ne", "Te-Ni", "その他"]
AUX_FUNC_OPTIONS = ["外向感情(Fe)", "内向感覚(Si)", "外向直観(Ne)", "内向思考(Ti)", "外向感覚(Se)", "内向感情(Fi)", "外向思考(Te)", "内向直観(Ni)"]

def analyze_text_with_ai(text, key):
    """応募者の文章をGemini APIで自動解析する関数"""
    if not key:
        return [], [], "※APIキー未設定のため自動解析スキップ。手動で入力してください。"
    
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        prompt = f"""
        以下の応募者の記述文章を心理・認知特性の観点から分析してください。
        
        【応募者記述文章】
        {text}
        
        【分析指示】
        1. 主タイプ（該当するもの）：{MAIN_TYPE_OPTIONS} の中から選んでください。
        2. 補助機能（複数認定）：{AUX_FUNC_OPTIONS} の中から選んでください。
        3. 採用・評価メモ：認知の癖、職場でのリスク、主張の矛盾点などを150〜200文字程度で簡潔にまとめてください。
        
        【回答形式】
        必ず以下のJSON形式のみで出力してください（余計な解説は不要です）:
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
                st.subheader("【応募者の記述内容】")
                st.write(sub["text"])
                
                st.subheader("【AI拡張解析・ラベリングエリア】")
                col1, col2 = st.columns(2)
                
                with col1:
                    selected_mains = st.multiselect(
                        "主タイプ（該当するものすべて）",
                        options=MAIN_TYPE_OPTIONS,
                        default=sub["selected_mains"],
                        key=f"main_{sub['id']}"
                    )
                with col2:
                    selected_auxs = st.multiselect(
                        "補助機能（複数認定）",
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
                
                if st.button("評価を保存する", key=f"save_{sub['id']}"):
                    st.session_state.submissions[idx]["selected_mains"] = selected_mains
                    st.session_state.submissions[idx]["selected_auxs"] = selected_auxs
                    st.session_state.submissions[idx]["memo"] = memo
                    st.success(f"提出データ #{sub['id']} の評価を更新しました！")
