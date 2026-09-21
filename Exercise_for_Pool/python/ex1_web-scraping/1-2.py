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
import requests

# =========================================
# ChromeDriver設定
# =========================================

driver_path = Path(__file__).resolve().parent / "chromedriver.exe"

service = Service(
    executable_path=str(driver_path)
)

headers = {"User-Agent": "Mozilla/5.0"}

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

    # 「お店に直接メールする」の
    # mailto: だけを取得する
    # ページ本文中の別メールは取得しない
    links = driver.find_elements(
        By.TAG_NAME,
        "a"
    )

    for link in links:

        try:

            href = (
                link.get_attribute("href")
                or ""
            ).strip()

            link_text = (
                link.text
                or ""
            ).strip()

            if (
                href.lower().startswith("mailto:")
                and "お店に直接メールする" in link_text
            ):

                email = (
                    href[7:]
                    .split("?")[0]
                    .strip()
                )

                break

        except StaleElementReferenceException:
            continue


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

        remaining_address = (
            address_text[len(prefecture):]
        )

    else:

        remaining_address = address_text


    # =====================================
    # 建物名
    # =====================================
    parts = remaining_address.split(
        " ",
        1
    )

    main_address = parts[0]

    building = (
        parts[1]
        if len(parts) == 2
        else ""
    )


    # =====================================
    # 市区町村（町名まで）・番地
    # =====================================
    city = ""
    street = ""

    # 例：
    # 北海道旭川市2条通8-569-1
    # → 旭川市 / 2条通8-569-1
    special_match = re.match(
        r"^(.+?市)(\d+条(?:通)?\d+(?:[-－ー]\d+)*)$",
        main_address
    )

    if special_match:

        city = special_match.group(1)
        street = special_match.group(2)

    else:

        # 原則として番地の数字が始まる直前までを
        # 「市区町村」欄に入れる
        normal_match = re.match(
            r"^(.+?)(\d+(?:[-－ー]\d+)*)$",
            main_address
        )

        if normal_match:

            city = normal_match.group(1)
            street = normal_match.group(2)

        else:

            city = main_address


    # =====================================
    # オフィシャルURL
    # =====================================
    official_url = ""

    # 「お店のホームページ」を優先し、
    # なければ「オフィシャルページ」を使用する
    homepage_link = None
    official_page_link = None

    links = driver.find_elements(
        By.TAG_NAME,
        "a"
    )

    for link in links:

        try:

            text_value = (
                link.text
                or ""
            ).strip()

            href = (
                link.get_attribute("href")
                or ""
            ).strip()

            # # や javascript: は
            # 公式URL候補として扱わない
            if (
                not href
                or href == "#"
                or href.lower().startswith(
                    "javascript:"
                )
            ):
                continue

            if (
                "お店のホームページ" in text_value
                and homepage_link is None
            ):

                homepage_link = link

            elif (
                "オフィシャル" in text_value
                and official_page_link is None
            ):

                official_page_link = link

        except StaleElementReferenceException:
            continue


    if homepage_link is not None:
        official_link = homepage_link

    else:
        official_link = official_page_link


    # =====================================
    # 実際にリンクをブラウザで開く
    # =====================================
    if official_link is not None:

        # クリックに失敗しても保持できるように、
        # 先にリンク自身のURLを保存する
        try:

            original_official_url = (
                official_link.get_attribute("href")
                or ""
            ).strip()

        except StaleElementReferenceException:

            original_official_url = ""


        if original_official_url:

            official_url = original_official_url


        try:

            old_handles = driver.window_handles

            driver.execute_script(
                "arguments[0].scrollIntoView();",
                official_link
            )

            # クリック前に3秒待機
            time.sleep(3)

            driver.execute_script(
                "arguments[0].click();",
                official_link
            )

            # 遷移完了待ち
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


            displayed_url = (
                driver.current_url
                or ""
            ).strip()


            # CAPTCHA・認証ページなどを
            # 店舗URLとして保存しない
            suspicious_words = (
                "captcha",
                "challenge",
                "verify",
                "verification"
            )

            displayed_url_lower = (
                displayed_url.lower()
            )

            suspicious_redirect = any(
                word in displayed_url_lower
                for word in suspicious_words
            )


            if (
                displayed_url
                and not suspicious_redirect
            ):

                official_url = displayed_url

            elif suspicious_redirect:

                print(
                    "URL確認:",
                    original_official_url,
                    "-> 不適切な転送先のため"
                    "元URLを保持:",
                    displayed_url
                )


            # 新しいタブなら閉じて元へ戻す
            if len(new_handles) > len(old_handles):

                driver.close()

                driver.switch_to.window(
                    old_handles[0]
                )


        except WebDriverException as e:

            # ブラウザ遷移に失敗した場合も
            # 元の外部URLは消さない
            official_url = (
                original_official_url
            )

            print(
                "公式URLブラウザ確認失敗:",
                original_official_url,
                e
            )


    # =====================================
    # SSL判定
    # =====================================
    ssl = False

    if official_url:

        url_for_ssl_check = official_url

        try:

            # SSL確認のアクセス前にも3秒待機
            time.sleep(3)

            # requestsはデフォルトでverify=True。
            # HTTPS証明書検証に成功した場合だけ
            # SSL=Trueとする。
            ssl_response = requests.get(
                url_for_ssl_check,
                headers=headers,
                timeout=10,
                allow_redirects=True
            )

            final_ssl_url = (
                ssl_response.url
                or ""
            ).strip()

            final_ssl_url_lower = (
                final_ssl_url.lower()
            )

            suspicious_words = (
                "captcha",
                "challenge",
                "verify",
                "verification"
            )

            suspicious_ssl_redirect = any(
                word in final_ssl_url_lower
                for word in suspicious_words
            )


            # CAPTCHA等へ飛ばされた場合は、
            # その転送先を店舗URLにしない
            if suspicious_ssl_redirect:

                print(
                    "SSL確認:",
                    url_for_ssl_check,
                    "-> 不適切な転送先:",
                    final_ssl_url
                )

                ssl = False

            elif (
                final_ssl_url.lower().startswith(
                    "https://"
                )
                and ssl_response.ok
            ):

                # 実際に証明書検証済みHTTPS接続が
                # 成功した場合のみTrue
                ssl = True

                # 正常なリダイレクト先なら
                # 実際の最終URLを保存
                official_url = final_ssl_url

            else:

                ssl = False

                print(
                    "SSL確認失敗:",
                    url_for_ssl_check,
                    "status=",
                    ssl_response.status_code,
                    "final_url=",
                    final_ssl_url
                )


        except requests.exceptions.SSLError as e:

            ssl = False

            print(
                "SSL証明書エラー:",
                url_for_ssl_check,
                e
            )


        except requests.exceptions.Timeout as e:

            ssl = False

            print(
                "接続タイムアウト:",
                url_for_ssl_check,
                e
            )


        except requests.RequestException as e:

            ssl = False

            print(
                "URL接続エラー:",
                url_for_ssl_check,
                e
            )


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
# 有効50店舗を確保するため
# 候補店舗URLを最大100件取得
# =========================================
shop_urls = []


