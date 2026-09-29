"""ぐるなびの店舗情報を Selenium/ChromeDriver で50件取得する。"""

import json
import csv
import re
import socket
import time
from pathlib import Path
from datetime import datetime
from urllib.parse import parse_qs, urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

START_URL = "https://www.gnavi.co.jp/"
SEARCH_RESULTS_URL = "https://r.gnavi.co.jp/area/jp/rs/"
OUTPUT_FILE = "1-2.csv"
ERROR_FILE = "1-2_ssl_errors.csv"
TIMING_FILE = "1-2_preaccess_times.csv"
TARGET_COUNT = 50
TIMEOUT = 10
REQUEST_INTERVAL = 3
# chromedriver が PATH にない場合は、実際のファイルの絶対パスを指定する。
CHROMEDRIVER_PATH = str(Path(__file__).with_name("chromedriver.exe"))
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HEADERS = {"User-Agent": USER_AGENT}
SHOP_PATTERN = re.compile(r"^https://r\.gnavi\.co\.jp/[A-Za-z0-9]+/$")
PREF_PATTERN = re.compile(r"^(東京都|北海道|京都府|大阪府|.{2,3}県)")
PHONE_PATTERN = re.compile(r"0\d{1,4}-\d{1,4}-\d{3,4}")
OUTPUT_COLUMNS = ["店舗名", "電話番号", "メールアドレス", "都道府県", "市区町村", "番地", "建物名", "URL", "SSL"]
ERROR_COLUMNS = ["発生日時", "ぐるなび店舗URL", "店舗名", "確認対象URL", "エラーの種類", "具体的なエラーメッセージ"]


def make_error_row(shop_page_url, name, target_url, error_type, message):
    return [datetime.now().astimezone().isoformat(timespec="seconds"), shop_page_url,
            name, target_url, error_type, message]


def get_soup(driver, url):
    """Chrome が URL を開く直前に必ず3秒待つ。"""
    try:
        time.sleep(REQUEST_INTERVAL)
        driver.get(url)
        return BeautifulSoup(driver.page_source, "html.parser")
    except (TimeoutException, WebDriverException) as error:
        print(f"  ページ取得失敗: {error}")
        return None


def record_preaccess_time(shop_url, target_url, retrieved_at, method):
    """店舗ページ取得からアクセス操作直前までの時間を記録する。"""
    elapsed = time.perf_counter() - retrieved_at
    print(f"  店舗ページ取得から{method}直前まで: {elapsed:.2f}秒")
    timing_path = Path(TIMING_FILE)
    with timing_path.open("a", newline="", encoding="utf-8-sig") as timing_file:
        writer = csv.writer(timing_file)
        if timing_file.tell() == 0:
            writer.writerow(["計測日時", "店舗ページURL", "アクセス対象URL", "方法", "アクセス前経過時間（秒）"])
        writer.writerow([
            datetime.now().astimezone().isoformat(timespec="seconds"),
            shop_url, target_url, method, f"{elapsed:.2f}"
        ])


def click_shop_homepage(driver, target_url, shop_retrieved_at):
    """店舗ページ取得から外部リンクへのアクセス開始までを測る。"""
    original_handle = driver.current_window_handle
    old_handles = set(driver.window_handles)
    original_url = driver.current_url
    for element in driver.find_elements(By.TAG_NAME, "a"):
        try:
            html = BeautifulSoup(element.get_attribute("outerHTML"), "html.parser").find("a")
            if not html or decode_shop_link(html) != target_url:
                continue
            # 同じURLの非表示リンクはクリックできないので飛ばす。
            if not element.is_displayed() or not element.is_enabled():
                continue
            # 画面上端では別のリンクが重なることがあるため中央に移す。
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
                element
            )
            # WebElement.click() 自体がネットワークアクセスを起こす。
            time.sleep(REQUEST_INTERVAL)
            record_preaccess_time(original_url, target_url, shop_retrieved_at, "クリック")
            element.click()
            # 新しいタブで開く場合は、そのタブが作られるまで待つ。
            WebDriverWait(driver, TIMEOUT).until(
                lambda browser: (set(browser.window_handles) - old_handles)
                or browser.current_url != original_url
            )
            new_handles = set(driver.window_handles) - old_handles
            if new_handles:
                driver.switch_to.window(next(iter(new_handles)))
            # 中継ページからの転送と画面の読み込みを待つ。
            WebDriverWait(driver, TIMEOUT).until(
                lambda browser: browser.current_url not in ("about:blank", "data:,")
                and browser.execute_script("return document.readyState") == "complete"
            )
            time.sleep(3)  # 画面でも遷移先を確認できるようにする。
            actual_url = driver.current_url
            print(f"  お店のホームページを表示: {actual_url}")
            return actual_url
        except (TimeoutException, WebDriverException) as error:
            print(f"  ホームページのクリック失敗: {error}")
            break

    # 表示されるリンクがない場合も、取得した店舗URLをChromeで実際に開く。
    # driver.get() もアクセスなので、その直前に必ず3秒待つ。
    print(f"  クリックできないためURLを直接開きます: {target_url}")
    try:
        time.sleep(REQUEST_INTERVAL)
        record_preaccess_time(original_url, target_url, shop_retrieved_at, "直接アクセス")
        driver.get(target_url)
        WebDriverWait(driver, TIMEOUT).until(
            lambda browser: browser.execute_script("return document.readyState") == "complete"
        )
        time.sleep(3)
        actual_url = driver.current_url
        print(f"  お店のホームページを表示: {actual_url}")
        return actual_url
    except (TimeoutException, WebDriverException) as error:
        print(f"  ホームページへの直接アクセス失敗: {error}")
        return ""


