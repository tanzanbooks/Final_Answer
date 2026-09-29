"""
test_selenium_wait_before_click.py

【7. Seleniumのクリック前にも3秒待機する】

確認内容
1. REQUEST_INTERVAL が3秒である
2. click()より前に sleep(3) が実行される
3. 待機後にアクセス直前時間が記録される
4. その後に click() が実行される

提出用 improved1_2.py は変更しない。
"""

from unittest.mock import Mock, patch

import improved1_2


# ============================================================
# 実行順序を記録する
# ============================================================

events = []


# ============================================================
# sleep() の代用品
# 実際には待たず、何秒待つ指定なのかを記録する
# ============================================================

def fake_sleep(seconds):

    events.append(
        ("sleep", seconds)
    )

    print(
        f"sleep({seconds})"
    )


# ============================================================
# record_preaccess_time() の代用品
# ============================================================

def fake_record_preaccess_time(
    shop_url,
    target_url,
    retrieved_at,
    method
):

    events.append(
        ("record_preaccess_time", method)
    )

    print(
        "record_preaccess_time()"
    )


# ============================================================
# click() の代用品
# ============================================================

def fake_click():

    events.append(
        ("click", None)
    )

    print(
        "element.click()"
    )


# ============================================================
# テスト用URL
# ============================================================

SHOP_PAGE_URL = (
    "https://r.gnavi.co.jp/test/"
)

TARGET_URL = (
    "https://shop.example.com/"
)


# ============================================================
# テスト用の<a>要素
# ============================================================

element = Mock()

element.is_displayed.return_value = True
element.is_enabled.return_value = True

element.get_attribute.side_effect = (
    lambda name: {
        "outerHTML":
            '<a href="https://shop.example.com/">'
            'お店のホームページ'
            '</a>',
        "href":
            TARGET_URL
    }.get(name, "")
)

element.click.side_effect = (
    fake_click
)


# ============================================================
# テスト用WebDriver
# ============================================================

driver = Mock()

driver.current_window_handle = "main"

driver.window_handles = [
    "main"
]

driver.current_url = (
    SHOP_PAGE_URL
)

driver.find_elements.return_value = [
    element
]

driver.execute_script.return_value = (
    "complete"
)


# ============================================================
# decode_shop_link() の代用品
#
# HTML解析そのものではなく、
# 今回はクリック前待機だけをテストする。
# ============================================================

def fake_decode_shop_link(html):

    return TARGET_URL


# ============================================================
# テスト開始
# ============================================================

print()
print(
    "========================================"
)
print(
    "Selenium クリック前3秒待機テスト"
)
print(
    "========================================"
)


# ============================================================
# REQUEST_INTERVAL の確認
# ============================================================

print()
print(
    "REQUEST_INTERVAL:",
    improved1_2.REQUEST_INTERVAL
)


# ============================================================
# 本番関数を実行
# ============================================================

