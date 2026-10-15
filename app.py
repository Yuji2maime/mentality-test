import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json

st.set_page_config(page_title="AI統合型 認知特性テスト - 接続テスト画面", layout="wide")

# 正しいスプレッドシートIDに修正済み
TARGET_SPREADSHEET_ID = "1hkFRa9v6wbGqmT1RAKvm9EJhuEIRS-R9YAELThPJRW0"

def fetch_from_spreadsheet():
    try:
        st.write("--- 接続テスト開始 ---")
        
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        st.write("1. Streamlit Secretsから認証情報を取得しています...")
        if "gcp_credentials" in st.secrets:
            raw_creds = st.secrets["gcp_credentials"]
            if isinstance(raw_creds, str):
                creds_dict = json.loads(raw_creds)
            else:
                creds_dict = dict(raw_creds)
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            st.write("-> 【成功】認証情報のパースが完了しました。")
        else:
            st.error("【エラー】gcp_credentials が見つかりません。")
            return []
            
        st.write("2. gspreadクライアントの認可を行っています...")
        client = gspread.authorize(creds)
        st.write("-> 【成功】クライアントの認可が完了しました。")
        
        st.write("3. スプレッドシートを開いています...")
        spreadsheet = client.open_by_key(TARGET_SPREADSHEET_ID.strip())
        st.write("-> 【成功】スプレッドシートを開くことができました！")
        
        st.write("4. ワークシートを取得しています...")
        sheet = spreadsheet.get_worksheet(0)
        st.write("-> 【成功】ワークシートを取得しました。")
        
        st.write("5. 行データをすべて取得しています...")
        rows = sheet.get_all_values()
        st.write(f"-> 【成功】全 {len(rows)} 行のデータを取得しました！")
        
        if len(rows) <= 1:
            return []
            
        data_rows = rows[1:]
        records = []
        for r in data_rows:
            padded = list(r) + [""] * max(0, 20 - len(r))
            record = {
                "id": padded[0],
                "name": padded[1],
                "main_func": padded[2],
                "sub_func": padded[3],
                "memo": padded[4],
                "scores": []
            }
            for val in padded[5:10]:
                try:
                    record["scores"].append(float(val) if val != "" else 0.0)
                except ValueError:
                    record["scores"].append(0.0)
            records.append(record)
        return records
    except Exception as e:
        st.error(f"【詳細エラー】以下の箇所で例外が発生しました: {e}")
        return []

def main():
    st.title("AI統合型 認知特性テスト - 接続テスト画面")
    records = fetch_from_spreadsheet()
    if records:
        st.success(f"🎉 データの読み込みに完全成功しました！（計 {len(records)} 件）")
        for rec in records:
            st.write(f"名前: **{rec['name']}** (ID: {rec['id']})")

if __name__ == "__main__":
    main()
