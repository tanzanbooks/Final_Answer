from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    WebDriverException,
    StaleElementReferenceException
)

from pathlib import Path
import pandas as pd
import re
import time

# =========================================
# ChromeDriver設定
# =========================================

driver_path = Path(__file__).resolve().parent / "chromedriver.exe"

service = Service(
    executable_path=str(driver_path)
)

options = Options()
options.add_argument("--user-agent=Mozilla/5.0")

driver = webdriver.Chrome(
    service=service,
    options=options
)

# =========================================
# 1店舗の情報を取得する関数
# =========================================
def get_shop_info(gnavi_url):

    # サーバー負荷軽減
    time.sleep(3)

    driver.get(gnavi_url)

    time.sleep(1)


    # =====================================
    # 店舗名
    # =====================================
    shop_name = ""

    h1_elements = driver.find_elements(
        By.TAG_NAME,
        "h1"
    )

    for h1 in h1_elements:

        try:
            text = h1.text.strip()
        except StaleElementReferenceException:
            continue

        if text and text != "ぐるなび":
            shop_name = text
            break


    # =====================================
    # 電話番号
    # =====================================
    tel_numbers = []

    elements = driver.find_elements(
        By.CSS_SELECTOR,
        "span, p, td, dd"
    )

    for element in elements:

        try:

            text = element.text.strip()

            numbers = re.findall(
                r"\d{2,4}-\d{2,4}-\d{3,4}",
                text
            )

            tel_numbers.extend(numbers)

        except StaleElementReferenceException:
            continue


    # 重複削除
    tel_numbers = list(
        dict.fromkeys(tel_numbers)
    )

    phone = (
        tel_numbers[0]
        if tel_numbers
        else ""
    )


    # =====================================
    # メールアドレス
    # =====================================
    email = ""

    try:

        body_text = driver.find_element(
            By.TAG_NAME,
            "body"
        ).text

        email_match = re.search(
            r"[A-Za-z0-9._%+-]+@"
            r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            body_text
        )

        if email_match:
            email = email_match.group()

    except Exception:
        pass


    # =====================================
    # 住所取得
    # =====================================
    address_text = ""

    address_elements = driver.find_elements(
        By.CSS_SELECTOR,
        "td, dd"
    )

    for element in address_elements:

        try:

            text = element.text.replace(
                "\n",
                " "
            ).strip()

            if re.search(
                r"〒?\d{3}-\d{4}\s*"
                r"(北海道|東京都|京都府|大阪府|.{2,3}県)",
                text
            ):

                address_text = text
                break

        except StaleElementReferenceException:
            continue


    # =====================================
    # 住所整形
    # =====================================
    address_text = re.sub(
        r"〒?\d{3}-\d{4}\s*",
        "",
        address_text
    )

    address_text = address_text.replace(
        "大きな地図で見る",
        ""
    )

    address_text = address_text.replace(
        "地図印刷",
        ""
    )

    address_text = re.sub(
        r"\s+",
        " ",
        address_text
    ).strip()


    # =====================================
    # 都道府県
    # =====================================
    prefecture = ""

    pref_match = re.match(
        r"^(北海道|東京都|京都府|大阪府|.{2,3}県)",
        address_text
    )

    if pref_match:
        prefecture = pref_match.group(1)


    remaining_address = address_text

    if prefecture:

        remaining_address = (
            remaining_address[
                len(prefecture):
            ]
        )


    # =====================================
    # 市区町村
    # 四日市市などにも対応
    # =====================================
    city = ""

    city_match = re.match(
        r"^("
        r".+?市市"
        r"|.+?市.+?区"
        r"|.+?市"
        r"|.+?区"
        r"|.+?町"
        r"|.+?村"
        r")",
        remaining_address
    )

    if city_match:
        city = city_match.group(1)


    # 市区町村を除く
    street_and_building = (
        remaining_address
    )

    if city:

        street_and_building = (
            street_and_building[
                len(city):
            ]
        )


    # =====================================
    # 番地・建物名
    # =====================================
    street = ""
    building = ""

    address_match = re.match(
        r"^(\S+?[\d０-９]+"
        r"(?:[-－ー]\d+)*)"
        r"(?:\s+(.+))?$",
        street_and_building
    )

    if address_match:

        street = address_match.group(1)

        if address_match.group(2):
            building = address_match.group(2)

    else:
        street = street_and_building


    # =====================================
    # オフィシャルURL
    # =====================================
    official_url = ""

    official_link = None

    links = driver.find_elements(
        By.TAG_NAME,
        "a"
    )

    for link in links:

        try:

            text = link.text.strip()

            if (
                "オフィシャル" in text
                or "ホームページ" in text
            ):

                official_link = link
                break

        except StaleElementReferenceException:
            continue


    # =====================================
    # 実際にリンクをブラウザで開く
    # =====================================
    if official_link:

        try:

            old_handles = driver.window_handles

            driver.execute_script(
                "arguments[0].scrollIntoView();",
                official_link
            )

            time.sleep(1)

            driver.execute_script(
                "arguments[0].click();",
                official_link
            )

            time.sleep(3)


            new_handles = driver.window_handles


            # 新しいタブが開いた場合
            if len(new_handles) > len(old_handles):

                new_handle = [
                    handle
                    for handle in new_handles
                    if handle not in old_handles
                ][0]

                driver.switch_to.window(
                    new_handle
                )


            # 実際に表示されたURL
            official_url = (
                driver.current_url
            )


            # 新しいタブなら閉じて元へ戻す
            if len(new_handles) > len(old_handles):

                driver.close()

                driver.switch_to.window(
                    old_handles[0]
                )


        except WebDriverException:

            official_url = ""


    # =====================================
    # SSL判定
    # =====================================
    ssl = False

    if official_url.startswith(
        "https://"
    ):
        ssl = True


    # =====================================
    # 1店舗分を辞書で返す
    # =====================================
    return {
        "店舗名": shop_name,
        "電話番号": phone,
        "メールアドレス": email,
        "都道府県": prefecture,
        "市区町村": city,
        "番地": street,
        "建物名": building,
        "URL": official_url,
        "SSL": ssl
    }