def restore_shop_page(driver, shop_page_url, original_handle):
    """外部リンクから戻る。戻る操作の直前にも3秒待つ。"""
    try:
        if len(driver.window_handles) > 1:
            for handle in driver.window_handles:
                if handle != original_handle:
                    driver.switch_to.window(handle)
                    driver.close()
            driver.switch_to.window(original_handle)
        elif driver.current_url != shop_page_url:
            time.sleep(REQUEST_INTERVAL)
            driver.back()
    except WebDriverException as error:
        print(f"  店舗ページへの復帰失敗: {error}")


def click_next_page(driver, next_url):
    """検索結果の「>」をクリックする。クリック直前に3秒待つ。"""
    for element in driver.find_elements(By.TAG_NAME, "a"):
        href = element.get_attribute("href")
        if href != next_url:
            continue
        label = element.get_attribute("aria-label") or ""
        images = element.find_elements(By.TAG_NAME, "img")
        image_alt = images[0].get_attribute("alt") if images else ""
        if not (label.startswith("次") or image_alt.startswith("次")
                or element.text.strip() in (">", "＞", "次へ")):
            continue
        try:
            time.sleep(REQUEST_INTERVAL)
            element.click()
            # click()の直後は前のページのHTMLが残ることがある。
            WebDriverWait(driver, 30).until(
                lambda browser: browser.current_url == next_url
                and browser.execute_script("return document.readyState") == "complete"
            )
            return BeautifulSoup(driver.page_source, "html.parser")
        except (TimeoutException, WebDriverException) as error:
            print(f"  次ページへのクリック失敗: {error}")
            return None
    print("  次ページの「>」ボタンが見つかりません")
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
        r"\d+(?:[-－ー−]\d+)*",
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

def get_shop_details(driver, shop_page_url):
    """
    1店舗を調べ、
    (9列のデータ, エラーの種類, 具体的なメッセージ)
    を返す。
    """

    # ぐるなびの店舗ページを取得
    # get_soup() 内で3秒待ってからアクセスする
    soup = get_soup(driver, shop_page_url)
    shop_retrieved_at = time.perf_counter()

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

        # 店舗ページから取得した元の外部サイトURLを保持する。
        # 転送先がCAPTCHAなどでも、このURLをエラー記録に残す。
        original_shop_url = shop_url
        original_handle = driver.current_window_handle
        actual_url = click_shop_homepage(driver, original_shop_url, shop_retrieved_at)
        restore_shop_page(driver, shop_page_url, original_handle)
        if actual_url:
            invalid_reason = invalid_shop_url_reason(actual_url)
            if invalid_reason:
                ssl = False
                error_type = "転送先URL不適切"
                reason = f"元URL: {original_shop_url}／転送先: {actual_url}／{invalid_reason}"
            else:
                # 有効な転送先だけをURL欄へ採用する。
                shop_url = actual_url
                ssl, error_type, reason = check_ssl(actual_url)
        else:
            ssl = False
            error_type = "リンク遷移失敗"
            reason = f"元URL: {original_shop_url}／実際の遷移先URLを取得できませんでした"

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

def get_first_search_page(driver, start_url):
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
        driver, start_url
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
            candidate_page = parse_qs(parsed.query).get("p", ["1"])[0]
            if candidate_page.isdigit() and int(candidate_page) > current_page:
                return next_url

    return ""


# ==================== 9. メイン処理 ====================

def main():

    options = Options()
    options.add_argument(f"--user-agent={USER_AGENT}")
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    try:
        run_scraper(driver)
    finally:
        driver.quit()


def run_scraper(driver):
    # ---------- 最初の検索ページ ----------

    search_url = get_first_search_page(
        driver, START_URL
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
    clicked_soup = None
    while len(rows) < TARGET_COUNT:

        visited_pages.add(
            search_url
        )

        print(
            f"検索ページ: {search_url}"
        )

        # 検索結果ページを取得
        # get_soup() 内で3秒待つ
        if clicked_soup is not None:
            soup = clicked_soup
            clicked_soup = None
        else:
            soup = get_soup(driver, search_url)

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
                get_shop_details(driver, href)
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

        # 店舗ページから検索結果へ戻してから「>」をクリックする。
        if get_soup(driver, search_url) is None:
            break
        clicked_soup = click_next_page(driver, next_url)
        if clicked_soup is None:
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
