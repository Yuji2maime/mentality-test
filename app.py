import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

st.set_page_config(
    page_title="AI統合型 認知特性テスト システム", 
    layout="wide"
)

TARGET_SPREADSHEET_ID = "1hkFRa9v6wbGqmT1RAKvm9EJhuEIRS-R9YAELThPJRW0"

# Gemini APIの設定（最新モデル gemini-3.8-flash を指定）
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    pass

@st.cache_resource
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    raw_creds = st.secrets["gcp_credentials"]
    if isinstance(raw_creds, str):
        creds_dict = json.loads(raw_creds)
    else:
        creds_dict = dict(raw_creds)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def load_data():
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(TARGET_SPREADSHEET_ID.strip())
        sheet = spreadsheet.get_worksheet(0)
        rows = sheet.get_all_values()
        
        if not rows or len(rows) <= 1:
            return pd.DataFrame()
            
        header = rows[0]
        data = rows[1:]
        df = pd.DataFrame(data, columns=header[:len(data[0])])
        return df
    except Exception as e:
        st.error(f"データの読み込み中にエラーが発生しました: {e}")
        return pd.DataFrame()

def append_row_to_sheet(row_data):
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(TARGET_SPREADSHEET_ID.strip())
        sheet = spreadsheet.get_worksheet(0)
        sheet.append_row(row_data)
        return True
    except Exception as e:
        st.error(f"データ保存中にエラーが発生しました: {e}")
        return False

def delete_row_from_sheet(sheet_row_index):
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(TARGET_SPREADSHEET_ID.strip())
        sheet = spreadsheet.get_worksheet(0)
        sheet.delete_rows(sheet_row_index)
        return True
    except Exception as e:
        st.error(f"削除中にエラーが発生しました: {e}")
        return False

def clear_all_data():
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(TARGET_SPREADSHEET_ID.strip())
        sheet = spreadsheet.get_worksheet(0)
        rows = sheet.get_all_values()
        if len(rows) > 1:
            sheet.batch_clear([f"A2:Z{len(rows)}"])
        return True
    except Exception as e:
        st.error(f"一括クリア中にエラーが発生しました: {e}")
        return False

def analyze_answer_with_ai(answer_text):
    """
    応募者の解答をGemini APIで自動分析し、特性・メモ・5軸スコアを算出する
    """
    try:
        # モデル名を最新の gemini-3.8-flash に変更
        model = genai.GenerativeModel("gemini-3.8-flash")
        prompt = f"""
あなたは労働管理・組織人事の専門家であり、AI認知特性アナリストです。
以下の応募者の解答テキストを分析し、JSON形式で以下の項目を評価・算出してください。

評価軸（0〜100点満点の整数スコア）：
1. 論理・合理性 (score1)
2. 直観・洞察 (score2)
3. 目的遂行力 (score3)
4. 対人関係 (score4)
5. 柔軟・適応力 (score5)

その他の項目：
- main_trait: メイン特性（例：「Te-Ni」「知性の盾系」「論理推進型」など、思考スタイルの傾向を表す簡潔な分類）
- sub_trait: サブ特性（例：「外向思考(Te)」「内向直観(Ni)」など）
- memo: メモ・所見（応募者の強みや面接・労務管理で注目すべきポイントのAI分析コメント、150〜200文字程度）

応募者の解答:
{answer_text}

出力は必ず以下の純粋なJSONフォーマットのみで行ってください（Markdownの ```json や ``` などの記号は一切含めず、中括弧 {{ }} から始まる文字列のみを出力してください）：
{{
  "main_trait": "...",
  "sub_trait": "...",
  "memo": "...",
  "score1": 75,
  "score2": 70,
  "score3": 80,
  "score4": 65,
  "score5": 85
}}
"""
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        data = json.loads(text)
        return data
    except Exception as e:
        return {
            "main_trait": "標準特性",
            "sub_trait": "バランス型",
            "memo": f"AI自動分析エラー: {str(e)}",
            "score1": 50,
            "score2": 50,
            "score3": 50,
            "score4": 50,
            "score5": 50
        }

