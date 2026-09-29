"""
公式 sample.csv の24件を使って、
1-1.py の住所分割処理が正しいか確認するテストプログラム。
"""

import pandas as pd

# 1-1.pyと同じ住所分割関数を使用する
from improved1_1 import split_address


# ==================== 1. 設定 ====================

SAMPLE_FILE = "sample.csv"


# ==================== 2. sample.csvを読む ====================

df = pd.read_csv(
    SAMPLE_FILE,
    encoding="utf-8-sig"
)


# ==================== 3. テスト開始 ====================

success_count = 0

print("===== 住所分割テスト =====")
print()


for index, row in df.iterrows():

    # ---------- sample.csvの正解データ ----------

    prefecture = (
        ""
        if pd.isna(row["都道府県"])
        else str(row["都道府県"]).strip()
    )

    city = (
        ""
        if pd.isna(row["市区町村"])
        else str(row["市区町村"]).strip()
    )

    street = (
        ""
        if pd.isna(row["番地"])
        else str(row["番地"]).strip()
    )

    building = (
        ""
        if pd.isna(row["建物名"])
        else str(row["建物名"]).strip()
    )


    # ---------- 正解データ ----------

    expected = (
        prefecture,
        city,
        street,
        building
    )


    # ---------- 元の住所を復元 ----------

    # 都道府県、市区町村、番地をつなげる
    full_address = (
        prefecture
        + city
        + street
    )

    # 建物名がある場合は、
    # 番地との境界が分かるようにスペースを入れる
    if building:
        full_address += " " + building


    # ---------- 1-1.pyの住所分割関数を実行 ----------

    actual = split_address(
        full_address
    )


    # ---------- 正解と比較 ----------

    if actual == expected:

        result = "OK"
        success_count += 1

    else:

        result = "NG"


    # ---------- 1件ごとの結果を表示 ----------

    print(
        f"{index + 1:2}件目: {result}"
    )


    # NGの場合だけ詳細を表示する
    if result == "NG":

        print(
            f"   元住所 : {full_address}"
        )

        print(
            f"   正解   : {expected}"
        )

        print(
            f"   実際   : {actual}"
        )

        print()


# ==================== 4. 最終結果 ====================

print()
print("----------------------------------------")

print(
    f"住所分割テスト結果: "
    f"{success_count}/{len(df)} 一致"
)

print("----------------------------------------")


# ==================== 5. 合否を表示 ====================

if success_count == len(df):

    print(
        "すべての住所がsample.csvと一致しました。"
    )

else:

    failed_count = (
        len(df) - success_count
    )

    print(
        f"{failed_count}件の住所が一致しませんでした。"
    )
