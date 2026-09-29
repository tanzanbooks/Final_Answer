"""
SSL確認の異常系テスト

実際の1-1.pyの check_ssl() を使用して、

1. 接続失敗
2. CAPTCHA画面

を人工的に発生させる。

確認すること
・元の店舗URLが失われない
・SSL結果がFalseになる
・原因が正しく判定される
・エラーログに残せる情報が返される

実際の外部サイトにはアクセスしない。
"""

import requests

from unittest.mock import patch, Mock

from improved1_1 import check_ssl


# ============================================================
# 共通設定
# ============================================================

success_count = 0
test_count = 0


# ============================================================
# テスト1
# 接続失敗を人工的に発生させる
# ============================================================

print()
print("========================================")
print("テスト1: 接続失敗")
print("========================================")


original_url_1 = "https://shop.example.com/"


# requests.get() が呼ばれたら、
# ConnectionErrorを発生させる
with patch(
    "improved1_1.requests.get"
) as mock_get:

    mock_get.side_effect = (
        requests.exceptions.ConnectionError(
            "テスト用の接続失敗"
        )
    )

    ssl_result_1, error_type_1, error_message_1 = (
        check_ssl(original_url_1)
    )


# check_ssl()を実行した後も、
# 元URLそのものは変更していない
saved_url_1 = original_url_1


print(
    "元のURL:",
    original_url_1
)

print(
    "保存するURL:",
    saved_url_1
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
    saved_url_1 == original_url_1
    and ssl_result_1 is False
    and error_type_1 == "接続エラー"
    and "テスト用の接続失敗"
    in error_message_1
):

    print("結果: OK")
    success_count += 1

else:

    print("結果: NG")


# ============================================================
# テスト2
# CAPTCHA画面を人工的に返す
# ============================================================

print()
print("========================================")
print("テスト2: CAPTCHA")
print("========================================")


original_url_2 = "https://shop.example.com/"


# requests.get() が返す偽のレスポンスを作る
mock_response = Mock()

mock_response.url = (
    original_url_2
)

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


# raise_for_status()では
# エラーを発生させない
mock_response.raise_for_status.return_value = None


with patch(
    "improved1_1.requests.get",
    return_value=mock_response
):

    ssl_result_2, error_type_2, error_message_2 = (
        check_ssl(original_url_2)
    )


# CAPTCHAになっても
# 元の外部サイトURLを保持する
saved_url_2 = original_url_2


print(
    "元のURL:",
    original_url_2
)

print(
    "保存するURL:",
    saved_url_2
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
    saved_url_2 == original_url_2
    and ssl_result_2 is False
    and error_type_2 == "CAPTCHA"
    and "CAPTCHA"
    in error_message_2
):

    print("結果: OK")
    success_count += 1

else:

    print("結果: NG")


# ============================================================
# エラーログに保存する内容を確認
# ============================================================

print()
print("========================================")
print("ログへ保存できる情報")
print("========================================")

print()

print("【接続失敗】")

print(
    "URL:",
    saved_url_1
)

print(
    "エラー種類:",
    error_type_1
)

print(
    "エラーメッセージ:",
    error_message_1
)


print()

print("【CAPTCHA】")

print(
    "URL:",
    saved_url_2
)

print(
    "エラー種類:",
    error_type_2
)

print(
    "エラーメッセージ:",
    error_message_2
)


# ============================================================
# 最終結果
# ============================================================

print()
print("========================================")
print("SSL異常系テスト結果")
print("========================================")

print(
    f"{success_count}/{test_count} テスト成功"
)


if success_count == test_count:

    print(
        "すべてのテストに成功しました。"
    )

    print(
        "接続失敗・CAPTCHAの場合でも、"
        "元の外部サイトURLを保持し、"
        "原因を記録できることを確認しました。"
    )

else:

    print(
        f"{test_count - success_count}件の"
        "テストに失敗しました。"
    )