def main():
    st.title("AI統合型 認知特性テスト システム")
    st.markdown("---")
    
    st.sidebar.header("メニュー")
    mode = st.sidebar.selectbox("画面モード切替", ["📝 応募者用入力画面", "📊 管理・閲覧・削除画面"])
    
    if st.sidebar.button("🔄 データを再読み込み"):
        st.cache_resource.clear()
        st.rerun()

    if mode == "📝 応募者用入力画面":
        st.subheader("📝 認知特性テスト 回答フォーム")
        
        st.markdown(
            """
            ### 📌 【テストの目的とテーマについて】
            本テストは、組織における個人の認知特性や思考スタイルを多角的に把握し、より良いチームづくりや適材適所の環境を整えるためのものです。  
            以下のテーマについて、あなたの考えや直感するアプローチを自由にご記入ください。
            
            **【ご記入いただくテーマ】**  
            > 「これまでのご経験の中で、不確実性の高い課題や困難な状況に直面した際、あなたはどのような思考プロセスで状況を整理し、周囲と協調しながら推進されましたか？具体的なスタンスや判断基準を教えてください。」
            """
        )
        st.markdown("---")
        
        with st.form("candidate_form"):
            input_name = st.text_input("お名前（氏名）", placeholder="例: 山田 太郎")
            input_answer = st.text_area("解答欄（あなたの考えや回答をご記入ください）", placeholder="ここに回答を入力してください...", height=200)
            
            st.markdown("")
            submitted = st.form_submit_button("回答を提出する", type="primary")
            
            if submitted:
                if not input_name.strip():
                    st.warning("お名前（氏名）を入力してください。")
                elif not input_answer.strip():
                    st.warning("解答欄に内容を入力してください。")
                else:
                    with st.spinner("🤖 AIが解答を分析し、特性とスコアを自動生成しています..."):
                        ai_result = analyze_answer_with_ai(input_answer.strip())
                        
                    # スプレッドシートの列順（ID, 氏名, メイン特性, サブ特性,メモ, スコア1〜5）に完全に一致させる
                    row_data = [
                        "",
                        input_name.strip(),
                        ai_result.get("main_trait", ""),
                        ai_result.get("sub_trait", ""),
                        ai_result.get("memo", ""),
                        str(ai_result.get("score1", 50)),
                        str(ai_result.get("score2", 50)),
                        str(ai_result.get("score3", 50)),
                        str(ai_result.get("score4", 50)),
                        str(ai_result.get("score5", 50))
                    ]
                    if append_row_to_sheet(row_data):
                        st.success("🎉 テストの回答を正常に提出し、AIによる自動分析を完了しました！ご協力ありがとうございました。")
                        st.markdown("ウィンドウを閉じていただいて構いません。")
                        st.balloons()

    elif mode == "📊 管理・閲覧・削除画面":
        st.subheader("🔐 管理者認証")
        
        input_pass = st.text_input("管理者パスワードを入力してください", type="password")
        
        if input_pass == "7777":
            st.success("認証に成功しました。")
            st.markdown("---")
            
            df = load_data()
            st.subheader("📋 登録済み受検者データ一覧 & レーダーチャート分析")
            
            if df.empty:
                st.info("現在、スプレッドシートにデータが登録されていません。")
            else:
                st.success(f"合計 {len(df)} 件のデータを取得しました。")
                st.dataframe(df, use_container_width=True)
                
                st.markdown("### 🔍 個別詳細ビュー & レーダーチャート & 削除")
                selected_row = st.selectbox("確認・削除する受検者を選択", df.index, format_func=lambda x: f"{df.loc[x, '氏名'] if '氏名' in df.columns else f'行 {x+1}'}")
                
                if selected_row is not None and not df.empty:
                    row_data = df.loc[selected_row]
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("#### 👤 受検者情報・AI所見")
                        for col_name in df.columns[:5]:
                            st.metric(label=col_name, value=str(row_data.get(col_name, "-")))
                        
                        st.markdown("---")
                        if st.button("🗑️ この受検者データを削除する", type="secondary"):
                            sheet_row_idx = int(selected_row) + 2
                            if delete_row_from_sheet(sheet_row_idx):
                                st.success("データを削除しました！")
                                st.cache_resource.clear()
                                st.rerun()

                    with col2:
                        st.write("#### 📊 スコア・レーダーチャート")
                        
                        score_cols = [c for c in df.columns if c in ["論理・合理性", "直観・洞察", "目的遂行力", "対人関係", "柔軟・適応力"]]
                        if not score_cols and len(df.columns) >= 10:
                            score_cols = df.columns
                        
                        scores = []
                        categories = []
                        for col in score_cols:
                            val = row_data.get(col, 0)
                            try:
                                num_val = float(val) if val != "" else 0.0
                            except ValueError:
                                num_val = 0.0
                            scores.append(num_val)
                            categories.append(col)
                        
                        if scores and sum(scores) > 0:
                            fig = go.Figure(data=go.Scatterpolar(
                              r=scores + [scores[0]],
                              theta=categories + [categories[0]],
                              fill='toself'
                            ))
                            fig.update_layout(
                              polar=dict(
                                radialaxis=dict(
                                  visible=True,
                                  range=[0, 100]
                                )),
                              showlegend=False,
                              margin=dict(l=20, r=20, t=20, b=20),
                              height=300
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("※ スコアの数値が入力されていないためチャートを表示できません。")
                        
                        st.write("#### 📄 詳細データ (JSON)")
                        st.json(row_data.to_dict())
                
                st.markdown("---")
                with st.expander("⚙️ 高度なデータ管理（一括削除）"):
                    st.warning("⚠️ 注意: 以下のボタンを押すと、スプレッドシートの全受検者データがクリアされます。")
                    if st.button("🔥 すべてのデータを一括クリアする", type="primary"):
                        if clear_all_data():
                            st.success("すべてのデータをクリアしました！")
                            st.cache_resource.clear()
                            st.rerun()
        elif input_pass != "":
            st.error("パスワードが間違っています。")

if __name__ == "__main__":
    main()
