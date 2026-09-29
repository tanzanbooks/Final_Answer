"""ぐるなびの店舗情報を50件集め、CSVに保存します。"""

import json
import re
import socket                  #**追加：名前解決失敗の判定に使う**
import time
from datetime import datetime  #**追加：発生日時に使う**
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup


# ==================== 1. 設定 ====================

START_URL = "https://www.gnavi.co.jp/"  # トップページから開始
SEARCH_RESULTS_URL = "https://r.gnavi.co.jp/area/jp/rs/"

OUTPUT_FILE = "1-1.csv" #課題提出用のファイル
ERROR_FILE = "1-1_ssl_errors.csv" #取得・SSL確認で失敗したときの記録

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

            email = href.removeprefix(
                "mailto:"
            )

            break

    # ---------- お店のURL ----------

    shop_url, rejected_reason = (
        get_shop_url(soup)
    )

    # ---------- SSL ----------

    if shop_url:

        ssl, error_type, reason = check_ssl(
            shop_url
        )

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

def check_ssl(url):
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
    """画面に表示される＞」のリンク先を探す。"""

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

            return next_url

    return ""


# ==================== 9. メイン処理 ====================

def main():

    # ---------- 最初の検索ページ ----------

    search_url = get_first_search_page(
        START_URL
    )

    if not search_url:

        print(
            "トップページを取得できなかったため"
            "終了します。"
        )

        return

    # 同じ検索ページに戻らないための記録
    visited_pages = set()

    # 同じ店舗を重複して取得しないための記録
    seen_shops = set()

    # SSLがTrueの店舗だけを入れる
    rows = []

    # SSL Falseや取得失敗を記録する
    error_rows = []

    # SSL Trueが50店舗になるまで続ける
    while len(rows) < TARGET_COUNT:

        visited_pages.add(
            search_url
        )

        print(
            f"検索ページ: {search_url}"
        )

        # 検索結果ページを取得
        # get_soup() 内で3秒待つ
        soup = get_soup(
            search_url
        )

        if soup is None:

            print(
                "検索ページを取得できないため"
                "中断します。"
            )

            break

        # ---------- 店舗リンクを探す ----------

        links = soup.find_all("a")

        for link in links:

            href = link.get(
                "href",
                ""
            )

            # 店舗ページのURLでなければ無視
            if not SHOP_PATTERN.fullmatch(
                href
            ):
                continue

            # すでに調べた店舗なら無視
            if href in seen_shops:
                continue

            seen_shops.add(
                href
            )

            print(
                f"候補: {href}"
            )

            # 1店舗の情報を取得
            details, error_type, reason = (
                get_shop_details(href)
            )

            # 店舗ページそのものの取得に失敗した場合
            if details is None:

                error_rows.append(make_error_row(
                    href, "", href, error_type, reason
                ))

                continue

            # detailsの最後はSSLのTrue/False
            if details[-1] is True:

                rows.append(
                    details
                )

                print(
                    "SSL True: "
                    f"{len(rows)}/"
                    f"{TARGET_COUNT}店舗"
                )

            else:

                # 出力用CSVには入れず、エラー原因を別CSVに残す
                error_rows.append(make_error_row(
                    href, details[0], details[-2] or href,
                    error_type, reason
                ))

                print(
                    "  SSL False: "
                    f"{reason}"
                    "（次の候補へ）"
                )

            # SSL Trueが50店舗に達したら終了
            if len(rows) == TARGET_COUNT:
                break

        # 50店舗集まった場合
        if len(rows) == TARGET_COUNT:
            break

        # ---------- 次の検索結果ページへ ----------

        # 画面上の「＞」リンクを読み、そこに書かれたURLへ進む
        next_url = get_next_page_url(
            soup,
            search_url
        )

        if not next_url:

            print(
                "次ページへの「＞」リンクがありません。"
            )

            break

        # すでに訪問したページなら停止
        if next_url in visited_pages:

            print(
                "次ページのリンクが"
                "訪問済みのページを指しています。"
            )

            break

        search_url = next_url


    # ==================== 10. CSVに保存 ====================

    # pandasのDataFrameで列順を指定する。
    # 空文字は空欄のまま保存する。
    pd.DataFrame(
        rows,
        columns=OUTPUT_COLUMNS
    ).to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    # エラー情報は別CSVに保存
    pd.DataFrame(
        error_rows,
        columns=ERROR_COLUMNS
    ).to_csv(
        ERROR_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    # ---------- 実行結果 ----------

    print(
        f"SSL Trueの{len(rows)}店舗を"
        f"{OUTPUT_FILE}に保存しました。"
    )

    print(
        f"失敗・SSL Falseの"
        f"{len(error_rows)}件を"
        f"{ERROR_FILE}に記録しました。"
    )

    if len(rows) < TARGET_COUNT:

        print(
            "50店舗に達していません。"
            "取得条件やエラーを確認してください。"
        )


# ==================== 11. プログラム開始 ====================

if __name__ == "__main__":
    main()
