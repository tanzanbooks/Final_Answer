"""
本文にサイト運営者などのメールアドレスがあっても、
誤取得せず、「お店に直接メールする」のメールだけを
取得できるか確認するテスト。
"""

from bs4 import BeautifulSoup


# ==================== 1. テスト用HTML ====================

html = """
<html>
<head>
    <title>メール取得テスト</title>
</head>

<body>

    <h1>テスト店舗</h1>

    <p>
        このサイトについてのお問い合わせは
        site-admin@example.com
        までお願いします。
    </p>

    <p>
        サイト運営者：
        <a href="mailto:operator@example.com">
            operator@example.com
        </a>
    </p>

    <p>
        店舗へのお問い合わせ：
        <a href="mailto:shop@example.com">
            お店に直接メールする
        </a>
    </p>

</body>
</html>
"""


# ==================== 2. HTMLを解析 ====================

soup = BeautifulSoup(
    html,
    "html.parser"
)


# ==================== 3. 1-1.pyと同じメール取得処理 ====================

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


# ==================== 4. テスト結果 ====================

expected_email = "shop@example.com"

print("===== 本文メール誤取得テスト =====")
print()

print(
    "本文のメール:",
    "site-admin@example.com"
)

print(
    "サイト運営者メール:",
    "operator@example.com"
)

print(
    "店舗メール:",
    "shop@example.com"
)

print()

print(
    "期待する取得結果:",
    expected_email
)

print(
    "実際の取得結果:",
    email
)

print()


# ==================== 5. 判定 ====================

if email == expected_email:

    print("テスト結果: OK")

    print(
        "本文・サイト運営者のメールを誤取得せず、"
        "店舗メールだけを取得しました。"
    )

else:

    print("テスト結果: NG")

    print(
        "店舗メール以外を取得した、"
        "またはメールを取得できませんでした。"
    )
