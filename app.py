import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="AI統合型 認知特性テスト システム", 
    layout="wide"
)

TARGET_SPREADSHEET_ID = "1hkFRa9v6wbGqmT1RAKvm9EJhuEIRS-R9YAELThPJRW0"

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

def main():
    st.title("AI統合型 認知特性テスト システム")
    st.markdown("---")
    
    # サイドバーでモード切替
    st.sidebar.header("メニュー")
    mode = st.sidebar.selectbox("画面モード切替", ["📝 応募者用入力画面", "📊 管理・閲覧・削除画面"])
    
    if st.sidebar.button("🔄 データを再読み込み"):
        st.cache_resource.clear()
        st.rerun()

    if mode == "📝 応募者用入力画面":
        st.subheader("📝 認知特性テスト 回答フォーム")
        
        # 普遍的な固定テーマの案内文
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
                    # スプレッドシートの列構成（ID, 氏名, 解答, メイン特性, サブ特性, メモ, スコア1〜5）
                    row_data = [
                        "",
                        input_name.strip(),
                        input_answer.strip(),
                        "",
                        "",
                        "",
                        "0",
                        "0",
                        "0",
                        "0",
                        "0"
                    ]
                    if append_row_to_sheet(row_data):
                        st.success("🎉 テストの回答を正常に提出しました！ご協力ありがとうございました。")
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
                        st.write("#### 👤 受検者情報・解答")
                        for col_name in df.columns[:6]:
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
                        if not score_cols and len(df.columns) >= 11:
                            score_cols = df.columns[6:11]
                        
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
                            st.info("※ スコアの数値が入力されていないためチャートを表示できません。（スプレッドシート側でスコアを設定してください）")
                        
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
