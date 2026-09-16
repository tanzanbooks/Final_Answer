import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from sqlalchemy import create_engine


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

    page_text = soup.get_text(
        " ",
        strip=True
    )

    email_match = re.search(
        r"[A-Za-z0-9._%+-]+"
        r"@[A-Za-z0-9.-]+"
        r"\.[A-Za-z]{2,}",
        page_text
    )

    if email_match:

        email = email_match.group()


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


    # =====================================
    # 都道府県を除いた住所
    # =====================================

    remaining_address = address_text

    if prefecture:

        remaining_address = (
            remaining_address[
                len(prefecture):
            ]
        )


    # =====================================
    # 市区町村
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


    # =====================================
    # 市区町村を除いた住所
    # =====================================

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

    for link in soup.find_all(
        "a",
        href=True
    ):

        text = link.get_text(
            " ",
            strip=True
        )

        if (
            "オフィシャル" in text
            or "ホームページ" in text
        ):

            official_url = link["href"]
            break


    # =====================================
    # オフィシャルURLへ実際にアクセス
    # リダイレクト後のURLを取得
    # =====================================

    ssl = False

    if official_url:

        official_response = get_response(
            official_url
        )

        if official_response is not None:

            # リダイレクト後のURL
            official_url = (
                official_response.url
            )

        # HTTPSならSSLあり
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
# 検索結果から50店舗のURLを取得
# =========================================

shop_urls = []

page = 1


while len(shop_urls) < 50:

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

    response = get_response(
        search_url
    )

    if response is None:

        print(
            "検索ページを取得できませんでした。"
        )

        page += 1
        continue


    response.encoding = (
        response.apparent_encoding
    )

    print(
        "ステータスコード:",
        response.status_code
    )


    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )


    # =====================================
    # 店舗URL抽出
    # =====================================

    before_count = len(shop_urls)

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

            if href not in shop_urls:

                shop_urls.append(href)

                print(
                    len(shop_urls),
                    href
                )


                if len(shop_urls) >= 50:

                    break


    # 店舗URLが全く増えなかった場合
    if len(shop_urls) == before_count:

        print(
            "新しい店舗URLがありませんでした。"
        )


    page += 1


# =========================================
# URL取得結果
# =========================================

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
    shop_urls[:50],
    start=1
):

    print()
    print(
        f"{i}/50 店舗目を取得中"
    )

    print(url)


    try:

        shop_data = get_shop_info(
            url
        )

    except Exception as e:

        # 予期しないエラーでも
        # 50件という行数を保つ
        print(
            "予期しないエラー:",
            url,
            e
        )

        shop_data = {
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


    # 成否にかかわらず必ず1件追加
    results.append(
        shop_data
    )

    print(
        "取得完了:",
        shop_data["店舗名"]
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
# MySQL保存
# =========================================

engine = create_engine(
    "mysql+pymysql://"
    "root:root@ex2_mysql:3306/"
    "ex2?charset=utf8mb4",
    pool_pre_ping=True
)


df.to_sql(
    "ex2_2",
    con=engine,
    if_exists="replace",
    index=False
)


engine.dispose()


print()
print("MySQLに保存しました")


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
