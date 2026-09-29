"""ぐるなびの店舗情報を50件取得し、MySQLのex2.ex2_2に保存する。"""

import json
import os
import re
import socket                  #**追加：名前解決失敗の判定に使う**
import time
from datetime import datetime  #**追加：発生日時に使う**
from urllib.parse import parse_qs, urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from sqlalchemy import Boolean, Column, MetaData, String, Table, create_engine, delete, func, select
from sqlalchemy.engine import URL


# ==================== 1. 設定 ====================

START_URL = "https://www.gnavi.co.jp/"  # トップページから開始
SEARCH_RESULTS_URL = "https://r.gnavi.co.jp/area/jp/rs/"

DB_NAME = "ex2"
TABLE_NAME = "ex2_2"
DB_HOST = os.getenv("DB_HOST", "ex2_mysql")  # Docker内。Windowsから直接実行するならlocalhost
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

TARGET_COUNT = 50 #変更**50件ではなく、50店舗を取得**

TIMEOUT = 10  # 秒。

# サーバーに負荷をかけないため、HTTPリクエストを送る前に必ず3秒待つ
REQUEST_INTERVAL = 3

# ページ取得とSSL確認の両方で使用するUser-Agent
HEADERS = {"User-Agent": "ExerciseForPoolScraper(Python requests; educational use)"}

SHOP_PATTERN = re.compile(r"^https://r\.gnavi\.co\.jp/[A-Za-z0-9]+/$")

PREF_PATTERN = re.compile(r"^(東京都|北海道|京都府|大阪府|.{2,3}県)")

PHONE_PATTERN = re.compile(r"0\d{1,4}-\d{1,4}-\d{3,4}")

#sample.csvと同じ９列の要素
OUTPUT_COLUMNS = [
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

ERROR_COLUMNS = [
    "発生日時",   # **新しく追加**
    "ぐるなび店舗URL",
    "店舗名",
    "確認対象URL",
    "エラーの種類",
    "具体的なエラーメッセージ"
]


def make_error_row(shop_page_url, name, target_url, error_type, message):
    """提出用CSVとは別の記録を1行作る。"""
    return [
        datetime.now().astimezone().isoformat(timespec="seconds"),
        shop_page_url,
        name,
        target_url,
        error_type,
        message
    ]


# ==================== 2. HTMLを読む ====================

def get_soup(url):
    """ページを取得し、BeautifulSoupに変換する。失敗したらNone。"""

    try:
        # サーバーに負荷をかけないため、リクエストを送る前に必ず3秒待つ
        time.sleep(REQUEST_INTERVAL)

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT
        )

        response.raise_for_status()
        response.encoding = "utf-8"

        return BeautifulSoup(
            response.text,
            "html.parser"
        )

    except requests.exceptions.RequestException as error:
        print(f"  ページ取得失敗: {error}")
        return None


# ==================== 3. 住所を取り出して分割 ====================

def get_address_parts(soup):
    """住所欄から都道府県、市区町村、番地、建物名を返す。"""

    address = ""
    label = None

    # HTMLの文字を上から順に読み、
    # 「住所」と書かれた場所を探す
    for value in soup.find_all(string=True):

        if value.strip() == "住所":
            label = value
            break

    if label:

        # 住所は表の「住所」行に入る。
        # td全体を読むと建物名も取得できる。
        row = label.find_parent("tr")

        address_cell = row.find("td") if row else None

        if address_cell:

            address = address_cell.get_text(
                " ",
                strip=True
            )

        else:

            # 表以外のページでは、住所ラベルの直後の要素を使う
            next_element = label.parent.find_next()

            address = (
                next_element.get_text(" ", strip=True)
                if next_element
                else ""
            )

        # 郵便番号など不要な文字を削除
        address = re.sub(r"〒?\d{3}-\d{4}\s*","",address)

        address = address.replace("大きな地図で見る","")

        address = address.replace("地図印刷","").strip()

    # 都道府県を取得
    pref_match = PREF_PATTERN.match(address)

    if not pref_match:
        return "", "", "", ""

    prefecture = pref_match.group()

    remaining = address[len(prefecture):]

    # 数字の前までを市区町村・町名とする
    city_match = re.match(r"(.+?)(?=\d)",remaining)

    if not city_match:
        return prefecture, "", "", ""

    city = city_match.group().strip()

    after_city = remaining[len(city_match.group()):].strip()

    # 番地と建物名の間に空白がなくても、番地の数字とハイフンで区切る
    street_match = re.match(
        r"(?:\d+条通)?\d+(?:[-－ー−]\d+)*",
        after_city
    )

    if not street_match:

        return (
            prefecture,
            city,
            "",
            after_city
        )

    street = street_match.group()

    building = after_city[
        street_match.end():
    ].strip()

    return (
        prefecture,
        city,
        street,
        building
    )


