import streamlit as st
import pandas as pd
import plotly.express as px
import io
import time
from datetime import datetime

# ==========================================
# ページ設定
# ==========================================
st.set_page_config(page_title="AI統合型 認知特性テスト", layout="wide")

# ==========================================
# セッション状態（メモリ）の初期化
# ==========================================
if "page" not in st.session_state:
    st.session_state.page = "candidate"  # "candidate" または "admin"
if "is_admin_auth" not in st.session_state:
    st.session_state.is_admin_auth = False
if "candidate_data" not in st.session_state:
    st.session_state.candidate_data = []

# ==========================================
# サイドバー（管理者向け免責事項・データ削除）
# ==========================================
with st.sidebar:
    st.title("⚙️ アプリ機能")
    if st.session_state.page == "admin" and st.session_state.is_admin_auth:
        st.subheader("データ管理")
        if st.button("⚠️ 保存された履歴データをすべて削除"):
            st.session_state.candidate_data = []
            st.success("すべてのデータをリセットしました。")
            time.sleep(1)
            st.rerun()
            
    st.markdown("---")
    st.markdown("### ご利用にあたっての重要事項（免責・禁止事項）")
    st.markdown("""
    **【1. ツールの目的と運用の限界】**
    本ツールは、応募者や従業員の思考・コミュニケーション特性を把握し、配置のミスマッチや組織内摩擦の低減、日常の労務管理（ハラスメントリスクの低減等）を補助するためのものです。医学的な診断を目的とするものではなく、面接時におけるメンタル疾患の発見・特定等を目的とした使用はできません。最終的な採用・配属決定は、総合的な評価に基づきご自身の責任で行ってください。

    **【2. 免責事項（不可抗力と危険負担）】**
    予期せぬシステムエラーやバグ、通信障害、第三者による不正アクセス（ハッキング等）、および天災地変等の不可抗力（自然災害等）により本システムが停止・誤作動・情報漏洩した場合、それに伴う利用者のいかなる損害についても開発者は責任を負いかねます。

    **【3. 転売・譲渡の禁止と法的措置】**
    開発者の事前の同意なく、本ツールのプログラム、URL、出力結果のフォーマット等を複製、無断転売、譲渡、貸与することを固く禁じます。違反行為が発覚した場合、損害賠償等の民事上の措置に加え、直ちに刑事告訴等の厳格な法的措置を講じます。
    """)

# ==========================================
# 画面遷移メニュー（中央）
# ==========================================
col_nav1, col_nav2 = st.columns([1, 1])
with col_nav1:
    if st.button("🧑‍💻 応募者用画面へ", use_container_width=True):
        st.session_state.page = "candidate"
        st.rerun()
with col_nav2:
    with st.expander("🏢 採用側（管理）画面へ", expanded=False):
        pwd = st.text_input("パスワードを入力してください", type="password")
        if st.button("ログインして切り替え"):
            if pwd == "7777":  # ※所定のパスワード
                st.session_state.is_admin_auth = True
                st.session_state.page = "admin"
                st.rerun()
            else:
                st.error("パスワードが間違っています。")

st.markdown("---")

# ==========================================
# 1. 応募者用画面
# ==========================================
if st.session_state.page == "candidate":
    st.title("思考・表現力セッション")
    st.write("これまでの仕事や生活で最も工夫して乗り越えたエピソードなど、自由に記述してください。")

    name_input = st.text_input("氏名をご記入ください")
    text_input = st.text_area("エピソードの記述（文字数無制限）", height=300)

    if st.button("これで完了する（終了）", type="primary"):
        if name_input.strip() and text_input.strip():
            with st.spinner("AIが解析中です..."):
                # -----------------------------------------------------
                # 【ここにGemini APIの呼び出しコードが本来入ります】
                # 今回は保存処理を確実に行うためのダミー結果を生成しています
                # （実際のGemini呼び出しコードがある場合はここを置き換えてください）
                # -----------------------------------------------------
                time.sleep(2) # API通信のモック
                
                new_data = {
                    "応募者ID": len(st.session_state.candidate_data) + 1,
                    "氏名": name_input,
                    "text": text_input,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    # ドロップダウンとExcel用のデータ
                    "主タイプ_list": ["Si-Fe"],
                    "主タイプ": "Si-Fe",
                    "補助機能_list": ["内向感覚(Si)", "外向感情(Fe)"],
                    "補助機能": "内向感覚(Si), 外向感情(Fe)",
                    "採用・評価メモ": "環境やプライベートな空間に対する強いこだわりが見られる一方、ビジネスシーンにおける客観性や柔軟性に欠けるリスクがある。\n面接では、他者との協調性や、定型的でない業務への適応力について具体的に確認することが推奨される。",
                    # レーダーチャート用スコア
                    "論理的分析力": 45,
                    "直観・本質把握": 40,
                    "計画・規律性": 65,
                    "独立・内省力": 80,
                    "対人・柔軟性": 35
                }
                st.session_state.candidate_data.append(new_data)
                
                # -----------------------------------------------------
                # 【ここにGoogleスプレッドシートへの初期追加コードが入ります】
                # -----------------------------------------------------
                
            st.success("送信が完了いたしました。ご協力ありがとうございました！そのままブラウザを閉じて終了してください。")
            st.balloons()
        else:
            st.warning("氏名とエピソードの両方を入力してください。")

