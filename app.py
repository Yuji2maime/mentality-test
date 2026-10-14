import json
import os
from datetime import datetime
import gspread
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from google.oauth2.service_account import Credentials

# 【重要】スプレッドシートID
TARGET_SPREADSHEET_ID = "1hkFRa9v6wbGqmT1RAKvm9EJhuEiR9-R9YAELThPJRW0"

st.set_page_config(page_title="AI統合型 認知特性テスト", layout="wide")

def fetch_from_spreadsheet():
    """スプレッドシートから全データを読み込む"""
    creds_raw = st.secrets.get("gcp_credentials") or st.secrets.get("gcp_service_account")
    if not creds_raw:
        st.error("Google Cloudの認証情報（Secrets）が見つかりません。StreamlitのSecrets設定を確認してください。")
        return []

    # Secretsの値が文字列（JSON文字列）である場合を考慮してパースする
    try:
        if isinstance(creds_raw, str):
            creds_data = json.loads(creds_raw)
        else:
            creds_data = creds_raw
        
        # リスト形式（[...]）で保存されている場合は、最初の要素を取り出す
        if isinstance(creds_data, list):
            creds_data = creds_data[0]
    except Exception as e:
        st.error(f"認証情報の解析に失敗しました: {e}")
        return []

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(creds_data, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(TARGET_SPREADSHEET_ID).worksheet("シート1")
    rows = sheet.get_all_values()
    if len(rows) <= 1:
        return []
    
    data_rows = rows[1:]
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

def main():
    st.title("AI統合型 認知特性テスト - 管理画面")
    records = fetch_from_spreadsheet()
    
    if not records:
        st.info("スプレッドシートにデータが見つからないか、データが空です。")
        return

    df = pd.DataFrame(records)
    st.subheader("登録者一覧")
    st.dataframe(df)

    # 選択機能やレーダーチャート表示
    selected_name = st.selectbox("詳細を確認する人物を選択", options=df["name"].tolist())
    if selected_name:
        selected_row = df[df["name"] == selected_name].iloc[0]
        st.write(f"### {selected_name} の詳細")
        st.write(f"**主機能:** {selected_row['main_func']}")
        st.write(f"**補助機能:** {selected_row['sub_func']}")
        st.write(f"**メモ:** {selected_row['memo']}")

        scores = selected_row["scores"]
        categories = ["スコア1", "スコア2", "スコア3", "スコア4", "スコア5"]

        fig = go.Figure(data=go.Scatterpolar(
            r=scores,
            theta=categories,
            fill='toself'
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 10]
                )),
            showlegend=False
        )
        st.plotly_chart(fig)

if __name__ == "__main__":
    main()