# ==================== 4. お店のホームページを探す ====================

def decode_shop_link(link):
    """
    通常のhref、または
    ぐるなびのdata-oからリンク先を取り出す。
    """

    # data-oとは、ぐるなびのページにあるリンク先の情報を入れたHTML属性
    href = link.get("href", "")

    if href and href != "#":
        return href

    try:

        encoded = json.loads(
            link.get("data-o", "{}")
        )

        host = encoded.get("a", "")
        scheme = encoded.get("b", "")

        if host and scheme in ("http", "https"):

            return scheme + "://" + host

    except (ValueError, TypeError):
        pass

    return ""


def invalid_shop_url_reason(url):
    """CAPTCHAやぐるなび中継ページなら、採用できない理由を返す。"""

    parsed = urlparse(url)

    host = (
        parsed.hostname or ""
    ).lower()

    # httpまたはhttpsでなければ無効
    if (
        parsed.scheme.lower()
        not in ("http", "https")
        or not host
    ):
        return "有効なお店のURLなし"

    # ぐるなび自身のURLは店舗ホームページとして扱わない
    if (
        host == "gnavi.co.jp"
        or host.endswith(".gnavi.co.jp")
    ):
        return "ぐるなびの中継URL"

    if (
        host == "gnavi.com"
        or host.endswith(".gnavi.com")
    ):
        return "ぐるなびの中継URL"

    # CAPTCHA関連URLを除外
    if any(
        word in (host + parsed.path.lower())
        for word in (
            "captcha",
            "recaptcha",
            "hcaptcha",
            "challenge"
        )
    ):
        return "CAPTCHAのURL"

    return ""


def get_shop_url(soup):
    """お店のページをオフィシャルページより優先。有効な店のURLと不採用理由を返す。"""

    links = soup.find_all("a")

    rejected_reason = "お店のURLなし"

    # 上から順番に優先する
    # 1. お店のホームページ
    # 2. オフィシャルページ
    for label in (
        "お店のホームページ",
        "オフィシャルページ",
        "オフィシャル ページ"
    ):

        for link in links:

            link_text = link.get_text(
                " ",
                strip=True
            )

            if label in link_text:

                url = decode_shop_link(link)

                reason = invalid_shop_url_reason(
                    url
                )

                # 問題がなければ採用
                if not reason:
                    return url, ""

                # 採用できなかった理由を保存
                rejected_reason = reason

    return "", rejected_reason


# ==================== 5. 1店舗の情報を集める ====================

def get_shop_details(shop_page_url):
    """
    1店舗を調べ、
    (9列のデータ, エラーの種類, 具体的なメッセージ)
    を返す。
    """

    # ぐるなびの店舗ページを取得
    # get_soup() 内で3秒待ってからアクセスする
    soup = get_soup(shop_page_url)

    if soup is None:

        return (
            None,
            "店舗ページ取得失敗",
            "店舗ページを取得できませんでした。詳細は画面の「ページ取得失敗」を確認してください。"
        )

    # ---------- 店名 ----------

    h1 = soup.find("h1")

    name = (
        h1.get_text(strip=True)
        if h1
        else ""
    )

    if not name:

        print(
            "  店名を取得できませんでした"
        )

        return (
            None,
            "店名取得失敗",
            "店舗ページに店名が見つかりませんでした。"
        )

    # ---------- 電話番号 ----------

    text = soup.get_text(
        " ",
        strip=True
    )

    phone_match = PHONE_PATTERN.search(
        text
    )

    phone = (
        phone_match.group()
        if phone_match
        else ""
    )

    # ---------- 住所 ----------

    (
        prefecture,
        city,
        street,
        building
    ) = get_address_parts(soup)

    # ---------- メールアドレス ----------

    # 「お店に直接メールする」のmailtoリンクだけを対象にする
    email = ""

    for link in soup.find_all("a"):

        href = link.get(
            "href",
            ""
        )

        link_text = link.get_text(
            strip=True
        )

        if (
            "お店に直接メールする"
            in link_text
            and href.startswith("mailto:")
        ):

            email = href[len("mailto:"):]

            break

    # ---------- お店のURL ----------

    shop_url, rejected_reason = (
        get_shop_url(soup)
    )

    # ---------- SSL ----------

    if shop_url:

        # 検証に成功した転送先だけをDBのURL欄へ反映する。
        final_urls = []
        ssl, error_type, reason = check_ssl(
            shop_url, final_url_callback=final_urls.append
        )
        if final_urls:
            shop_url = final_urls[0]

    else:

        ssl = False
        error_type = "店舗URLなし"
        reason = rejected_reason

    print(
        f"  SSL: {ssl}（{reason}）"
    )

    # CSVに保存する9列
    details = [
        name,
        phone,
        email,
        prefecture,
        city,
        street,
        building,
        shop_url,
        ssl
    ]

    return details, error_type, reason


