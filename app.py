import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import pandas as pd
import plotly.graph_objects as go

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
        # ヘッダーを残して2行目以降をすべてクリア
        rows = sheet.get_all_values()
        if len(rows) > 1:
            sheet.batch_clear([f"A2:Z{len(rows)}"])
        return True
    except Exception as e:
        st.error(f"一括クリア中にエラーが発生しました: {e}")
        return False

def main():
    st.title("AI統合型 認知特性テスト - 管理画面")
    st.markdown("---")
    
    # サイドバー
    st.sidebar.header("メニュー")
    menu = st.sidebar.selectbox("表示モード", ["受検者データ一覧", "データ管理・削除"])
    
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
            st.dataframe(df, use_container_width=True)
            
            # 詳細確認セクション
            st.markdown("### 🔍 個別詳細ビュー & 削除")
            selected_row = st.selectbox("確認・削除する受検者を選択", df.index, format_func=lambda x: f"{df.loc[x, '氏名'] if '氏名' in df.columns else f'行 {x+1}'}")
            
            if selected_row is not None and not df.empty:
                row_data = df.loc[selected_row]
                col1, col2 = st.columns(2)
                with col1:
                    for col_name in df.columns[:5]:
                        st.metric(label=col_name, value=row_data.get(col_name, "-"))
                    
                    st.markdown("---")
                    # 個別削除ボタン
                    if st.button("🗑️ この受検者データを削除する", type="secondary"):
                        # pandasのインデックス(0始まり)からスプレッドシートの行番号(2始まり)を計算
                        sheet_row_idx = int(selected_row) + 2
                        if delete_row_from_sheet(sheet_row_idx):
                            st.success("データを削除しました！")
                            st.cache_resource.clear()
                            st.rerun()

                with col2:
                    st.write("#### 📊 スコア・レーダーチャート")
                    
                    score_cols = [c for c in df.columns if 'スコア' in c]
                    if not score_cols and len(df.columns) >= 10:
                        score_cols = df.columns[5:10]
                    
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

    elif menu == "データ管理・削除":
        st.subheader("✍️ データ管理・一括削除")
        st.info("スプレッドシートのデータを一覧で確認したり、全データを一括でクリア（初期化）することができます。")
        
        if not df.empty:
            st.write("現在のスプレッドシート内容プレビュー:")
            st.dataframe(df, use_container_width=True)
            
            st.markdown("---")
            st.warning("⚠️ 注意: 以下のボタンを押すと、スプレッドシートのデータ（ヘッダー行を除くすべての受検者データ）が完全に削除されます。")
            if st.button("🔥 すべてのデータを一括削除（クリア）する", type="primary"):
                if clear_all_data():
                    st.success("すべてのデータをクリアしました！")
                    st.cache_resource.clear()
                    st.rerun()
        else:
            st.info("現在、削除対象となるデータはありません。")

if __name__ == "__main__":
    main()
