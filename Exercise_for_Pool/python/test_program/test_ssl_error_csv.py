"""
SSL異常時のCSVログ保存テスト

実際の improved1_1.py の check_ssl() を使用して、

1. 接続失敗
2. CAPTCHA

を人工的に発生させる。

その結果について、
・元の外部サイトURL
・エラー種類
・具体的なエラーメッセージ

をテスト用CSVへ保存し、
正しく保存されたか読み直して確認する。

本番の 1-1_ssl_errors.csv は変更しない。
"""

import csv
import os
import requests

from datetime import datetime
from unittest.mock import patch, Mock

from improved1_1 import check_ssl


# ============================================================
# 1. 設定
# ============================================================

TEST_OUTPUT_FILE = "test_ssl_errors_output.csv"

error_rows = []

success_count = 0
test_count = 0


# ============================================================
# 2. 接続失敗テスト
# ============================================================

print()
print("========================================")
print("テスト1: 接続失敗")
print("========================================")


shop_url_1 = "https://shop.example.com/"


# requests.get() が呼ばれたら、
# ConnectionErrorを人工的に発生させる
with patch(
    "improved1_1.requests.get"
) as mock_get:

    mock_get.side_effect = (
        requests.exceptions.ConnectionError(
            "テスト用の接続失敗"
        )
    )

    ssl_result_1, error_type_1, error_message_1 = (
        check_ssl(shop_url_1)
    )


# エラー情報を保存用リストへ追加
error_rows.append(
    {
        "発生日時": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "店舗URL": shop_url_1,
        "エラー種類": error_type_1,
        "エラーメッセージ": error_message_1
    }
)


print(
    "元のURL:",
    shop_url_1
)

print(
    "SSL結果:",
    ssl_result_1
)

print(
    "エラー種類:",
    error_type_1
)

print(
    "エラーメッセージ:",
    error_message_1
)


test_count += 1


if (
    ssl_result_1 is False
    and error_type_1 == "接続エラー"
    and "テスト用の接続失敗"
    in error_message_1
):

    print("判定結果: OK")
    success_count += 1

else:

    print("判定結果: NG")


# ============================================================
# 3. CAPTCHAテスト
# ============================================================

print()
print("========================================")
print("テスト2: CAPTCHA")
print("========================================")


# URL自体には "captcha" という文字を入れない。
# URLにcaptchaが入っていると、
# check_ssl() の最初のURL検査で
# 「無効なURL」と判定されるため。
shop_url_2 = "https://shop2.example.com/"


# 偽のHTTPレスポンスを作成
mock_response = Mock()


# 転送先URLは通常の外部サイトURLとする
mock_response.url = shop_url_2


# HTMLのタイトルをCAPTCHAにすることで、
# ページ内容によるCAPTCHA判定をテストする
mock_response.text = """
<html>

<head>
    <title>CAPTCHA</title>
</head>

<body>
    ロボットではないことを確認してください
</body>

</html>
"""


# HTTPステータスについては
# エラーを発生させない
mock_response.raise_for_status.return_value = None


with patch(
    "improved1_1.requests.get",
    return_value=mock_response
):

    ssl_result_2, error_type_2, error_message_2 = (
        check_ssl(shop_url_2)
    )


# CAPTCHAになっても、
# 取得済みの元URLを保存用リストへ入れる
error_rows.append(
    {
        "発生日時": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "店舗URL": shop_url_2,
        "エラー種類": error_type_2,
        "エラーメッセージ": error_message_2
    }
)


print(
    "元のURL:",
    shop_url_2
)

print(
    "SSL結果:",
    ssl_result_2
)

print(
    "エラー種類:",
    error_type_2
)

print(
    "エラーメッセージ:",
    error_message_2
)


test_count += 1


if (
    ssl_result_2 is False
    and error_type_2 == "CAPTCHA"
    and "CAPTCHA"
    in error_message_2
):

    print("判定結果: OK")
    success_count += 1

else:

    print("判定結果: NG")


# ============================================================
# 4. テスト用CSVへ保存
# ============================================================

print()
print("========================================")
print("テスト用CSVへ保存")
print("========================================")


fieldnames = [
    "発生日時",
    "店舗URL",
    "エラー種類",
    "エラーメッセージ"
]


with open(
    TEST_OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8-sig"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()

    writer.writerows(
        error_rows
    )


print(
    f"{TEST_OUTPUT_FILE} に保存しました。"
)


# ============================================================
# 5. CSVを読み直して確認
# ============================================================

print()
print("========================================")
print("保存内容を読み直して確認")
print("========================================")


with open(
    TEST_OUTPUT_FILE,
    "r",
    newline="",
    encoding="utf-8-sig"
) as file:

    reader = csv.DictReader(
        file
    )

    saved_rows = list(
        reader
    )


print(
    "保存されたエラー件数:",
    len(saved_rows)
)


for index, row in enumerate(
    saved_rows,
    start=1
):

    print()
    print(
        f"【{index}件目】"
    )

    print(
        "発生日時:",
        row["発生日時"]
    )

    print(
        "店舗URL:",
        row["店舗URL"]
    )

    print(
        "エラー種類:",
        row["エラー種類"]
    )

    print(
        "エラーメッセージ:",
        row["エラーメッセージ"]
    )


# ============================================================
# 6. CSV保存結果の判定
# ============================================================

print()
print("========================================")
print("CSV保存テスト")
print("========================================")


csv_test_ok = False


if len(saved_rows) == 2:

    row1 = saved_rows[0]
    row2 = saved_rows[1]


    # ---------- 接続失敗の保存内容 ----------

    connection_ok = (
        row1["店舗URL"]
        == shop_url_1

        and row1["エラー種類"]
        == "接続エラー"

        and "テスト用の接続失敗"
        in row1["エラーメッセージ"]
    )


    # ---------- CAPTCHAの保存内容 ----------

    captcha_ok = (
        row2["店舗URL"]
        == shop_url_2

        and row2["エラー種類"]
        == "CAPTCHA"

        and "CAPTCHA"
        in row2["エラーメッセージ"]
    )


    if (
        connection_ok
        and captcha_ok
    ):

        csv_test_ok = True


test_count += 1


if csv_test_ok:

    print("CSV保存結果: OK")
    success_count += 1

else:

    print("CSV保存結果: NG")


# ============================================================
# 7. 最終結果
# ============================================================

print()
print("========================================")
print("異常系ログ保存テスト 最終結果")
print("========================================")

print(
    f"{success_count}/{test_count} テスト成功"
)


if success_count == test_count:

    print(
        "すべてのテストに成功しました。"
    )

    print()

    print(
        "接続失敗・CAPTCHAの場合でも、"
    )

    print(
        "元の外部サイトURLを保持し、"
    )

    print(
        "エラー種類と具体的な"
        "エラーメッセージをCSVへ"
        "保存できることを確認しました。"
    )

else:

    print(
        f"{test_count - success_count}件の"
        "テストに失敗しました。"
    )


# ============================================================
# 8. テストCSVの存在確認
# ============================================================

print()


if os.path.exists(
    TEST_OUTPUT_FILE
):

    print(
        "テストCSV:",
        TEST_OUTPUT_FILE
    )

else:

    print(
        "テストCSVが見つかりません。"
    )
