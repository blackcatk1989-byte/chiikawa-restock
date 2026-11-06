"""ちいかわマーケット 補貨監控：有貨時用 ntfy 推播到手機。"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = "https://chiikawamarket.jp"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
STATE_FILE = Path(__file__).with_name("state.json")
TPE = timezone(timedelta(hours=8))

# 商品代碼（網址 /products/ 後面的數字）: 顯示名稱
PRODUCTS = {
    "4571609412281": "Kiramekko Teddy Bear Christmas（ちいかわ）",
    "4571609412298": "Kiramekko Teddy Bear Christmas（ハチワレ）",
    "4571609412304": "Kiramekko Teddy Bear Christmas（うさぎ）",
    "4571609413035": "ツリーなうさぎマスコット",
    "4571609414148": "クリスマスリースなぬいぐるみ",
    "4571609414117": "クリスマスの精マスコット（ちいかわ）",
    "4571609414124": "クリスマスの精マスコット（ハチワレ）",
    "4571609414131": "クリスマスの精マスコット（うさぎ）",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept": "application/json",
}


def is_available(handle: str) -> bool:
    """Shopify 的 /products/<handle>.js 會回傳 available 欄位。"""
    req = urllib.request.Request(f"{BASE}/products/{handle}.js", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    return bool(data.get("available"))


def notify(title: str, message: str, click: str) -> None:
    payload = {
        "topic": NTFY_TOPIC,
        "title": title,
        "message": message,
        "click": click,
        "priority": 5,
        "tags": ["rotating_light"],
    }
    req = urllib.request.Request(
        "https://ntfy.sh",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=20).read()


def main() -> int:
    if not NTFY_TOPIC:
        print("缺少 NTFY_TOPIC")
        return 1

    if os.environ.get("TEST_NOTIFY") == "true":
        notify("ちいかわ 測試通知", "補貨監控推播正常運作中 ✅", f"{BASE}/collections/newitems")
        print("已送出測試通知")
        return 0

    old = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    new = dict(old)
    newly_available = []
    errors = 0

    for handle, name in PRODUCTS.items():
        try:
            ok = is_available(handle)
        except Exception as e:  # 網站暫時讀不到就跳過，下次再查
            print(f"[錯誤] {name}: {e}")
            errors += 1
            continue
        print(f"{'有貨' if ok else '售完'}  {name}")
        if ok and not old.get(handle):
            newly_available.append((handle, name))
        new[handle] = ok
        time.sleep(1)

    # 只在「售完 → 有貨」時通知，避免每 5 分鐘重複推播
    for handle, name in newly_available:
        url = f"{BASE}/products/{handle}"
        notify("ちいかわ 有貨了！", f"{name}\n點這則通知直接開商品頁", url)
        print(f"已通知：{name}")

    if errors == len(PRODUCTS):
        now = datetime.now(TPE).strftime("%H:%M")
        print(f"{now} 全部商品都讀取失敗，可能被網站擋了")

    if new != old:
        STATE_FILE.write_text(json.dumps(new, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