while len(shop_urls) < 100:

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

                if len(shop_urls) >= 100:
                    break


    # =====================================
    # 候補URLを100件取得したら終了
    # =====================================
    if len(shop_urls) >= 100:
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

        except StaleElementReferenceException:

            continue


        if not href:
            continue


        # =====================================
        # ページ下部の「>」ボタンを識別
        # =====================================
        # 画面上では「>」だが、
        # HTMLではリンク内のimg要素として
        # 表示されている。
        #
        # ページ番号「2」などのリンクではなく、
        # alt="次（2）ページを表示"
        # の画像を持つリンクだけを対象にする。
        try:

            images = link.find_elements(
                By.TAG_NAME,
                "img"
            )

            for image in images:

                alt_text = (
                    image.get_attribute("alt")
                    or ""
                ).strip()

                if re.match(
                    r"^次（\d+）ページを表示$",
                    alt_text
                ):

                    next_button = link
                    break

            if next_button is not None:
                break

        except StaleElementReferenceException:

            continue


    # =====================================
    # 「>」がない場合は終了
    # ページ番号リンクでは代用しない
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

    # クリック前に3秒待機
    time.sleep(3)

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
# 有効な店舗が50件になるまで詳細情報を取得
# =========================================
results = []


for i, url in enumerate(
    shop_urls,
    start=1
):

    # 有効店舗が50件そろったら終了
    if len(results) >= 50:
        break


    print()
    print(
        f"候補 {i}/{len(shop_urls)}"
        " を取得中"
    )

    print(url)


    try:

        shop_data = (
            get_shop_info(url)
        )


        # =====================================
        # 有効店舗か確認
        # =====================================
        # メール・公式URLは存在しない店舗もあるため
        # 必須条件にはしない。
        # 店舗名・都道府県・市区町村が取得できた
        # 店舗だけを有効店舗として採用する。
        if (
            shop_data["店舗名"]
            and shop_data["都道府県"]
            and shop_data["市区町村"]
        ):

            results.append(
                shop_data
            )

            print(
                "有効店舗:",
                len(results),
                "/50",
                shop_data["店舗名"]
            )

        else:

            print(
                "無効店舗のためスキップ:",
                url
            )


    except Exception as e:

        # 失敗店舗を空行として追加しない。
        # 次の候補店舗へ進む。
        print(
            "取得エラー・スキップ:",
            url,
            e
        )


# =========================================
# 50件に達したか確認
# =========================================
if len(results) < 50:

    raise RuntimeError(
        "有効店舗が50件に達しませんでした。"
        f" 取得数={len(results)}"
        f" 候補数={len(shop_urls)}"
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
