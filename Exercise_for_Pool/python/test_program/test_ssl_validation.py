"""
SSL証明書検証テスト

本間さんからの指摘：

・httpsで始まるだけでTrueにしない
・証明書検証成功に基づいてTrueにする
・証明書エラーはFalse
・タイムアウトはFalse
・確認できない場合もTrueにしない
・原因を記録できるようにする

1-2.py と 2-2.py の実際の check_ssl() をテストする。
"""

import requests

from unittest.mock import patch, Mock

import improved1_2
import improved2_2

# ============================================================
# 1. 共通設定
# ============================================================

success_count = 0
test_count = 0


def show_result(
    program_name,
    test_name,
    actual,
    expected_ssl,
    expected_error
):
    """
    check_ssl() の結果を確認する。
    """

    global success_count
    global test_count

    test_count += 1

    ssl_result, error_type, message = actual

    print()
    print("----------------------------------------")
    print(f"{program_name}: {test_name}")
    print("----------------------------------------")

    print("SSL結果:", ssl_result)
    print("エラー種類:", error_type)
    print("メッセージ:", message)

    if (
        ssl_result is expected_ssl
        and error_type == expected_error
    ):
        print("結果: OK")
        success_count += 1

    else:
        print("結果: NG")


# ============================================================
# 2. 1つのプログラムについて4種類テストする
# ============================================================

def run_tests(
    program_name,
    module
):

    test_url = "https://shop.example.com/"


    # ========================================================
    # テスト1
    # 正常なHTTPS接続
    # ========================================================

    normal_response = Mock()

    normal_response.url = (
        "https://shop.example.com/"
    )

    normal_response.text = """
    <html>
    <head>
        <title>Test Shop</title>
    </head>
    <body>
        Test Shop
    </body>
    </html>
    """

    normal_response.raise_for_status.return_value = None


    with patch(
        f"{module.__name__}.requests.get",
        return_value=normal_response
    ) as mock_get:

        result = module.check_ssl(
            test_url
        )

        # verify=Trueで呼ばれたか確認
        verify_value = (
            mock_get.call_args.kwargs.get(
                "verify"
            )
        )


    show_result(
        program_name,
        "正常なHTTPS接続",
        result,
        True,
        ""
    )


    print(
        "verifyの設定:",
        verify_value
    )

    if verify_value is True:
        print("証明書検証: 有効")
    else:
        print("証明書検証: NG")


    # ========================================================
    # テスト2
    # HTTPSでも証明書エラーならFalse
    # ========================================================

    with patch(
        f"{module.__name__}.requests.get"
    ) as mock_get:

        mock_get.side_effect = (
            requests.exceptions.SSLError(
                "テスト用の証明書エラー"
            )
        )

        result = module.check_ssl(
            test_url
        )


    show_result(
        program_name,
        "HTTPSだが証明書エラー",
        result,
        False,
        "証明書エラー"
    )


    # ========================================================
    # テスト3
    # HTTPSでもタイムアウトならFalse
    # ========================================================

    with patch(
        f"{module.__name__}.requests.get"
    ) as mock_get:

        mock_get.side_effect = (
            requests.exceptions.Timeout(
                "テスト用のタイムアウト"
            )
        )

        result = module.check_ssl(
            test_url
        )


    show_result(
        program_name,
        "HTTPSだがタイムアウト",
        result,
        False,
        "タイムアウト"
    )


    # ========================================================
    # テスト4
    # HTTPSでも接続エラーならFalse
    # ========================================================

    with patch(
        f"{module.__name__}.requests.get"
    ) as mock_get:

        mock_get.side_effect = (
            requests.exceptions.ConnectionError(
                "テスト用の接続エラー"
            )
        )

        result = module.check_ssl(
            test_url
        )


    show_result(
        program_name,
        "HTTPSだが接続エラー",
        result,
        False,
        "接続エラー"
    )


# ============================================================
# 3. 1-2.pyをテスト
# ============================================================

print()
print("========================================")
print("1-2.py SSL証明書検証テスト")
print("========================================")

run_tests(
    "1-2.py",
    improved1_2
)


# ============================================================
# 4. 2-2.pyをテスト
# ============================================================

print()
print("========================================")
print("2-2.py SSL証明書検証テスト")
print("========================================")

run_tests(
    "2-2.py",
    improved2_2
)


# ============================================================
# 5. 最終結果
# ============================================================

print()
print("========================================")
print("SSL証明書検証テスト 最終結果")
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
        "httpsで始まるだけではTrueにせず、"
    )

    print(
        "証明書検証に成功した場合のみ"
        "Trueになることを確認しました。"
    )

    print()

    print(
        "証明書エラー・タイムアウト・"
        "接続エラーの場合はFalseとなり、"
    )

    print(
        "原因も取得できることを確認しました。"
    )

else:

    print(
        f"{test_count - success_count}件の"
        "テストに失敗しました。"
    )
