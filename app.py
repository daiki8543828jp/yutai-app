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

# タブを3つに分割
tab1, tab2, tab3 = st.tabs(["📋 優待一覧", "➕ 新規登録", "✏️ 編集・削除"])

# --- タブ1: 一覧表示 ---
with tab1:
    st.subheader("登録済み優待一覧")
    df = load_data()
    
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

        # ▼ 修正ポイント: st.table を使って中央揃えを強制適用する ▼
        styled_df = df_display.style.hide(axis="index").set_properties(**{
            'text-align': 'center'
        }).set_table_styles([
            {'selector': 'th', 'props': [('text-align', 'center')]},
            {'selector': 'td', 'props': [('text-align', 'center')]}
        ])

        # st.dataframe ではなく st.table で表示
        st.table(styled_df)
        # ▲ ▲ ▲ ▲ ▲ ▲ ▲ ▲ ▲ ▲ ▲ ▲ ▲ ▲ ▲ ▲ ▲ ▲ ▲
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
        options = {f"{row['name']} (期限: {row['expiry_date']})": row['id'] for index, row in df.iterrows()}
        selected_label = st.selectbox("編集・削除する優待を選択してください", list(options.keys()))
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
            
            col1, col2 = st.columns(2)
            with col1:
                update_btn = st.form_submit_button("この内容で更新")
            with col2:
                delete_btn = st.form_submit_button("このデータを削除", type="primary")
                
            if update_btn:
                if new_name:
                    update_data(selected_id, new_name, new_amount, new_expiry_date, new_memo)
                    st.success("データを更新しました！")
                    st.rerun()
                else:
                    st.error("名称は必須入力です。")
                    
            if delete_btn:
                delete_data(selected_id)
                st.warning(f"「{target_row['name']}」を削除しました。")
                st.rerun()
    else:
        st.info("編集できるデータがありません。")
