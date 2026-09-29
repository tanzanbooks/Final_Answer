"""
SSL証明書検証テスト

提出用の 1-2.py と 2-2.py の check_ssl() を、
模擬した通信結果で確認する。
"""

from pathlib import Path
import importlib.util
import sys
from unittest.mock import Mock, patch

import requests


# ============================================================
# 1. 提出用プログラムを読み込む
# ============================================================

TEST_DIR = Path(__file__).resolve().parent
PYTHON_DIR = TEST_DIR.parent


def load_program(module_name, file_path):
    """ファイル名にハイフンがあるPythonファイルを読み込む。"""
    if not file_path.is_file():
        raise FileNotFoundError(f"提出用プログラムが見つかりません: {file_path}")

    spec = importlib.util.spec_from_file_location(module_name, file_path)

    if spec is None or spec.loader is None:
        raise ImportError(f"読み込めません: {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    return module


program_1_2 = load_program(
    "program_1_2",
    PYTHON_DIR / "ex1_web-scraping" / "1-2.py"
)

program_2_2 = load_program(
    "program_2_2",
    PYTHON_DIR / "ex2_docker_and_db" / "2-2.py"
)


# ============================================================
# 2. 結果表示
# ============================================================

success_count = 0
test_count = 0


def show_result(
    program_name,
    test_name,
    actual,
    expected_ssl,
    expected_error,
    verify_value
):
    """SSL結果、エラー種類、証明書検証設定を確認する。"""
    global success_count, test_count

    test_count += 1
    ssl_result, error_type, message = actual

    # 正常時も異常時も、通信時に証明書検証が有効であることを確認する
    passed = (
        ssl_result is expected_ssl
        and error_type == expected_error
        and verify_value is True
        and (expected_ssl is True or bool(message))
    )

    print()
    print("----------------------------------------")
    print(f"{program_name}: {test_name}")
    print("----------------------------------------")
    print("SSL結果:", ssl_result)
    print("エラー種類:", error_type)
    print("メッセージ:", message)
    print("verifyの設定:", verify_value)
    print("結果:", "OK" if passed else "NG")

    if passed:
        success_count += 1


# ============================================================
# 3. 1つのプログラムについて4種類を確認
# ============================================================

def run_tests(program_name, module):
    test_url = "https://shop.example.com/"

    normal_response = Mock()
    normal_response.url = test_url
    normal_response.text = (
        "<html><head><title>Test Shop</title></head>"
        "<body>Test Shop</body></html>"
    )
    normal_response.raise_for_status.return_value = None

    cases = [
        (
            "正常なHTTPS接続",
            normal_response,
            None,
            True,
            ""
        ),
        (
            "HTTPSだが証明書エラー",
            None,
            requests.exceptions.SSLError(
                "テスト用の証明書エラー"
            ),
            False,
            "証明書エラー"
        ),
        (
            "HTTPSだがタイムアウト",
            None,
            requests.exceptions.Timeout(
                "テスト用のタイムアウト"
            ),
            False,
            "タイムアウト"
        ),
        (
            "HTTPSだが接続エラー",
            None,
            requests.exceptions.ConnectionError(
                "テスト用の接続エラー"
            ),
            False,
            "接続エラー"
        )
    ]

    for (
        test_name,
        mock_response,
        mock_error,
        expected_ssl,
        expected_error
    ) in cases:

        # 実際の通信と3秒待機を、このテスト中だけ置き換える
        with (
            patch.object(module.time, "sleep"),
            patch.object(module.requests, "get") as mock_get
        ):
            if mock_error is None:
                mock_get.return_value = mock_response
            else:
                mock_get.side_effect = mock_error

            actual = module.check_ssl(test_url)

            verify_value = (
                mock_get.call_args.kwargs.get("verify")
                if mock_get.call_args is not None
                else None
            )

        show_result(
            program_name,
            test_name,
            actual,
            expected_ssl,
            expected_error,
            verify_value
        )


# ============================================================
# 4. 実行
# ============================================================

print("===== 1-2.py SSL証明書検証テスト =====")
run_tests("1-2.py", program_1_2)

print()
print("===== 2-2.py SSL証明書検証テスト =====")
run_tests("2-2.py", program_2_2)

print()
print("========================================")
print("SSL証明書検証テスト 最終結果")
print("========================================")
print(f"{success_count}/{test_count} テスト成功")

if success_count == test_count:
    print("すべてのテストに成功しました。")
else:
    print(f"{test_count - success_count}件のテストに失敗しました。")