# ==================== 6. SSLを確認 ====================

def check_ssl(url, final_url_callback=None):
    """URLに接続し、証明書の検証と最終URLのHTTPSを確認する。"""

    # まずURL自体が有効か確認
    invalid_reason = (
        invalid_shop_url_reason(url)
    )

    if invalid_reason:
        return False, "無効なURL", invalid_reason

    try:

        # ==========================================
        # サーバーに負荷をかけないため、
        # SSL確認のリクエスト前にも必ず3秒待つ
        # ==========================================
        time.sleep(REQUEST_INTERVAL)

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT,
            allow_redirects=True,
            verify=True
        )

        response.raise_for_status()

        # 有効なURLを開いても、　　　　　　　　　　**以下大幅追加**
        # 転送先がCAPTCHAや
        # ぐるなび中継ページの場合がある
        invalid_reason = (
            invalid_shop_url_reason(
                response.url
            )
        )

        if invalid_reason:

            return (
                False,
                "転送先URL不適切",
                "転送先: "
                + invalid_reason
            )

        # ページタイトルも確認
        title = BeautifulSoup(
            response.text,
            "html.parser"
        ).find("title")

        title_text = (
            title.get_text(
                " ",
                strip=True
            ).lower()
            if title
            else ""
        )

        # CAPTCHA画面か確認
        if any(
            word in title_text
            for word in (
                "captcha",
                "recaptcha",
                "robot check",
                "ロボットではない"
            )
        ):

            return (
                False,
                "CAPTCHA",
                "転送先がCAPTCHA画面"
            )

        # 証明書・HTTP応答・転送先の検査を通った場合のみ保存する。
        # 失敗時は呼び出し元の元URLをそのまま残す。
        if final_url_callback is not None:
            final_url_callback(response.url)

        # 最終的なURLがhttpsならTrue
        if response.url.lower().startswith(
            "https://"
        ):

            return (
                True,
                "",
                "SSL確認成功"
            )

        return (
            False,
            "HTTPへの転送",
            "最終URLがHTTP"
        )

    # SSL証明書そのものに問題がある
    except requests.exceptions.SSLError as error:

        return (
            False,
            "証明書エラー",
            str(error)
        )

    # タイムアウト
    except requests.exceptions.Timeout as error:

        return (
            False,
            "タイムアウト",
            str(error)
        )

    # 名前解決失敗は一般的な接続エラーと区別する
    except requests.exceptions.ConnectionError as error:

        cause = error
        while cause is not None:
            if isinstance(cause, socket.gaierror):
                return False, "名前解決失敗", str(error)
            cause = cause.__cause__ or cause.__context__

        if "NameResolutionError" in str(error) or "Failed to resolve" in str(error):
            return False, "名前解決失敗", str(error)

        return False, "接続エラー", str(error)

    # HTTPエラーなど、その他の通信エラー
    except requests.exceptions.RequestException as error:

        return (
            False,
            "通信エラー",
            str(error)
        )


# ==================== 7. 検索結果の最初のページを決める ====================

def get_first_search_page(start_url):
    """トップページから全国の店舗一覧へ移動する。"""

    # 最初から検索結果ページを指定している場合はそのURLをそのまま使う
    if (
        start_url.rstrip("/")
        != "https://www.gnavi.co.jp"
    ):

        return start_url

    print(
        f"トップページを開きます: {start_url}"
    )

    # get_soup() 内で3秒待ってからアクセス
    home_soup = get_soup(
        start_url
    )

    if home_soup is None:
        return ""

    # 全国一覧へのリンクがトップページ内にあれば、そのhrefを使う
    for link in home_soup.find_all(
        "a",
        href=True
    ):

        destination = urljoin(
            start_url,
            link["href"]
        )

        if (
            destination.rstrip("/")
            == SEARCH_RESULTS_URL.rstrip("/")
        ):

            print(
                "全国の店舗一覧へ移動します: "
                f"{destination}"
            )

            return destination

    # トップページに全国一覧へのリンクがない場合は、既知の検索結果URLを使う
    # トップページの地域別リンクを選ぶと、全国50店舗の対象が変わってしまう
    print(
        "全国の店舗一覧へ移動します: "
        f"{SEARCH_RESULTS_URL}"
    )

    return SEARCH_RESULTS_URL


# ==================== 8. 次の検索ページを探す ====================

