"""
sample.csv の住所24件を使い、
1-1.py の get_address_parts() の分割結果を確認する。
"""

from pathlib import Path
import importlib.util
from html import escape

import pandas as pd
from bs4 import BeautifulSoup


TEST_DIR = Path(__file__).resolve().parent
SAMPLE_FILE = TEST_DIR / "sample.csv"
PROGRAM_FILE = TEST_DIR.parent / "ex1_web-scraping" / "1-1.py"


# 1-1.pyを読み込む
spec = importlib.util.spec_from_file_location("program_1_1", PROGRAM_FILE)

if spec is None or spec.loader is None:
    raise ImportError(f"読み込めません: {PROGRAM_FILE}")

program = importlib.util.module_from_spec(spec)
spec.loader.exec_module(program)

get_address_parts = program.get_address_parts


def cell_value(row, column):
    """CSVの空欄を空文字にして、前後の空白を除く。"""
    value = row[column]
    return "" if pd.isna(value) else str(value).strip()


df = pd.read_csv(SAMPLE_FILE, encoding="utf-8-sig", dtype=str)

success_count = 0

print("===== 住所分割テスト =====")
print()

for index, row in df.iterrows():
    prefecture = cell_value(row, "都道府県")
    city = cell_value(row, "市区町村")
    street = cell_value(row, "番地")
    building = cell_value(row, "建物名")

    expected = (prefecture, city, street, building)

    # sample.csvの列から、店舗ページの住所欄に相当するHTMLを作る
    full_address = prefecture + city + street
    if building:
        full_address += " " + building

    html = (
        "<table><tr><th>住所</th><td>"
        + escape(full_address)
        + "</td></tr></table>"
    )
    soup = BeautifulSoup(html, "html.parser")

    actual = get_address_parts(soup)

    if actual == expected:
        result = "OK"
        success_count += 1
    else:
        result = "NG"

    print(f"{index + 1:2}件目: {result}")

    if result == "NG":
        print(f"   元住所 : {full_address}")
        print(f"   正解   : {expected}")
        print(f"   実際   : {actual}")
        print()

print()
print("----------------------------------------")
print(f"住所分割テスト結果: {success_count}/{len(df)} 一致")
print("----------------------------------------")

if success_count == len(df):
    print("すべての住所がsample.csvと一致しました。")
else:
    print(f"{len(df) - success_count}件の住所が一致しませんでした。")
