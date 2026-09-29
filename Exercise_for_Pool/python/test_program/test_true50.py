"""
1-1.csvが空欄行で埋められた50行ではなく、
50店舗分のデータになっているか確認するテスト。
"""

from pathlib import Path

import pandas as pd


# ==================== 1. 設定 ====================

TEST_DIR = Path(__file__).resolve().parent
CSV_FILE = TEST_DIR.parent / "ex1_web-scraping" / "1-1.csv"
TARGET_COUNT = 50

if not CSV_FILE.is_file():
    raise FileNotFoundError(
        f"1-1.csvが見つかりません: {CSV_FILE}"
    )


# ==================== 2. CSVを読み込む ====================

df = pd.read_csv(CSV_FILE, encoding="utf-8-sig")

for column in ("店舗名", "URL"):
    if column not in df.columns:
        raise ValueError(
            f"CSVに必要な列「{column}」がありません: {CSV_FILE}"
        )

print("===== 50店舗取得テスト =====")
print("確認するCSV:", CSV_FILE)
print()


# ==================== 3. 行数 ====================

row_count = len(df)
print(f"CSVのデータ行数: {row_count}")


# ==================== 4. 完全な空欄行 ====================

# NaNだけでなく、空文字や空白だけのセルも空欄とみなす
text_df = df.fillna("").astype(str).apply(
    lambda column: column.str.strip()
)

blank_rows = df[text_df.eq("").all(axis=1)]
blank_row_count = len(blank_rows)

print(f"完全な空欄行: {blank_row_count}")


# ==================== 5. 店舗名の空欄 ====================

shop_name = text_df["店舗名"]
blank_shop_rows = df[shop_name.eq("")]
blank_shop_count = len(blank_shop_rows)

print(f"店舗名が空欄の行: {blank_shop_count}")


# ==================== 6. URLの空欄・不正値 ====================

url = text_df["URL"]

blank_url_rows = df[url.eq("")]
blank_url_count = len(blank_url_rows)

hash_url_rows = df[url.eq("#")]
hash_url_count = len(hash_url_rows)

javascript_rows = df[
    url.str.lower().str.startswith("javascript:")
]
javascript_count = len(javascript_rows)

print(f"URLが空欄の行: {blank_url_count}")
print(f"URLが # の行: {hash_url_count}")
print(f"javascript: のURL: {javascript_count}")


# ==================== 7. 最終判定 ====================

passed = (
    row_count == TARGET_COUNT
    and blank_row_count == 0
    and blank_shop_count == 0
    and blank_url_count == 0
    and hash_url_count == 0
    and javascript_count == 0
)

print()
print("----------------------------------------")
print("テスト結果:", "OK" if passed else "NG")

if passed:
    print(
        "50行すべてに店舗名とURLがあり、"
        "空欄行・#・javascript: URLはありません。"
    )
else:
    print("上記のいずれかの条件を満たしていません。")


# ==================== 8. 問題行を表示 ====================

problem_groups = [
    ("完全な空欄行", blank_rows),
    ("店舗名が空欄の行", blank_shop_rows),
    ("URLが空欄の行", blank_url_rows),
    ("URLが # の行", hash_url_rows),
    ("javascript: のURL", javascript_rows),
]

for label, rows in problem_groups:
    if not rows.empty:
        print()
        print(f"【{label}】")
        print(rows.to_string(index=True))