# =========================================
# 検索結果ページを開く
# =========================================
search_url = (
    "https://r.gnavi.co.jp/area/jp/rs/"
)

time.sleep(3)

driver.get(search_url)


# =========================================
# 店舗URLを50件取得
# =========================================
shop_urls = []


while len(shop_urls) < 50:

    time.sleep(3)

    print()
    print(
        "現在の検索ページ:",
        driver.current_url
    )


    links = driver.find_elements(
        By.TAG_NAME,
        "a"
    )


    # =====================================
    # 店舗URL抽出
    # =====================================
    for link in links:

        try:

            href = link.get_attribute(
                "href"
            )

        except StaleElementReferenceException:

            continue


        if not href:
            continue


        if re.match(
            r"^https://r\.gnavi\.co\.jp/"
            r"[A-Za-z0-9]+/?$",
            href
        ):

            if href not in shop_urls:

                shop_urls.append(href)

                print(
                    len(shop_urls),
                    href
                )

                if len(shop_urls) >= 50:
                    break


    # =====================================
    # 50件取得したら終了
    # =====================================
    if len(shop_urls) >= 50:
        break


    # =====================================
    # 現在ページ番号
    # =====================================
    page_match = re.search(
        r"[?&]p=(\d+)",
        driver.current_url
    )

    if page_match:
        current_page = int(
            page_match.group(1)
        )
    else:
        current_page = 1


    next_page = (
        current_page + 1
    )


    # =====================================
    # 次ページ「>」を探す
    # =====================================
    next_button = None

    links = driver.find_elements(
        By.TAG_NAME,
        "a"
    )


    for link in links:

        try:

            href = link.get_attribute(
                "href"
            )

            text = link.text.strip()

            aria_label = link.get_attribute(
                "aria-label"
            )

        except StaleElementReferenceException:

            continue


        if not href:
            continue


        if (
            text == ">"
            or aria_label == "次へ"
        ):

            next_button = link
            break


    # =====================================
    # > が取得できない場合
    # 次ページURLを持つリンクを探す
    # =====================================
    if next_button is None:

        for link in links:

            try:

                href = link.get_attribute(
                    "href"
                )

            except StaleElementReferenceException:

                continue


            if not href:
                continue


            if (
                f"?p={next_page}" in href
                or
                f"&p={next_page}" in href
            ):

                next_button = link
                break


    # =====================================
    # 次ページがない場合
    # =====================================
    if next_button is None:

        print(
            "次ページボタンが"
            "見つかりませんでした。"
        )

        break


    # =====================================
    # 「>」をクリック
    # =====================================
    old_url = driver.current_url

    driver.execute_script(
        "arguments[0].scrollIntoView();",
        next_button
    )

    time.sleep(1)

    driver.execute_script(
        "arguments[0].click();",
        next_button
    )

    time.sleep(3)


    print(
        "ページ移動:",
        old_url,
        "→",
        driver.current_url
    )


print()
print(
    "店舗URL取得完了:",
    len(shop_urls),
    "件"
)


# =========================================
# 50店舗の詳細情報を取得
# =========================================
results = []


for i, url in enumerate(
    shop_urls,
    start=1
):

    print()
    print(
        f"{i}/{len(shop_urls)}"
        " 店舗目を取得中"
    )

    print(url)


    try:

        shop_data = (
            get_shop_info(url)
        )

        results.append(
            shop_data
        )

        print(
            "取得完了:",
            shop_data["店舗名"]
        )


    except Exception as e:

        print(
            "取得エラー:",
            url,
            e
        )

        results.append(
            {
                "店舗名": "",
                "電話番号": "",
                "メールアドレス": "",
                "都道府県": "",
                "市区町村": "",
                "番地": "",
                "建物名": "",
                "URL": "",
                "SSL": False
            }
        )


# =========================================
# DataFrame作成
# =========================================
columns = [
    "店舗名",
    "電話番号",
    "メールアドレス",
    "都道府県",
    "市区町村",
    "番地",
    "建物名",
    "URL",
    "SSL"
]


df = pd.DataFrame(
    results,
    columns=columns
)


# =========================================
# CSV保存
# =========================================
df.to_csv(
    "1-2.csv",
    index=False,
    encoding="utf-8-sig"
)


# =========================================
# 最終表示
# =========================================
print()
print("============================")
print("処理完了")
print("============================")

print(
    "取得店舗数:",
    len(df)
)

print()

print(
    df.head()
)

print()

print(
    "1-2.csv を保存しました。"
)


# =========================================
# Chrome終了
# =========================================
driver.quit()
