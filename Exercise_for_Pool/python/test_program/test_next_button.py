"""
Selenium「>」ボタンクリックテスト

確認すること：
1. ページ番号「2」はクリックしない
2. ページ下部の「>」ボタンをクリックする
3. 「>」のリンク先へ遷移する
"""

from unittest.mock import Mock, patch

import improved1_2


# ============================================================
# 1. テスト用URL
# ============================================================

CURRENT_URL = (
    "https://r.gnavi.co.jp/area/jp/rs/"
)

NEXT_URL = (
    "https://r.gnavi.co.jp/area/jp/rs/?p=2"
)


# ============================================================
# 2. ページ番号「2」の偽リンク
# ============================================================

page_number = Mock()

page_number.get_attribute.side_effect = (
    lambda name: {
        "href": NEXT_URL,
        "aria-label": ""
    }.get(name, "")
)

page_number.text = "2"

page_number.find_elements.return_value = []


# ============================================================
# 3. 「>」ボタンの偽リンク
# ============================================================

next_button = Mock()

next_button.get_attribute.side_effect = (
    lambda name: {
        "href": NEXT_URL,
        "aria-label": "次（2）ページを表示"
    }.get(name, "")
)

next_button.text = ""

next_image = Mock()

next_image.get_attribute.return_value = (
    "次（2）ページを表示"
)

next_button.find_elements.return_value = [
    next_image
]


# ============================================================
# 4. 偽のWebDriver
# ============================================================

driver = Mock()

driver.find_elements.return_value = [
    page_number,
    next_button
]

driver.current_url = NEXT_URL

driver.execute_script.return_value = (
    "complete"
)

driver.page_source = """
<html>
<body>
    <h1>2ページ目</h1>
</body>
</html>
"""


# ============================================================
# 5. テスト実行
# ============================================================

print()
print("========================================")
print("Selenium「>」ボタンクリックテスト")
print("========================================")


# 3秒待機は今回のテスト対象ではないので、
# 実際には待たないようにする
with patch(
    "improved1_2.time.sleep"
):

    # WebDriverWaitもテスト用に置き換える
    with patch(
        "improved1_2.WebDriverWait"
    ) as mock_wait:

        wait_instance = Mock()

        mock_wait.return_value = (
            wait_instance
        )

        wait_instance.until.return_value = (
            True
        )

        result = (
            improved1_2.click_next_page(
                driver,
                NEXT_URL
            )
        )


# ============================================================
# 6. ページ番号「2」がクリックされなかったか
# ============================================================

print()
print("----------------------------------------")
print("テスト1: ページ番号「2」")
print("----------------------------------------")


if page_number.click.called:

    print(
        "結果: NG"
    )

    print(
        "ページ番号「2」が"
        "クリックされています。"
    )

    test1 = False

else:

    print(
        "結果: OK"
    )

    print(
        "ページ番号「2」は"
        "クリックされていません。"
    )

    test1 = True


# ============================================================
# 7. 「>」ボタンがクリックされたか
# ============================================================

print()
print("----------------------------------------")
print("テスト2: 「>」ボタン")
print("----------------------------------------")


if next_button.click.called:

    print(
        "結果: OK"
    )

    print(
        "「>」ボタンが"
        "クリックされました。"
    )

    test2 = True

else:

    print(
        "結果: NG"
    )

    print(
        "「>」ボタンが"
        "クリックされていません。"
    )

    test2 = False


# ============================================================
# 8. 次ページのHTMLを取得できたか
# ============================================================

print()
print("----------------------------------------")
print("テスト3: 次ページ取得")
print("----------------------------------------")


if (
    result is not None
    and "2ページ目"
    in result.get_text()
):

    print(
        "結果: OK"
    )

    print(
        "クリック後の"
        "2ページ目を取得しました。"
    )

    test3 = True

else:

    print(
        "結果: NG"
    )

    test3 = False


# ============================================================
# 9. 最終結果
# ============================================================

print()
print("========================================")
print("最終結果")
print("========================================")


success_count = sum(
    [
        test1,
        test2,
        test3
    ]
)


print(
    f"{success_count}/3 テスト成功"
)


if success_count == 3:

    print(
        "すべてのテストに成功しました。"
    )

    print()

    print(
        "ページ番号「2」ではなく、"
    )

    print(
        "指定された「>」ボタンを"
        "クリックすることを確認しました。"
    )

else:

    print(
        "テストに失敗しました。"
    )