try:

    with patch(
        "improved1_2.time.sleep",
        side_effect=fake_sleep
    ):

        with patch(
            "improved1_2.record_preaccess_time",
            side_effect=fake_record_preaccess_time
        ):

            with patch(
                "improved1_2.decode_shop_link",
                side_effect=fake_decode_shop_link
            ):

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

                    # ----------------------------------------
                    # 店舗ページを取得した時刻の代用品
                    #
                    # 今回は時間そのものではなく、
                    # sleep → record → click の順序を確認する
                    # ----------------------------------------

                    shop_retrieved_at = 100.0

                    result = (
                        improved1_2.click_shop_homepage(
                            driver,
                            TARGET_URL,
                            shop_retrieved_at
                        )
                    )


    # ========================================================
    # 実行順序を表示
    # ========================================================

    print()
    print(
        "========================================"
    )
    print(
        "実行された処理の順番"
    )
    print(
        "========================================"
    )

    for number, event in enumerate(
        events,
        start=1
    ):

        print(
            f"{number}: {event}"
        )


    # ========================================================
    # テスト1
    # REQUEST_INTERVAL == 3
    # ========================================================

    print()
    print(
        "----------------------------------------"
    )
    print(
        "テスト1: 待機時間の設定"
    )
    print(
        "----------------------------------------"
    )

    test1 = (
        improved1_2.REQUEST_INTERVAL
        == 3
    )

    if test1:

        print(
            "OK: REQUEST_INTERVALは3秒です。"
        )

    else:

        print(
            "NG: REQUEST_INTERVALが"
            "3秒ではありません。"
        )


    # ========================================================
    # clickの位置を取得
    # ========================================================

    click_index = None

    for index, event in enumerate(events):

        if event[0] == "click":

            click_index = index

            break


    # ========================================================
    # clickより前にあるsleep(3)を探す
    # ========================================================

    sleep_before_click_index = None

    if click_index is not None:

        for index, event in enumerate(
            events[:click_index]
        ):

            if (
                event[0] == "sleep"
                and event[1] >= 3
            ):

                sleep_before_click_index = index


    # ========================================================
    # テスト2
    # click()より前に3秒待機しているか
    # ========================================================

    print()
    print(
        "----------------------------------------"
    )
    print(
        "テスト2: click()前の3秒待機"
    )
    print(
        "----------------------------------------"
    )

    test2 = (
        sleep_before_click_index
        is not None
    )

    if test2:

        print(
            "OK: click()より前に"
            "3秒待機しています。"
        )

    else:

        print(
            "NG: click()より前の"
            "3秒待機を確認できません。"
        )


    # ========================================================
    # record_preaccess_time の位置
    # ========================================================

    record_index = None

    for index, event in enumerate(events):

        if (
            event[0]
            == "record_preaccess_time"
        ):

            record_index = index

            break


    # ========================================================
    # テスト3
    # sleep → record の順番
    # ========================================================

    print()
    print(
        "----------------------------------------"
    )
    print(
        "テスト3: 待機後にアクセス直前時間を記録"
    )
    print(
        "----------------------------------------"
    )

    test3 = (
        sleep_before_click_index
        is not None
        and record_index is not None
        and sleep_before_click_index
        < record_index
    )

    if test3:

        print(
            "OK: 3秒待機の後に"
            "アクセス直前時間を記録しています。"
        )

    else:

        print(
            "NG: 処理順序が違います。"
        )


    # ========================================================
    # テスト4
    # sleep → record → click の順番
    # ========================================================

    print()
    print(
        "----------------------------------------"
    )
    print(
        "テスト4: 全体の処理順序"
    )
    print(
        "----------------------------------------"
    )

    test4 = (
        sleep_before_click_index
        is not None
        and record_index is not None
        and click_index is not None
        and sleep_before_click_index
        < record_index
        < click_index
    )

    if test4:

        print(
            "OK: 処理順序は"
        )

        print(
            "3秒待機"
        )

        print(
            "↓"
        )

        print(
            "アクセス直前時間を記録"
        )

        print(
            "↓"
        )

        print(
            "click()"
        )

        print(
            "です。"
        )

    else:

        print(
            "NG: 正しい順序ではありません。"
        )


    # ========================================================
    # 最終結果
    # ========================================================

    print()
    print(
        "========================================"
    )
    print(
        "最終結果"
    )
    print(
        "========================================"
    )

    success_count = sum(
        [
            test1,
            test2,
            test3,
            test4
        ]
    )

    print(
        f"{success_count}/4 テスト成功"
    )

    if success_count == 4:

        print()
        print(
            "すべてのテストに成功しました。"
        )

        print()
        print(
            "Seleniumによる店舗ホームページへの"
        )

        print(
            "クリックでは、アクセスを発生させる"
        )

        print(
            "click()より前に3秒待機することを"
        )

        print(
            "確認しました。"
        )

    else:

        print()
        print(
            "テストに失敗しました。"
        )


except Exception as error:

    print()
    print(
        "========================================"
    )
    print(
        "テスト中にエラーが発生しました"
    )
    print(
        "========================================"
    )

    print(
        type(error).__name__
    )

    print(
        str(error)
    )
