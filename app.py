import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import date, datetime
import notifier

# --- Supabaseの接続設定 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- データベース操作関数 ---
def load_data():
    response = supabase.table("yutai").select("*").execute()
    return pd.DataFrame(response.data)

def insert_data(name, amount, expiry_date, memo):
    data = {
        "name": name,
        "amount": amount,
        "expiry_date": str(expiry_date),
        "memo": memo
    }
    supabase.table("yutai").insert(data).execute()

def update_data(record_id, name, amount, expiry_date, memo):
    data = {
        "name": name,
        "amount": amount,
        "expiry_date": str(expiry_date),
        "memo": memo
    }
    supabase.table("yutai").update(data).eq("id", record_id).execute()

def delete_data(record_id):
    supabase.table("yutai").delete().eq("id", record_id).execute()

# --- 画面UIの設定 ---
st.set_page_config(page_title="株主優待管理", layout="wide")
st.title("🎁 株主優待 管理アプリ")

# サイドバー（通知テスト用）
with st.sidebar:
    st.header("⚙️ 管理メニュー")
    st.write("定期通知の動作確認用")
    if st.button("Slack通知テストを実行"):
        try:
            notifier.check_and_notify()
            st.success("通知プログラムを実行しました！対象があればSlackに通知が届きます。")
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")

# データ取得（全タブで使うため外に出す）
df = load_data()

# タブを3つに分割
tab1, tab2, tab3 = st.tabs(["📋 優待一覧", "➕ 新規登録", "⚙️ 編集・削除"])

# --- タブ1: 一覧表示 ---
with tab1:
    st.subheader("登録済み優待一覧")
    
    if not df.empty:
        # カラム名を日本語に変換
        df_display = df[['name', 'amount', 'expiry_date', 'memo']].rename(columns={
            'name': '名称',
            'amount': '金額 (円)',
            'expiry_date': '有効期限',
            'memo': 'メモ'
        })

        # 並び替え（ソート）用のUI
        col_sort1, col_sort2 = st.columns(2)
        with col_sort1:
            sort_col = st.selectbox("並び替え項目", ["有効期限", "金額 (円)", "名称"])
        with col_sort2:
            sort_order = st.radio("順序", ["昇順", "降順"], horizontal=True)

        # 選択された条件でデータをソートする
        is_ascending = True if sort_order == "昇順" else False
        df_display = df_display.sort_values(by=sort_col, ascending=is_ascending)

        # HTMLタグを左詰めにして誤作動を防止し、デザインを整える
        table_html = df_display.to_html(index=False)
        
        html_code = f"""
<style>
.custom-table table {{
    width: 100%;
    border-collapse: collapse;
}}
.custom-table th, .custom-table td {{
    text-align: center !important;
    padding: 10px;
    border-bottom: 1px solid #e6e6f1;
}}
.custom-table th {{
    background-color: #f0f2f6;
    color: #31333F;
}}
</style>
<div class="custom-table">
{table_html}
</div>
"""
        st.markdown(html_code, unsafe_allow_html=True)
    else:
        st.info("現在登録されている株主優待はありません。")

# --- タブ2: 新規登録フォーム ---
with tab2:
    st.subheader("優待の新規登録")
    with st.form("yutai_form", clear_on_submit=True):
        name = st.text_input("名称 (例: オリックス カタログギフト)")
        amount = st.number_input("金額 (円)", min_value=0, step=500)
        expiry_date = st.date_input("有効期限", min_value=date.today())
        memo = st.text_area("メモ (例: 妻の誕生日プレゼントに使う)")
        
        submitted = st.form_submit_button("登録")
        
        if submitted:
            if name:
                insert_data(name, amount, expiry_date, memo)
                st.success(f"「{name}」を登録しました！")
                st.rerun()
            else:
                st.error("名称は必須入力です。")

# --- タブ3: 編集・削除フォーム ---
with tab3:
    st.subheader("登録済みデータの編集・削除")
    if not df.empty:
        # 操作モードの切り替え
        operation_mode = st.radio(
            "操作を選択してください", 
            ["✏️ 1件を選択して編集する", "🗑️ 複数を選択して一括削除する"], 
            horizontal=True
        )
        st.divider()

        # 【編集モード】従来通り1件ずつ編集
        if operation_mode == "✏️ 1件を選択して編集する":
            options = {f"{row['name']} (期限: {row['expiry_date']})": row['id'] for index, row in df.iterrows()}
            selected_label = st.selectbox("編集する優待を選択してください", list(options.keys()))
            selected_id = options[selected_label]
            
            target_row = df[df['id'] == selected_id].iloc[0]
            
            current_amount = int(target_row['amount']) if pd.notna(target_row['amount']) else 0
            current_memo = str(target_row['memo']) if pd.notna(target_row['memo']) else ""
            current_date = datetime.strptime(str(target_row['expiry_date']), '%Y-%m-%d').date()

            with st.form("edit_form"):
                new_name = st.text_input("名称", value=str(target_row['name']))
                new_amount = st.number_input("金額 (円)", min_value=0, step=500, value=current_amount)
                new_expiry_date = st.date_input("有効期限", value=current_date)
                new_memo = st.text_area("メモ", value=current_memo)
                
                update_btn = st.form_submit_button("この内容で更新")
                    
                if update_btn:
                    if new_name:
                        update_data(selected_id, new_name, new_amount, new_expiry_date, new_memo)
                        st.success("データを更新しました！")
                        st.rerun()
                    else:
                        st.error("名称は必須入力です。")

        # ▼ 修正ポイント: 【削除モード】リスト形式でチェックボックス表示 ▼
        elif operation_mode == "🗑️ 複数を選択して一括削除する":
            st.write("削除したい優待にチェックを入れてください：")
            
            # チェックされたIDを保存するリスト
            selected_ids = []
            
            # 登録されているデータをループして、それぞれにチェックボックスを表示
            for index, row in df.iterrows():
                # 表示するテキスト（名称を太字にして見やすくする）
                label = f"**{row['name']}** （金額: {row.get('amount', 0)}円, 期限: {row['expiry_date']}）"
                
                # チェックボックスを生成。チェックされたらリストにIDを追加
                if st.checkbox(label, key=f"del_{row['id']}"):
                    selected_ids.append(row['id'])
            
            # 1つでもチェックされていれば、削除確認エリアを表示
            if selected_ids:
                st.markdown("---") # 区切り線
                st.warning(f"⚠️ 選択された **{len(selected_ids)}** 件のデータを削除します。この操作は元に戻せません。")
                confirm_delete = st.checkbox("本当に削除しますか？（チェックを入れると削除ボタンが有効になります）")
                
                # disabled を使って、チェックが入っていない時はボタンを押せなくする
                if st.button("選択したデータを一括削除", type="primary", disabled=not confirm_delete):
                    for delete_id in selected_ids:
                        delete_data(delete_id) # 複数回削除処理を実行
                    st.success(f"{len(selected_ids)} 件のデータを削除しました！")
                    st.rerun()

    else:
        st.info("編集・削除できるデータがありません。")
