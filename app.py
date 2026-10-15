import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import pandas as pd

st.set_page_config(
    page_title="AI統合型 認知特性テスト - 管理画面", 
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

def main():
    st.title("AI統合型 認知特性テスト - 管理画面")
    st.markdown("---")
    
    # サイドバー
    st.sidebar.header("メニュー")
    menu = st.sidebar.selectbox("表示モード", ["受検者データ一覧", "新規データ登録・編集"])
    
    if st.sidebar.button("🔄 データを再読み込み"):
        st.cache_resource.clear()
        st.rerun()

    # データ読み込み
    df = load_data()

    if menu == "受検者データ一覧":
        st.subheader("📋 登録済み受検者データ一覧")
        
        if df.empty:
            st.info("現在、スプレッドシートにデータが登録されていません。2行目以降にデータを入力してください。")
        else:
            st.success(f"合計 {len(df)} 件のデータを取得しました。")
            # テーブル（データフレーム）として綺麗に表示
            st.dataframe(df, use_container_width=True)
            
            # 詳細確認セクション
            st.markdown("### 🔍 個別詳細ビュー")
            selected_row = st.selectbox("確認する受検者を選択", df.index, format_func=lambda x: f"{df.loc[x, '氏名'] if '氏名' in df.columns else f'行 {x+1}'}")
            
            if selected_row is not None and not df.empty:
                row_data = df.loc[selected_row]
                col1, col2 = st.columns(2)
                with col1:
                    for col_name in df.columns[:5]:
                        st.metric(label=col_name, value=row_data.get(col_name, "-"))
                with col2:
                    st.write("#### 📊 スコア・詳細情報")
                    st.json(row_data.to_dict())

    elif menu == "新規データ登録・編集":
        st.subheader("✍️ データ管理について")
        st.info("現在はスプレッドシート（Googleスプレッドシート）を直接編集してデータを追加・更新する運用になっています。スプレッドシート側でデータを編集後、左側メニューの「データを再読み込み」ボタンを押してください。")
        
        if not df.empty:
            st.write("現在のスプレッドシート内容プレビュー:")
            st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()
