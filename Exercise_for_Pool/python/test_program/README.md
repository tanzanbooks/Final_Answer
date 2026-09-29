## テスト用ファイル一覧

| 修正項目 | ファイル | 確認する内容 | 確認結果 |
| --- | --- | --- | --- |
| 1. 住所の分割を `sample.csv` に合わせる | `test_address.py` | 都道府県・市区町村・番地・建物名への分割 | 24/24件一致（sample.csvから作成した模擬HTML） |
| 2. メールアドレスの取得対象を修正する | `test_LIGNOSA_CAFE.py` | LIGNOSA CAFEのメールアドレス `info@lignosa.com` の取得（実行時表示） | `info@lignosa.com` を表示。SSLは `False`（最終URLがHTTP） |
| 2. メールアドレスの取得対象を修正する | `test_email_body.py` | 本文・サイト運営者のメールを除外し、店舗メールを取得 | OK：`shop@example.com` のみ取得（テスト用データ） |
| 3. ホームページURLの取得を修正する | `test_shop_url.py` | `#`、優先順位、代替URL、CAPTCHA、中継URL、接続失敗時の元URL保持 | 6/6件OK（テスト用URL・模擬エラー） |
| 4. SSLを証明書の検証結果に基づいて判定する | `test_ssl_validation.py` | `1-2.py`・`2-2.py` の正常HTTPS、証明書エラー、タイムアウト、接続エラーと `verify=True` | 8/8件OK（模擬通信） |
| 4. SSLを証明書の検証結果に基づいて判定する | `test_ssl_errors.py` | 提出用 `1-1.py` の接続エラー・CAPTCHA判定と、元URL・原因・メッセージを含むログ用の行 | 2/2件OK（模擬通信、CSVへの保存は対象外） |
| 4. SSLを証明書の検証結果に基づいて判定する | `test_ssl_error_csv.py` | `1-1.py` の接続失敗・CAPTCHA判定と、テスト自身による専用CSVへの保存・読み直し | 3/3件OK（模擬通信） |
| 4. SSLを証明書の検証結果に基づいて判定する | `test_ssl_errors_output.csv` | 上記テストが生成したエラー記録例 | 2件保存を実行表示で確認（接続エラー・CAPTCHA） |
| 5. 空欄行を追加して50行にしない | `test_true50.py` | `1-1.csv` の行数・全空欄行・店舗名とURLの空欄・`#`・`javascript:` | OK：50行、各問題行0件（保存済みCSVの検査） |
| 6. Seleniumでは指定された「>」ボタンをクリックする | `test_next_button.py` | ページ番号0回・「>」1回クリック、`?p=2` のURLとHTMLを確認 | 3/3件OK（偽のWebDriver）ハイライトのスクリーンショットtest_real_next_button_highlight.png別添 |
| 6. Seleniumでは指定された「>」ボタンをクリックする | `test_real_next_button.py` | 画像alt「次（2）ページを表示」の矢印ボタンを黄色・赤枠で目視確認し、提出用関数でクリック。`?p=2` への遷移とHTMLを確認 | OK（実サイト・画面確認） |
| 7. Seleniumのクリック前にも3秒待機する | `test_selenium_wait_before_click.py` | 提出用 `1-2.py` の店舗リンククリックで `sleep(3) → 時間記録 → click()` の順序を確認 | 4/4件OK（模擬WebDriver。クリック後にも別の `sleep(3)`） |

註）LIGNOSA CAFEのSSL表示は項目4の証明書エラー検証とは別の確認結果です。
