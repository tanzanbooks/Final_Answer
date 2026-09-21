import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time


# =========================================
# 基本設定
# =========================================

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/152.0.0.0 Safari/537.36"
    )
}


# =========================================
# Webページを取得する関数
# 最大3回まで再試行する
# =========================================

def get_response(url, retries=3):

    for attempt in range(1, retries + 1):

        try:
            # 課題指定：アクセス前に3秒待機
            time.sleep(3)

            response = requests.get(
                url,
                headers=headers,
                timeout=20
            )

            response.raise_for_status()

            return response

        except requests.RequestException as e:

            print(
                f"通信エラー "
                f"{attempt}/{retries}:",
                url
            )

            print(e)

            if attempt < retries:
                print("3秒後に再試行します。")

    # 3回すべて失敗した場合
    return None


# =========================================
# 1店舗の情報を取得する関数
# =========================================

def get_shop_info(gnavi_url):

    response = get_response(gnavi_url)

    # =====================================
    # 店舗ページを取得できなかった場合
    # =====================================

    if response is None:

        print(
            "店舗ページを取得できなかったため、"
            "空欄データとして保存します:",
            gnavi_url
        )

        return {
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

    response.encoding = response.apparent_encoding

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )


    # =====================================
    # 店舗名
    # =====================================

    shop_name = ""

    for h1 in soup.find_all("h1"):

        text = h1.get_text(strip=True)

        if text and text != "ぐるなび":

            shop_name = text
            break


    # =====================================
    # 電話番号
    # =====================================

    tel_numbers = []

    for tag in soup.find_all(
        ["span", "p", "td", "dd"]
    ):

        text = tag.get_text(
            " ",
            strip=True
        )

        numbers = re.findall(
            r"\d{2,4}-\d{2,4}-\d{3,4}",
            text
        )

        tel_numbers.extend(numbers)

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
    for link in soup.find_all(
        "a",
        href=True
    ):

        href = link.get(
            "href",
            ""
        ).strip()

        link_text = link.get_text(
            " ",
            strip=True
        )

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


    # =====================================
    # 住所取得
    # =====================================

    address_text = ""

    for tag in soup.find_all(
        ["td", "dd"]
    ):

        text = tag.get_text(
            " ",
            strip=True
        )

        if re.search(
            r"〒?\d{3}-\d{4}\s*"
            r"(北海道|東京都|京都府|大阪府|.{2,3}県)",
            text
        ):

            address_text = text
            break


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
        remaining_address = address_text[len(prefecture):]
    else:
        remaining_address = address_text


    # =====================================
    # 建物名
    # =====================================
    parts = remaining_address.split(" ", 1)

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
    # 有効なURLがなければ
    # 「オフィシャルページ」を使用する
    homepage_url = ""
    official_page_url = ""

    for link in soup.find_all(
        "a",
        href=True
    ):

        text = link.get_text(
            " ",
            strip=True
        )

        href = link.get(
            "href",
            ""
        ).strip()

        # # や javascript: は
        # 店舗URLとして扱わない
        if (
            not href
            or href == "#"
            or href.lower().startswith("javascript:")
        ):
            continue

        if (
            "お店のホームページ" in text
            and not homepage_url
        ):
            homepage_url = href

        elif (
            "オフィシャル" in text
            and not official_page_url
        ):
            official_page_url = href

    if homepage_url:
        official_url = homepage_url

    elif official_page_url:
        official_url = official_page_url


    # =====================================
    # URL確認・SSL判定
    # =====================================

    ssl = False

    if official_url:

        # 接続確認に失敗した場合にも、
        # ぐるなびから取得した元URLは保持する
        original_official_url = official_url

        try:

            # アクセス前に3秒待機
            time.sleep(3)

            # requests はデフォルトで verify=True。
            # HTTPS証明書を検証した状態で接続する
            official_response = requests.get(
                original_official_url,
                headers=headers,
                timeout=10,
                allow_redirects=True
            )

            final_url = (
                official_response.url
                or ""
            ).strip()

            # CAPTCHAや認証ページへの転送を
            # 店舗URLとして保存しない
            suspicious_words = (
                "captcha",
                "challenge",
                "verify",
                "verification"
            )

            final_url_lower = (
                final_url.lower()
            )

            suspicious_redirect = any(
                word in final_url_lower
                for word in suspicious_words
            )

            if suspicious_redirect:

                print(
                    "URL確認:",
                    original_official_url,
                    "-> 不適切な転送先のため元URLを保持:",
                    final_url
                )

                official_url = (
                    original_official_url
                )

                ssl = False

            else:

                # 正常な転送先なら、
                # 実際に表示された最終URLを保存する
                official_url = final_url

                # 最終URLがHTTPSで、
                # 証明書検証付き接続が成功した場合のみTrue
                if (
                    final_url_lower.startswith(
                        "https://"
                    )
                    and official_response.ok
                ):

                    ssl = True

                else:

                    ssl = False

                    print(
                        "SSL確認失敗:",
                        original_official_url,
                        "final_url=",
                        final_url,
                        "status=",
                        official_response.status_code
                    )

        except requests.exceptions.SSLError as e:

            official_url = (
                original_official_url
            )

            ssl = False

            print(
                "SSL証明書エラー:",
                original_official_url,
                e
            )

        except requests.exceptions.Timeout as e:

            official_url = (
                original_official_url
            )

            ssl = False

            print(
                "接続タイムアウト:",
                original_official_url,
                e
            )

        except requests.RequestException as e:

            official_url = (
                original_official_url
            )

            ssl = False

            print(
                "URL接続エラー:",
                original_official_url,
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
# 有効な店舗を50件取得
# =========================================

shop_urls = []
processed_urls = set()
results = []

page = 1


while len(results) < 50:

    if page == 1:

        search_url = (
            "https://r.gnavi.co.jp/"
            "area/jp/rs/"
        )

    else:

        search_url = (
            "https://r.gnavi.co.jp/"
            f"area/jp/rs/?p={page}"
        )


    print()
    print(
        "検索ページ取得中:",
        search_url
    )


    # =====================================
    # 検索ページ取得
    # =====================================

    # アクセス前に3秒待機
    time.sleep(3)

    try:

        response = requests.get(
            search_url,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()

        response.encoding = (
            response.apparent_encoding
        )

    except requests.RequestException as e:

        print(
            "検索ページ取得エラー:",
            search_url,
            e
        )

        # このページだけの失敗なら、
        # 次の検索ページを試す
        page += 1
        continue


    print(
        "ステータスコード:",
        response.status_code
    )


    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )


    # =====================================
    # このページの店舗URLを抽出
    # =====================================

    page_shop_urls = []

    for link in soup.find_all(
        "a",
        href=True
    ):

        href = link["href"]

        if re.match(
            r"^https://r\.gnavi\.co\.jp/"
            r"[A-Za-z0-9]+/?$",
            href
        ):

            if (
                href not in processed_urls
                and href not in page_shop_urls
            ):

                page_shop_urls.append(
                    href
                )


    print(
        "このページの新規候補:",
        len(page_shop_urls),
        "件"
    )


    # 新しい候補がない場合は、
    # 無限ループを防ぐため終了する
    if not page_shop_urls:

        print(
            "新しい店舗URLが見つからないため"
            "終了します。"
        )

        break


    # =====================================
    # 候補店舗の詳細情報を取得
    # =====================================

    for url in page_shop_urls:

        if len(results) >= 50:
            break

        processed_urls.add(
            url
        )

        shop_urls.append(
            url
        )


        print()
        print(
            f"候補{len(processed_urls)}件目を取得中"
        )

        print(url)


        try:

            shop_data = get_shop_info(
                url
            )


            # 空データを50件の穴埋めとして
            # カウントしない
            required_values = (
                shop_data.get(
                    "店舗名",
                    ""
                ).strip(),

                shop_data.get(
                    "都道府県",
                    ""
                ).strip(),

                shop_data.get(
                    "市区町村",
                    ""
                ).strip()
            )


            if not all(
                required_values
            ):

                print(
                    "有効店舗として数えません:",
                    url
                )

                continue


            results.append(
                shop_data
            )


            print(
                "取得成功:",
                shop_data["店舗名"]
            )

            print(
                "有効店舗数:",
                len(results),
                "/ 50"
            )


        except Exception as e:

            print(
                "店舗取得エラー:",
                url,
                e
            )

            # 失敗した店舗はresultsに追加せず、
            # 次の候補店舗へ進む
            continue


    page += 1


# =========================================
# 取得結果
# =========================================

print()

print(
    "処理した候補URL数:",
    len(processed_urls)
)

print(
    "有効店舗取得数:",
    len(results)
)


# 50件に達しなかった場合は、
# 不完全な状態でDB保存しない
if len(results) < 50:

    raise RuntimeError(
        "有効な店舗を50件取得できませんでした。"
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
    "1-1.csv",
    index=False,
    encoding="utf-8-sig"
)

print()
print("1-1.csv を保存しました。")


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
