#!/usr/bin/env python3
"""Скачивает листы «Темы», «Разборы», «Связи» из Google-таблицы в dannye/*.csv.

Запуск из корня проекта:  python3 instrumenty/obnovit_iz_tablicy.py

Работает, если у таблицы включён доступ «Все, у кого есть ссылка — читатель».
Если доступа по ссылке нет — скачай листы вручную:
Файл → Скачать → CSV (текущий лист) и положи их в dannye/ под именами ниже.
"""
import pathlib
import sys
import urllib.request

TABLICA = "18A87Lsp0tJMdq9rlw9NzHHVljkrN0qQWzxPzeSTOPlg"
LISTY = {  # имя файла: gid листа
    "temy.csv": 1226840405,      # «Темы»
    "razbory.csv": 145441936,    # «Разборы»
    "svyazi.csv": 2014555844,    # «Связи»
}

kuda = pathlib.Path(__file__).resolve().parent.parent / "dannye"
oshibki = 0
for imya, gid in LISTY.items():
    url = f"https://docs.google.com/spreadsheets/d/{TABLICA}/export?format=csv&gid={gid}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            dannye = r.read()
    except Exception as e:  # noqa: BLE001
        print(f"  {imya}: не скачалось ({e})")
        oshibki += 1
        continue
    if dannye.lstrip().startswith(b"<"):
        print(f"  {imya}: Google вернул страницу входа — открой доступ по ссылке или скачай вручную")
        oshibki += 1
        continue
    (kuda / imya).write_bytes(dannye)
    print(f"  {imya}: ок ({dannye.count(b'\n')} строк)")

sys.exit(1 if oshibki else 0)
