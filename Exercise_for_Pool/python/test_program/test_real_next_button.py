"""
test_real_next_button.py

提出用 1-2.py の関数を使い、実サイトで
「次」ボタンをクリックして次ページへ進めるか確認する。

クリック前に対象を黄色の背景と赤枠で強調し、
5秒間、目視で確認できるようにする。
"""

import importlib.util
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


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
# 2. 設定
# ============================================================

START_URL = "https://r.gnavi.co.jp/area/jp/rs/"


def find_next_button(driver, next_url):
    """
    提出用 click_next_page() と同じ条件で、
    クリック対象になる「次」ボタンを探す。
    """

    for element in driver.find_elements(By.TAG_NAME, "a"):
        href = element.get_attribute("href")

        if href != next_url:
            continue

        label = element.get_attribute("aria-label") or ""
        images = element.find_elements(By.TAG_NAME, "img")

        image_alt = (
            images[0].get_attribute("alt") or ""
            if images else ""
        )

        visible_text = element.text.strip()

        is_next_button = (
            label.startswith("次")
            or image_alt.startswith("次")
            or visible_text in (">", "＞", "次へ")
        )

        if is_next_button:
            return element, visible_text, label, image_alt

    return None, "", "", ""


# ============================================================
# 3. 実サイトで確認
# ============================================================

driver = None

try:
    driver = webdriver.Chrome()
    driver.set_page_load_timeout(30)

    print("===== 実サイト「次」ボタンクリックテスト =====")
    print("最初のページ:", START_URL)

    # 提出用1-2.pyの関数で1ページ目を取得。
    # この関数内でアクセス前に3秒待機する。
    first_soup = program.get_soup(driver, START_URL)

    if first_soup is None:
        raise RuntimeError("1ページ目を取得できませんでした。")

    before_url = driver.current_url
    print("クリック前URL:", before_url)

    # 提出用1-2.pyの関数で「次」のリンク先を取得
    next_url = program.get_next_page_url(
        first_soup,
        before_url
    )

    if not next_url:
        raise RuntimeError("次ページのリンク先を取得できませんでした。")

    print("「次」ボタンのリンク先:", next_url)

    # 提出用のクリック関数と同じ条件で、目視用の対象を探す
    (
        target,
        visible_text,
        label,
        image_alt
    ) = find_next_button(driver, next_url)

    if target is None:
        raise RuntimeError(
            "画面上に「次」ボタンのクリック対象が見つかりません。"
        )

    print()
    print("===== クリック対象 =====")
    print("表示文字:", repr(visible_text))
    print("aria-label:", repr(label))
    print("画像alt:", repr(image_alt))
    print("リンク先:", target.get_attribute("href"))

    if visible_text == "2":
        raise RuntimeError(
            "ページ番号「2」を選択したため中止します。"
        )

    # 画面中央に移動して、黄色の背景と赤枠で強調
    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center'});",
        target
    )

    driver.execute_script(
        "arguments[0].style.border = '5px solid red';"
        "arguments[0].style.backgroundColor = 'yellow';",
        target
    )

    print()
    print("黄色の背景と赤枠で強調した対象を5秒間表示します。")
    time.sleep(5)

    # 提出用1-2.pyの関数でクリック。
    # 関数内でクリック直前に3秒待機する。
    next_soup = program.click_next_page(driver, next_url)

    if next_soup is None:
        raise RuntimeError(
            "提出用関数による「次」ボタンのクリックに失敗しました。"
        )

    WebDriverWait(driver, 30).until(
        lambda browser: (
            browser.current_url == next_url
            and browser.execute_script(
                "return document.readyState"
            ) == "complete"
        )
    )

    after_url = driver.current_url
    print()
    print("クリック後URL:", after_url)

    if after_url == next_url and next_soup.find("html"):
        print("テスト結果: OK")
        print(
            "提出用1-2.pyの関数で「次」ボタンをクリックし、"
            "次ページのURLとHTMLを確認しました。"
        )
    else:
        print("テスト結果: NG")
        print(
            "次ページのURLまたはHTMLを確認できませんでした。"
        )

    print("クリック後の画面を5秒間表示します。")
    time.sleep(5)

except Exception as error:
    print()
    print("テスト結果: NG")
    print("エラー種類:", type(error).__name__)
    print("エラー内容:", error)

    if driver is not None:
        print("確認のため画面を5秒間表示します。")
        time.sleep(5)

finally:
    if driver is not None:
        driver.quit()