def get_next_page_url(soup, current_url):
    """画面に表示される「次」のリンク先を探す。"""
    current_page = int(parse_qs(urlparse(current_url).query).get("p", ["1"])[0])

    for link in soup.find_all(
        "a",
        href=True
    ):

        image = link.find("img")

        image_alt = (
            image.get("alt", "")
            if image
            else ""
        )

        label = link.get(
            "aria-label",
            ""
        )

        visible_text = link.get_text(
            strip=True
        )

        # ぐるなびでは「＞」が画像で、
        # altに
        # 「次（2）ページを表示」と入る
        is_next = (
            image_alt.startswith("次")
            or label.startswith("次")
            or visible_text
            in ("＞", ">", "次へ")
        )

        if not is_next:
            continue

        next_url = urljoin(
            current_url,
            link["href"]
        )

        parsed = urlparse(
            next_url
        )

        # 検索結果以外のページを誤って次ページにしない
        if (
            parsed.netloc
            == "r.gnavi.co.jp"
            and parsed.path
            == "/area/jp/rs/"
        ):

            page = parse_qs(parsed.query).get("p", ["1"])[0]
            if page.isdigit() and int(page) > current_page:
                return next_url

    return ""


# ==================== 9. メイン処理 ====================

def save_to_mysql(rows):
    """50件の取得が完了してから、Python経由でテーブルを更新する。"""
    address = URL.create(
        "mysql+pymysql", username=DB_USER, password=DB_PASSWORD,
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        query={"charset": "utf8mb4"}
    )
    engine = create_engine(address, pool_pre_ping=True)
    metadata = MetaData()
    shops = Table(
        TABLE_NAME, metadata,
        Column("店舗名", String(255)),
        Column("電話番号", String(50)),
        Column("メールアドレス", String(320)),
        Column("都道府県", String(20)),
        Column("市区町村", String(255)),
        Column("番地", String(255)),
        Column("建物名", String(255)),
        Column("URL", String(2048)),
        Column("SSL", Boolean),
    )
    frame = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    # 失敗店舗や空欄URLを50件に数えない。
    if len(frame) != TARGET_COUNT or frame["URL"].eq("").any():
        raise ValueError("有効なURLを持つ50店舗が揃っていません")
    try:
        # 既存データの削除と50件の保存を一つの処理として実行する。
        with engine.begin() as connection:
            metadata.create_all(connection, tables=[shops])
            connection.execute(delete(shops))
            frame.to_sql(TABLE_NAME, connection, if_exists="append", index=False)
            count = connection.scalar(select(func.count(shops.c.URL)))
            if count != TARGET_COUNT:
                raise ValueError(f"保存後のURL件数が{count}件です")
        print(f"MySQL {DB_NAME}.{TABLE_NAME} に{count}店舗保存しました")
    finally:
        engine.dispose()


def main():
    search_url = get_first_search_page(START_URL)
    if not search_url:
        print("トップページを取得できなかったため終了します")
        return

    visited_pages = set()
    seen_shops = set()
    rows = []
    errors = []

    while len(rows) < TARGET_COUNT:
        if search_url in visited_pages:
            print("訪問済みの検索ページです。終了します")
            break
        visited_pages.add(search_url)
        print(f"検索ページ: {search_url}")
        soup = get_soup(search_url)  # requests.getの直前に3秒待機
        if soup is None:
            break

        for link in soup.find_all("a", href=True):
            shop_page_url = link["href"]
            if not SHOP_PATTERN.fullmatch(shop_page_url):
                continue
            if shop_page_url in seen_shops:
                continue
            seen_shops.add(shop_page_url)
            print(f"候補: {shop_page_url}")
            details, error_type, reason = get_shop_details(shop_page_url)
            if details is None:
                errors.append(make_error_row(shop_page_url, "", shop_page_url, error_type, reason))
                continue
            if details[-1] is True and details[-2]:
                rows.append(details)
                print(f"SSL True: {len(rows)}/{TARGET_COUNT}店舗")
            else:
                errors.append(make_error_row(
                    shop_page_url, details[0], details[-2] or shop_page_url,
                    error_type, reason
                ))
                print(f"  SSL False: {reason}（次の候補へ）")
            if len(rows) >= TARGET_COUNT:
                break

        if len(rows) >= TARGET_COUNT:
            break
        next_url = get_next_page_url(soup, search_url)
        if not next_url or next_url in visited_pages:
            print("次の未訪問ページが見つかりません")
            break
        search_url = next_url

    if len(rows) != TARGET_COUNT:
        print(f"有効な店舗は{len(rows)}件です。50件未満なのでMySQLは更新しません")
        return
    save_to_mysql(rows)
    print(f"取得失敗・SSL False: {len(errors)}件")
    for error in errors:
        print(f"  {error[3]} | {error[4]} | {error[5]}")


if __name__ == "__main__":
    main()
