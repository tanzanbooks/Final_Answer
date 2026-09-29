"""
SSL異常時のCSVログ保存テスト

提出用 1-1.py の check_ssl() に対し、
接続失敗とCAPTCHA画面を模擬する。

元のURL・エラー種類・メッセージを
テスト専用CSVに保存し、読み直して確認する。
"""

import csv
import importlib.util
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import requests


# ============================================================
# 1. 設定と1-1.pyの読み込み
# ============================================================

TEST_DIR = Path(__file__).resolve().parent
PROGRAM_FILE = TEST_DIR.parent / "ex1_web-scraping" / "1-1.py"
TEST_OUTPUT_FILE = TEST_DIR / "test_ssl_errors_output.csv"

spec = importlib.util.spec_from_file_location(
    "program_1_1",
    PROGRAM_FILE
)

if spec is None or spec.loader is None:
    raise ImportError(f"1-1.pyを読み込めません: {PROGRAM_FILE}")

program = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = program
spec.loader.exec_module(program)

error_rows = []
success_count = 0
test_count = 0


def add_error_row(url, error_type, message):
    """テスト専用CSVに保存する1行を作る。"""
    error_rows.append({
        "発生日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "店舗URL": url,
        "エラー種類": error_type,
        "エラーメッセージ": message
    })


# ============================================================
# 2. 接続失敗テスト
# ============================================================

print()
print("========================================")
print("テスト1: 接続失敗")
print("========================================")

shop_url_1 = "https://shop.example.com/"

with (
    patch.object(program.time, "sleep"),
    patch.object(program.requests, "get") as mock_get
):
    mock_get.side_effect = requests.exceptions.ConnectionError(
        "テスト用の接続失敗"
    )
    ssl_result_1, error_type_1, error_message_1 = (
        program.check_ssl(shop_url_1)
    )

add_error_row(shop_url_1, error_type_1, error_message_1)

print("元のURL:", shop_url_1)
print("SSL結果:", ssl_result_1)
print("エラー種類:", error_type_1)
print("エラーメッセージ:", error_message_1)

test_count += 1

if (
    ssl_result_1 is False
    and error_type_1 == "接続エラー"
    and "テスト用の接続失敗" in error_message_1
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

shop_url_2 = "https://shop2.example.com/"

mock_response = Mock()
mock_response.url = shop_url_2
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
    ssl_result_2, error_type_2, error_message_2 = (
        program.check_ssl(shop_url_2)
    )

add_error_row(shop_url_2, error_type_2, error_message_2)

print("元のURL:", shop_url_2)
print("SSL結果:", ssl_result_2)
print("エラー種類:", error_type_2)
print("エラーメッセージ:", error_message_2)

test_count += 1

if (
    ssl_result_2 is False
    and error_type_2 == "CAPTCHA"
    and "CAPTCHA" in error_message_2
):
    print("判定結果: OK")
    success_count += 1
else:
    print("判定結果: NG")


# ============================================================
# 4. テスト専用CSVへ保存
# ============================================================

fieldnames = [
    "発生日時",
    "店舗URL",
    "エラー種類",
    "エラーメッセージ"
]

with TEST_OUTPUT_FILE.open(
    "w",
    newline="",
    encoding="utf-8-sig"
) as file:
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(error_rows)

print()
print("テスト用CSVへ保存:", TEST_OUTPUT_FILE)


# ============================================================
# 5. CSVを読み直して確認
# ============================================================

with TEST_OUTPUT_FILE.open(
    "r",
    newline="",
    encoding="utf-8-sig"
) as file:
    saved_rows = list(csv.DictReader(file))

print("保存されたエラー件数:", len(saved_rows))

for index, row in enumerate(saved_rows, start=1):
    print()
    print(f"【{index}件目】")
    print("発生日時:", row["発生日時"])
    print("店舗URL:", row["店舗URL"])
    print("エラー種類:", row["エラー種類"])
    print("エラーメッセージ:", row["エラーメッセージ"])


# ============================================================
# 6. 保存結果の判定
# ============================================================

csv_test_ok = (
    len(saved_rows) == 2
    and saved_rows[0]["店舗URL"] == shop_url_1
    and saved_rows[0]["エラー種類"] == "接続エラー"
    and "テスト用の接続失敗"
        in saved_rows[0]["エラーメッセージ"]
    and saved_rows[1]["店舗URL"] == shop_url_2
    and saved_rows[1]["エラー種類"] == "CAPTCHA"
    and "CAPTCHA" in saved_rows[1]["エラーメッセージ"]
)

test_count += 1

if csv_test_ok:
    print()
    print("CSV保存結果: OK")
    success_count += 1
else:
    print()
    print("CSV保存結果: NG")


# ============================================================
# 7. 最終結果
# ============================================================

print()
print("========================================")
print("異常系ログ保存テスト 最終結果")
print("========================================")
print(f"{success_count}/{test_count} テスト成功")
print("テストCSV:", TEST_OUTPUT_FILE)

if success_count == test_count:
    print("すべてのテストに成功しました。")
else:
    print(f"{test_count - success_count}件のテストに失敗しました。")
