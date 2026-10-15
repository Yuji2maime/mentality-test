import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# ページ設定
st.set_page_config(page_title="AI統合型 認知特性テスト - 管理画面", layout="wide")

# スプレッドシートID
TARGET_SPREADSHEET_ID = "1hkFRa9v6wbGqmT1RAKvm9EJhuEiR9-R9YAELThPJRW0"

def fetch_from_spreadsheet():
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # StreamlitのSecretsから認証情報を取得
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        else:
            st.error("Streamlit Secretsに 'gcp_service_account' が設定されていません。")
            return []
            
        client = gspread.authorize(creds)
        
        # スプレッドシートを開く（IDで指定し、一番左のシートを取得）
        spreadsheet = client.open_by_key(TARGET_SPREADSHEET_ID.strip())
        sheet = spreadsheet.get_worksheet(0)
        
        rows = sheet.get_all_values()
        if len(rows) <= 1:
            return []
            
        data_rows = rows[1:] # ヘッダーを除く
        records = []
        for r in data_rows:
            # インデックスエラーを防ぐためパディングを20に拡張
            padded = list(r) + [""] * max(0, 20 - len(r))
            record = {
                "id": padded[0],
                "name": padded[1],
                "main_func": padded[2],
                "sub_func": padded[3],
                "memo": padded[4],
                "scores": []
            }
            # スコア（5〜9列目）のパース処理
            for val in padded[5:10]:
                try:
                    record["scores"].append(float(val) if val != "" else 0.0)
                except ValueError:
                    record["scores"].append(0.0)
            records.append(record)
        return records
    except Exception as e:
        st.error(f"スプレッドシートの読み込み中にエラーが発生しました: {e}")
        return []

def main():
    st.title("AI統合型 認知特性テスト - 管理画面")
    
    with st.spinner("スプレッドシートからデータを読み込んでいます..."):
        records = fetch_from_spreadsheet()
        
    if not records:
        st.warning("データが取得できなかったか、スプレッドシートが空です。")
        return
        
    st.success(f"{len(records)} 件のデータを取得しました。")
    
    # データ一覧の表示
    for rec in records:
        st.write(f"名前: **{rec['name']}** (ID: {rec['id']}) | メイン: {rec['main_func']} | サブ: {rec['sub_func']}")

if __name__ == "__main__":
    main()
