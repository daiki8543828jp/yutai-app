import tomllib
import requests
from supabase import create_client, Client
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- 1. 設定ファイルの読み込み ---
# st.secrets は Streamlit 起動時専用のため、ここでは tomllib を使って直接読み込みます
# (Python 3.11以降に標準搭載されている tomllib を使用)
with open(".streamlit/secrets.toml", "rb") as f:
    secrets = tomllib.load(f)

SUPABASE_URL = secrets["SUPABASE_URL"]
SUPABASE_KEY = secrets["SUPABASE_KEY"]
SLACK_WEBHOOK_URL = secrets["SLACK_WEBHOOK_URL"]

# Supabaseクライアントの初期化
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. 通知実行ロジック ---
def send_slack_message(message):
    """Slackにメッセージを送信する関数"""
    data = {"text": message}
    response = requests.post(SLACK_WEBHOOK_URL, json=data)
    if response.status_code == 200:
        print("Slack通知成功！")
    else:
        print(f"通知失敗: {response.status_code}, {response.text}")

def check_and_notify():
    """有効期限をチェックして通知する関数"""
    today = date.today()
    # ターゲット日付の計算
    target_1_month = today + relativedelta(months=1)  # 1ヶ月後
    target_1_half_week = today + relativedelta(days=10) # 1.5週間後（約10日後）

    # Supabaseから全データを取得
    response = supabase.table("yutai").select("*").execute()
    records = response.data

    if not records:
        print("登録されている優待データはありません。")
        return

    # 各レコードの期限をチェック
    for row in records:
        name = row['name']
        amount = row.get('amount', '金額未定')
        # 文字列の日付('YYYY-MM-DD')を date オブジェクトに変換
        expiry_date = datetime.strptime(row['expiry_date'], '%Y-%m-%d').date()

        # 【1ヶ月前】の判定
        if expiry_date == target_1_month:
            msg = f"📢 *【期限1ヶ月前】*\n株主優待 *「{name}」* ({amount}円相当) の期限が1ヶ月後（{expiry_date}）に迫っています！"
            send_slack_message(msg)

        # 【1.5週間前】の判定
        elif expiry_date == target_1_half_week:
            msg = f"🚨 *【期限1.5週間前】*\n株主優待 *「{name}」* ({amount}円相当) の期限がもうすぐ（{expiry_date}）です！忘れずに使用してください。"
            send_slack_message(msg)

if __name__ == "__main__":
    print(f"本日の日付: {date.today()} - 株主優待の期限チェックを開始します...")
    check_and_notify()
    print("チェック完了！")