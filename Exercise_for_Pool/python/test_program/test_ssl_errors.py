"""
test_ssl_errors.py

提出用1-1.pyの check_ssl() を使用し、
接続失敗とCAPTCHA画面を模擬する。

check_ssl() の判定結果から make_error_row() で
ログ用の行を作り、URL・原因・メッセージを確認する。

実際の外部サイトにはアクセスしない。
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import requests


# ============================================================
# 1. 提出用1-1.pyを読み込む
# ============================================================

TEST_DIR = Path(__file__).resolve().parent
PROGRAM_FILE = TEST_DIR.parent / "ex1_web-scraping" / "1-1.py"

spec = importlib.util.spec_from_file_location(
    "program_1_1",
    PROGRAM_FILE
)

if spec is None or spec.loader is None:
    raise ImportError(f"1-1.pyを読み込めません: {PROGRAM_FILE}")

program = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = program
spec.loader.exec_module(program)


# ============================================================
# 2. 結果を確認する関数
# ============================================================

success_count = 0
test_count = 0

# make_error_row() の列順：
# 発生日時、ぐるなび店舗URL、店舗名、
# 確認対象URL、エラーの種類、具体的なエラーメッセージ
TARGET_URL_INDEX = 3
ERROR_TYPE_INDEX = 4
MESSAGE_INDEX = 5


def check_result(
    test_name,
    original_url,
    ssl_result,
    error_type,
    error_message,
    expected_type,
    expected_message
):
    global success_count, test_count

    test_count += 1

    log_row = program.make_error_row(
        "https://r.gnavi.co.jp/test/",
        "テスト店舗",
        original_url,
        error_type,
        error_message
    )

    passed = (
        ssl_result is False
        and error_type == expected_type
        and expected_message in error_message
        and log_row[TARGET_URL_INDEX] == original_url
        and log_row[ERROR_TYPE_INDEX] == expected_type
        and expected_message in log_row[MESSAGE_INDEX]
    )

    print()
    print("========================================")
    print(test_name)
    print("========================================")
    print("元の外部サイトURL:", original_url)
    print("SSL結果:", ssl_result)
    print("エラー種類:", error_type)
    print("エラーメッセージ:", error_message)
    print("ログ行の確認対象URL:", log_row[TARGET_URL_INDEX])
    print("ログ行のエラー種類:", log_row[ERROR_TYPE_INDEX])
    print("ログ行のメッセージ:", log_row[MESSAGE_INDEX])
    print("結果:", "OK" if passed else "NG")

    if passed:
        success_count += 1


# ============================================================
# 3. 接続失敗
# ============================================================

original_url_1 = "https://shop.example.com/"

with (
    patch.object(program.time, "sleep"),
    patch.object(program.requests, "get") as mock_get
):
    mock_get.side_effect = requests.exceptions.ConnectionError(
        "テスト用の接続失敗"
    )

    (
        ssl_result_1,
        error_type_1,
        error_message_1
    ) = program.check_ssl(original_url_1)

check_result(
    "テスト1: 接続失敗",
    original_url_1,
    ssl_result_1,
    error_type_1,
    error_message_1,
    "接続エラー",
    "テスト用の接続失敗"
)


# ============================================================
# 4. CAPTCHA画面
# ============================================================

original_url_2 = "https://shop2.example.com/"

mock_response = Mock()
mock_response.url = original_url_2
mock_response.text = """
<html>
<head><title>CAPTCHA</title></head>
<body>ロボットではないことを確認してください</body>
</html>
"""
mock_response.raise_for_status.return_value = None

with (
    patch.object(program.time, "sleep"),
    patch.object(
        program.requests,
        "get",
        return_value=mock_response
    )
):
    (
        ssl_result_2,
        error_type_2,
        error_message_2
    ) = program.check_ssl(original_url_2)

check_result(
    "テスト2: CAPTCHA画面",
    original_url_2,
    ssl_result_2,
    error_type_2,
    error_message_2,
    "CAPTCHA",
    "CAPTCHA"
)


# ============================================================
# 5. 最終結果
# ============================================================

print()
print("========================================")
print("SSL異常系テスト結果")
print("========================================")
print(f"{success_count}/{test_count} テスト成功")

if success_count == test_count:
    print("すべてのテストに成功しました。")
    print(
        "接続失敗・CAPTCHAの場合に、SSLをFalseとし、"
        "元URLと原因を含むログ用の行を作れることを確認しました。"
    )
else:
    print(f"{test_count - success_count}件のテストに失敗しました。")
