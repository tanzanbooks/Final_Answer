## テスト用ファイル一覧

| 修正項目 | ファイル | 確認する内容 |
| --- | --- | --- |
| 1. 住所の分割を `sample.csv` に合わせる | `test_address.py` | 都道府県・市区町村・番地・建物名への分割 |
| 2. メールアドレスの取得対象を修正する | `test_LIGNOSA_CAFE.py` | LIGNOSA CAFEのメールアドレス `info@lignosa.com` の取得（実行時表示） |
| 2. メールアドレスの取得対象を修正する | `test_email_body.py` | ページ本文からのメールアドレス取得 |
| 3. ホームページURLの取得を修正する | `test_shop_url.py` | 店舗ホームページURLの選別 |
| 4. SSLを証明書の検証結果に基づいて判定する | `test_ssl_validation.py` | SSL証明書の確認 |
| 4. SSLを証明書の検証結果に基づいて判定する | `test_ssl_errors.py` | SSL確認時のエラーの分類 |
| 4. SSLを証明書の検証結果に基づいて判定する | `test_ssl_error_csv.py` | エラー記録用CSVへの出力 |
| 4. SSLを証明書の検証結果に基づいて判定する | `test_ssl_errors_output.csv` | エラー記録の出力例 |
| 5. 空欄行を追加して50行にしない | `test_true50.py` | 取得件数と50件上限の確認 |
| 6. Seleniumでは指定された「>」ボタンをクリックする | `test_next_button.py` | 次ページへの移動処理 |
| 6. Seleniumでは指定された「>」ボタンをクリックする | `test_real_next_button.py` | 実際のページでの次ページボタンの確認 |
| 7. Seleniumのクリック前にも3秒待機する | `test_selenium_wait_before_click.py` | クリック前の3秒待機 |

註）`test_LIGNOSA_CAFE.py` の実行時には、メールアドレスに加えて `SSL: False（最終URLがHTTP）` と表示されました。このSSL表示は、項目4の証明書エラー検証とは別の確認結果です。

これらは個別の確認用ファイルです。実サイトを参照するものは、ページの更新や通信状況によって実行結果が変わる可能性があります。`test_ssl_errors_output.csv` はエラー記録の例であり、提出用の9列CSVとは別です。