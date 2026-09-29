"""
Selenium「>」ボタンクリックテスト

確認すること：
1. ページ番号「2」はクリックしない
2. ページ下部の「>」ボタンをクリックする
3. クリック後に次ページのHTMLを取得する
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
# 2. テスト用URL
# ============================================================

CURRENT_URL = "https://r.gnavi.co.jp/area/jp/rs/"
NEXT_URL = "https://r.gnavi.co.jp/area/jp/rs/?p=2"


# ============================================================
# 3. ページ番号「2」の偽リンク
# ============================================================

page_number = Mock()
page_number.get_attribute.side_effect = lambda name: {
    "href": NEXT_URL,
    "aria-label": ""
}.get(name, "")

page_number.text = "2"
page_number.find_elements.return_value = []


# ============================================================
# 4. 「>」ボタンの偽リンク
# ============================================================

next_button = Mock()
next_button.get_attribute.side_effect = lambda name: {
    "href": NEXT_URL,
    "aria-label": "次（2）ページを表示"
}.get(name, "")

next_button.text = ""

next_image = Mock()
next_image.get_attribute.return_value = "次（2）ページを表示"
next_button.find_elements.return_value = [next_image]


# ============================================================
# 5. 偽のWebDriver
# ============================================================

driver = Mock()
driver.find_elements.return_value = [
    page_number,
    next_button
]

# 最初は1ページ目にいる
driver.current_url = CURRENT_URL

driver.execute_script.return_value = "complete"
driver.page_source = """
<html>
<body><h1>2ページ目</h1></body>
</html>
"""


def move_to_next_page():
    """「>」ボタンをクリックした場合だけURLを更新する。"""
    driver.current_url = NEXT_URL


next_button.click.side_effect = move_to_next_page


# ============================================================
# 6. テスト実行
# ============================================================

print()
print("========================================")
print("Selenium「>」ボタンクリックテスト")
print("========================================")

with (
    patch.object(program.time, "sleep"),
    patch.object(program, "WebDriverWait") as mock_wait
):
    # 実際のWebDriverWaitの条件式を、偽のdriverで評価する
    wait_instance = mock_wait.return_value
    wait_instance.until.side_effect = lambda condition: condition(driver)

    result = program.click_next_page(driver, NEXT_URL)


# ============================================================
# 7. 各項目の判定
# ============================================================

test1 = not page_number.click.called
test2 = next_button.click.call_count == 1
test3 = (
    driver.current_url == NEXT_URL
    and result is not None
    and "2ページ目" in result.get_text()
)

print()
print("----------------------------------------")
print("テスト1: ページ番号「2」")
print("----------------------------------------")
print("結果:", "OK" if test1 else "NG")
print("クリック回数:", page_number.click.call_count)

print()
print("----------------------------------------")
print("テスト2: 「>」ボタン")
print("----------------------------------------")
print("結果:", "OK" if test2 else "NG")
print("クリック回数:", next_button.click.call_count)

print()
print("----------------------------------------")
print("テスト3: 次ページへの遷移とHTML取得")
print("----------------------------------------")
print("結果:", "OK" if test3 else "NG")
print("クリック後のURL:", driver.current_url)


# ============================================================
# 8. 最終結果
# ============================================================

success_count = sum((test1, test2, test3))

print()
print("========================================")
print("最終結果")
print("========================================")
print(f"{success_count}/3 テスト成功")

if success_count == 3:
    print("すべてのテストに成功しました。")
else:
    print("テストに失敗しました。")