# ==========================================
# 2. 採用側（管理）画面
# ==========================================
elif st.session_state.page == "admin":
    if not st.session_state.is_admin_auth:
        st.warning("上部のメニューからパスワードを入力してログインしてください。")
    else:
        st.title("採用担当者用 管理・評価ダッシュボード")
        
        if not st.session_state.candidate_data:
            st.info("現在、提出されたデータはありません。")
        else:
            # 応募者ごとにカードを表示
            for idx, candidate in enumerate(st.session_state.candidate_data):
                with st.container():
                    st.markdown(f"### 提出データ #{idx+1}： {candidate['氏名']} 様")
                    st.caption(f"提出日時: {candidate['timestamp']}")
                    
                    st.subheader("【応募者の記述内容】")
                    st.write(candidate["text"])
                    
                    st.markdown("---")
                    st.subheader("【AI拡張解析・ラベリングエリア】")
                    
                    # --- レーダーチャート表示 ---
                    scores = {
                        "項目": ["論理的分析力", "直観・本質把握", "計画・規律性", "独立・内省力", "対人・柔軟性"],
                        "スコア": [
                            candidate["論理的分析力"], 
                            candidate["直観・本質把握"], 
                            candidate["計画・規律性"], 
                            candidate["独立・内省力"], 
                            candidate["対人・柔軟性"]
                        ]
                    }
                    df_scores = pd.DataFrame(scores)
                    fig = px.line_polar(df_scores, r="スコア", theta="項目", line_close=True, range_r=[0, 100])
                    fig.update_traces(fill='toself')
                    
                    col_chart, col_edit = st.columns([1, 1.5])
                    
                    with col_chart:
                        st.plotly_chart(fig, use_container_width=True)
                        
                    with col_edit:
                        # ドロップダウンとテキストエリア（直接 key で状態を管理）
                        main_type_selected = st.multiselect(
                            "主タイプ",
                            options=["Si-Fe", "Te-Ni", "Ni-Te", "Ne-Fi", "Fi-Ne", "Ti-Ne", "Fe-Si", "Se-Ti"],
                            default=candidate.get("主タイプ_list", []),
                            key=f"main_type_{idx}"
                        )
                        
                        sub_type_selected = st.multiselect(
                            "補助機能",
                            options=["外向感情(Fe)", "内向感覚(Si)", "内向直観(Ni)", "外向思考(Te)", "外向直観(Ne)", "内向感情(Fi)", "内向思考(Ti)", "外向感覚(Se)"],
                            default=candidate.get("補助機能_list", []),
                            key=f"sub_type_{idx}"
                        )
                        
                        memo_text = st.text_area(
                            "採用・評価メモ（認知の癖、リスク、矛盾点など）",
                            value=candidate.get("採用・評価メモ", ""),
                            key=f"memo_{idx}",
                            height=150
                        )
                        
                        # ------------------------------------------------
                        # ★ 確実な保存処理（st.rerun() による即時反映）
                        # ------------------------------------------------
                        if st.button("💾 評価を保存する", key=f"save_btn_{idx}"):
                            # 文字列に変換して保存（Excel出力用）
                            st.session_state.candidate_data[idx]["主タイプ"] = ", ".join(main_type_selected) if main_type_selected else ""
                            st.session_state.candidate_data[idx]["補助機能"] = ", ".join(sub_type_selected) if sub_type_selected else ""
                            
                            # リスト形式も保存（画面表示用）
                            st.session_state.candidate_data[idx]["主タイプ_list"] = main_type_selected
                            st.session_state.candidate_data[idx]["補助機能_list"] = sub_type_selected
                            
                            # メモの保存
                            st.session_state.candidate_data[idx]["採用・評価メモ"] = memo_text
                            
                            st.success(f"提出データ #{idx + 1} の評価を保存・更新しました！")
                            time.sleep(1) # メッセージを1秒見せてから画面をリフレッシュ
                            st.rerun()
                            
                    # 個別削除ボタン
                    if st.button("🗑️ このデータを削除", key=f"del_btn_{idx}"):
                        st.session_state.candidate_data.pop(idx)
                        st.rerun()
                        
                    st.markdown("---")

            # ==========================================
            # Excel一括ダウンロード（保存された最新データを参照）
            # ==========================================
            st.subheader("📥 評価結果のエクスポート")
            
            # Excel出力用のデータフレームを作成（必要な列だけを抽出）
            export_df = pd.DataFrame(st.session_state.candidate_data)
            if not export_df.empty:
                columns_to_export = [
                    "応募者ID", "氏名", "主タイプ", "補助機能", "採用・評価メモ",
                    "論理的分析力", "直観・本質把握", "計画・規律性", "独立・内省力", "対人・柔軟性"
                ]
                export_df = export_df[columns_to_export]
                
                # Excelファイルの生成
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    export_df.to_excel(writer, index=False, sheet_name='評価結果')
                excel_data = output.getvalue()
                
                st.download_button(
                    label="全員の評価結果をExcelで一括ダウンロード",
                    data=excel_data,
                    file_name=f"evaluation_results_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
