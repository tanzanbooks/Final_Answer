"""
test_selenium_wait_before_click.py

提出用1-2.pyの click_shop_homepage() について確認する。

1. REQUEST_INTERVAL が3秒
2. click()の前に sleep(3) を実行
3. 待機後、アクセス直前時間を記録
4. その後に click() を実行

通信と待機は模擬する。提出用1-2.pyは変更しない。
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import Mock, patch


# ============================================================
# 1. 提出用1-2.pyを読み込む
# ============================================================

TEST_DIR = Path(__file__).resolve().parent
PROGRAM_FILE = TEST_DIR.parent / "ex1_web-scraping" / "1-2.py"

spec = importlib.util.spec_from_file_location(
    "program_1_2",
    PROGRAM_FILE
)

if spec is None or spec.loader is None:
    raise ImportError(f"1-2.pyを読み込めません: {PROGRAM_FILE}")

program = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = program
spec.loader.exec_module(program)


# ============================================================
# 2. 実行順序を記録する代用品
# ============================================================

events = []


def fake_sleep(seconds):
    events.append(("sleep", seconds))
    print(f"sleep({seconds})")


def fake_record_preaccess_time(
    shop_url,
    target_url,
    retrieved_at,
    method
):
    events.append(("record_preaccess_time", method))
    print(f"record_preaccess_time({method})")


def fake_click():
    events.append(("click", None))
    driver.current_url = TARGET_URL
    print("element.click()")


# ============================================================
# 3. 偽のリンクとWebDriver
# ============================================================

SHOP_PAGE_URL = "https://r.gnavi.co.jp/test/"
TARGET_URL = "https://shop.example.com/"

element = Mock()
element.is_displayed.return_value = True
element.is_enabled.return_value = True

element.get_attribute.side_effect = lambda name: {
    "outerHTML": (
        '<a href="https://shop.example.com/">'
        "お店のホームページ"
        "</a>"
    ),
    "href": TARGET_URL
}.get(name, "")

element.click.side_effect = fake_click

driver = Mock()
driver.current_window_handle = "main"
driver.window_handles = ["main"]
driver.current_url = SHOP_PAGE_URL
driver.find_elements.return_value = [element]
driver.execute_script.return_value = "complete"


# ============================================================
# 4. 提出用関数を実行
# ============================================================

print()
print("========================================")
print("Selenium クリック前3秒待機テスト")
print("========================================")
print("REQUEST_INTERVAL:", program.REQUEST_INTERVAL)

try:
    with (
        patch.object(
            program.time,
            "sleep",
            side_effect=fake_sleep
        ),
        patch.object(
            program,
            "record_preaccess_time",
            side_effect=fake_record_preaccess_time
        ),
        patch.object(program, "WebDriverWait") as mock_wait
    ):
        # 待機条件を偽のdriverに対して評価する
        wait_instance = mock_wait.return_value
        wait_instance.until.side_effect = (
            lambda condition: condition(driver)
        )

        result = program.click_shop_homepage(
            driver,
            TARGET_URL,
            shop_retrieved_at=100.0
        )

    print()
    print("========================================")
    print("実行された処理の順番")
    print("========================================")

    for number, event in enumerate(events, start=1):
        print(f"{number}: {event}")

    # click()より前の記録だけを調べる
    click_index = next(
        (
            index
            for index, event in enumerate(events)
            if event[0] == "click"
        ),
        None
    )

    sleep_index = next(
        (
            index
            for index, event in enumerate(events)
            if event == ("sleep", 3)
            and (click_index is None or index < click_index)
        ),
        None
    )

    record_index = next(
        (
            index
            for index, event in enumerate(events)
            if event == (
                "record_preaccess_time",
                "クリック"
            )
        ),
        None
    )

    test1 = program.REQUEST_INTERVAL == 3

    test2 = (
        sleep_index is not None
        and click_index is not None
        and sleep_index < click_index
    )

    test3 = (
        sleep_index is not None
        and record_index is not None
        and sleep_index < record_index
    )

    test4 = (
        sleep_index is not None
        and record_index is not None
        and click_index is not None
        and sleep_index < record_index < click_index
        and element.click.call_count == 1
        and result == TARGET_URL
    )

    print()
    print("========================================")
    print("確認結果")
    print("========================================")

    results = [
        ("待機時間の設定が3秒", test1),
        ("click()より前にsleep(3)", test2),
        ("待機後にアクセス直前時間を記録", test3),
        ("sleep → 記録 → clickの順序", test4),
    ]

    for name, passed in results:
        print(f"{name}: {'OK' if passed else 'NG'}")

    success_count = sum(passed for _, passed in results)

    print()
    print("========================================")
    print("最終結果")
    print("========================================")
    print(f"{success_count}/4 テスト成功")

    if success_count == 4:
        print("すべてのテストに成功しました。")
    else:
        print("テストに失敗しました。")

except Exception as error:
    print()
    print("テスト中にエラーが発生しました。")
    print("エラー種類:", type(error).__name__)
    print("エラー内容:", error)
