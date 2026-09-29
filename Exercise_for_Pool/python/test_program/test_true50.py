"""
1-1.csvが「空欄行を追加した50行」ではなく、
実際に取得できた50店舗分のデータになっているか確認するテスト。

確認内容
1. データ行が50行ある
2. 完全な空欄行がない
3. 店舗名が空欄の行がない
4. URLが空欄の行がない
5. URLが "#" ではない
6. URLが "javascript:" ではない
"""

import pandas as pd


# ==================== 1. 設定 ====================

CSV_FILE = "1-1.csv"

TARGET_COUNT = 50


# ==================== 2. CSVを読み込む ====================

df = pd.read_csv(
    CSV_FILE,
    encoding="utf-8-sig"
)


print("===== 50店舗取得テスト =====")
print()


# ==================== 3. 行数を確認 ====================

row_count = len(df)

print(
    f"CSVのデータ行数: {row_count}"
)


# ==================== 4. 完全な空欄行を確認 ====================

blank_rows = df[
    df.isna().all(axis=1)
]

blank_row_count = len(blank_rows)

print(
    f"完全な空欄行: {blank_row_count}"
)


# ==================== 5. 店舗名の空欄を確認 ====================

shop_name = (
    df["店舗名"]
    .fillna("")
    .astype(str)
    .str.strip()
)

blank_shop_rows = df[
    shop_name == ""
]

blank_shop_count = len(blank_shop_rows)

print(
    f"店舗名が空欄の行: {blank_shop_count}"
)


# ==================== 6. URLの空欄を確認 ====================

url = (
    df["URL"]
    .fillna("")
    .astype(str)
    .str.strip()
)

blank_url_rows = df[
    url == ""
]

blank_url_count = len(blank_url_rows)

print(
    f"URLが空欄の行: {blank_url_count}"
)


# ==================== 7. "#" のURLを確認 ====================

hash_url_rows = df[
    url == "#"
]

hash_url_count = len(hash_url_rows)

print(
    f"URLが # の行: {hash_url_count}"
)


# ==================== 8. javascript: のURLを確認 ====================

javascript_rows = df[
    url.str.lower().str.startswith(
        "javascript:"
    )
]

javascript_count = len(
    javascript_rows
)

print(
    f"javascript: のURL: {javascript_count}"
)


# ==================== 9. 最終判定 ====================

print()
print("----------------------------------------")


if (
    row_count == TARGET_COUNT
    and blank_row_count == 0
    and blank_shop_count == 0
    and blank_url_count == 0
    and hash_url_count == 0
    and javascript_count == 0
):

    print("テスト結果: OK")

    print(
        "空欄行で50行にせず、"
        "有効な50店舗分のデータが保存されています。"
    )

else:

    print("テスト結果: NG")

    print(
        "50店舗取得の条件を満たしていません。"
    )


# ==================== 10. 問題行を表示 ====================

if blank_row_count > 0:

    print()
    print("【完全な空欄行】")
    print(blank_rows)


if blank_shop_count > 0:

    print()
    print("【店舗名が空欄の行】")
    print(blank_shop_rows)


if blank_url_count > 0:

    print()
    print("【URLが空欄の行】")
    print(blank_url_rows)


if hash_url_count > 0:

    print()
    print("【URLが # の行】")
    print(hash_url_rows)


if javascript_count > 0:

    print()
    print("【javascript: のURL】")
    print(javascript_rows)
