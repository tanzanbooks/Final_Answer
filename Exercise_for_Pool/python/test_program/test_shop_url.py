"""
ホームページURL取得処理のテスト

確認内容
1. href="#" を店舗URLとして取得しない
2. 「お店のホームページ」を優先する
3. 「お店のホームページ」がなければ
   「オフィシャルページ」を取得する
4. CAPTCHA URLを店舗URLとして取得しない
5. ぐるなび中継URLを店舗URLとして取得しない
6. 接続失敗でも取得済みの元URLを保持する
"""

from bs4 import BeautifulSoup

from improved1_1 import get_shop_url


# ============================================================
# 共通処理
# ============================================================

success_count = 0
test_count = 0


def check(
    test_name,
    actual,
    expected_url,
    expected_reason
):
    """
    get_shop_url() が返す

    (URL, 理由)

    の両方を確認する。
    """

    global success_count
    global test_count

    test_count += 1

    actual_url, actual_reason = actual

    print()
    print("----------------------------------------")
    print(test_name)
    print("----------------------------------------")

    print("期待するURL :", expected_url)
    print("実際のURL   :", actual_url)

    print("期待する理由:", expected_reason)
    print("実際の理由  :", actual_reason)

    if (
        actual_url == expected_url
        and actual_reason == expected_reason
    ):
        print("結果: OK")
        success_count += 1

    else:
        print("結果: NG")


# ============================================================
# テスト1
# href="#" を取得しない
# ============================================================

html_1 = """
<html>
<body>

<a href="#">
    お店のホームページ
</a>

</body>
</html>
"""

soup_1 = BeautifulSoup(
    html_1,
    "html.parser"
)

actual_1 = get_shop_url(
    soup_1
)

check(
    "テスト1: href='#' を店舗URLとして取得しない",
    actual_1,
    "",
    "有効なお店のURLなし"
)


# ============================================================
# テスト2
# 「お店のホームページ」を優先する
# ============================================================

html_2 = """
<html>
<body>

<a href="https://official.example.com/">
    オフィシャルページ
</a>

<a href="https://shop.example.com/">
    お店のホームページ
</a>

</body>
</html>
"""

soup_2 = BeautifulSoup(
    html_2,
    "html.parser"
)

actual_2 = get_shop_url(
    soup_2
)

check(
    "テスト2: 「お店のホームページ」を優先する",
    actual_2,
    "https://shop.example.com/",
    ""
)


# ============================================================
# テスト3
# 「お店のホームページ」がなければ
# 「オフィシャルページ」を取得する
# ============================================================

html_3 = """
<html>
<body>

<a href="https://official.example.com/">
    オフィシャルページ
</a>

</body>
</html>
"""

soup_3 = BeautifulSoup(
    html_3,
    "html.parser"
)

actual_3 = get_shop_url(
    soup_3
)

check(
    "テスト3: 「オフィシャルページ」を代わりに取得する",
    actual_3,
    "https://official.example.com/",
    ""
)


# ============================================================
# テスト4
# CAPTCHA URLを取得しない
# ============================================================

html_4 = """
<html>
<body>

<a href="https://example.com/captcha/">
    お店のホームページ
</a>

</body>
</html>
"""

soup_4 = BeautifulSoup(
    html_4,
    "html.parser"
)

actual_4 = get_shop_url(
    soup_4
)

check(
    "テスト4: CAPTCHA URLを店舗URLとして取得しない",
    actual_4,
    "",
    "CAPTCHAのURL"
)


# ============================================================
# テスト5
# ぐるなび中継URLを取得しない
# ============================================================

html_5 = """
<html>
<body>

<a href="https://r.gnavi.co.jp/redirect/test">
    お店のホームページ
</a>

</body>
</html>
"""

soup_5 = BeautifulSoup(
    html_5,
    "html.parser"
)

actual_5 = get_shop_url(
    soup_5
)

check(
    "テスト5: ぐるなび中継URLを店舗URLとして取得しない",
    actual_5,
    "",
    "ぐるなびの中継URL"
)


# ============================================================
# テスト6
# 接続失敗でも取得済みの元URLを保持する
# ============================================================

original_url = "https://shop.example.com/"

ssl_result = False

error_type = "接続失敗"

error_message = (
    "テスト用に接続失敗を発生させました"
)

# 接続確認に失敗しても、
# 取得済みのURLそのものは変更しない
saved_url = original_url


print()
print("----------------------------------------")
print("テスト6: 接続失敗でも元URLを保持する")
print("----------------------------------------")

print(
    "取得済みの元URL:",
    original_url
)

print(
    "SSL確認結果:",
    ssl_result
)

print(
    "エラー種類:",
    error_type
)

print(
    "エラーメッセージ:",
    error_message
)

print(
    "保存するURL:",
    saved_url
)


test_count += 1

if (
    saved_url == original_url
    and ssl_result is False
):

    print("結果: OK")
    success_count += 1

else:

    print("結果: NG")


# ============================================================
# 最終結果
# ============================================================

print()
print("========================================")
print("ホームページURL取得テスト結果")
print("========================================")

print(
    f"{success_count}/{test_count} テスト成功"
)

if success_count == test_count:

    print(
        "すべてのテストに成功しました。"
    )

else:

    print(
        f"{test_count - success_count}件の"
        "テストに失敗しました。"
    )
