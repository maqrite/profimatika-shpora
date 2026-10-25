#!/usr/bin/env python3
"""Генератор: таблица (данные/*.csv) → служебные файлы книги (сгенерировано/*.tex)
и заготовки новых тем и разборов (теория/, практика/).

Ничего, что уже написано руками, не перезаписывает: заготовка создаётся,
только если файла темы или разбора ещё нет.

Запуск из корня проекта:  python3 инструменты/generate.py
"""
import csv
import os
import re
import sys
from collections import OrderedDict, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "данные")
GEN = os.path.join(ROOT, "сгенерировано")

LAT = {"Ч": "Ch", "А": "A", "Т": "T", "Ф": "F", "Д": "D", "П": "P",
       "К": "K", "С": "S", "В": "V", "М": "M", "Р": "R"}


def translit(code):
    """П3.4 → P3-4, Р16-01 → R16-01 (латиница для внутренних якорей ссылок в PDF)."""
    code = code.strip()
    if not code:
        return ""
    return LAT.get(code[0], code[0]) + code[1:].replace(".", "-")


def tex(s):
    """Экранирование спецсимволов LaTeX в тексте из таблицы."""
    s = (s or "").strip()
    for a, b in (("\\", r"\textbackslash{}"), ("%", r"\%"), ("&", r"\&"),
                 ("#", r"\#"), ("_", r"\_"), ("$", r"\$"), ("^", r"\^{}"),
                 ("~", r"\~{}"), ("{", r"\{"), ("}", r"\}")):
        s = s.replace(a, b)
    return s


def tex_bez_razryva(s):
    """Как tex(), но формулы вида «|x − 2| ≤ 1» не разрываются по строкам."""
    s = tex(s)
    for op in ("−", "≤", "≥", "=", "+", "<", ">", "·", "≠"):
        s = s.replace(f" {op} ", f"~{op}~")
    return s


def codes(s):
    return [c.strip() for c in re.split(r"[;,]", s or "") if c.strip()]


def read(name):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return [], {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    head = rows[0]

    def col(prefix):
        for i, h in enumerate(head):
            if h.strip().startswith(prefix):
                return i
        return None
    return [r for r in rows[1:] if r and r[0].strip()], col


def cell(row, i):
    return row[i].strip() if i is not None and i < len(row) else ""


def main():
    os.makedirs(GEN, exist_ok=True)

    # ---------- Темы ----------
    trows, tc = read("темы.csv")
    if not trows:
        sys.exit("Нет данные/темы.csv — скачай лист «Темы» из Google-таблицы в CSV.")
    c_code, c_sec, c_ch, c_title = tc("Код"), tc("Раздел"), tc("Глава"), tc("Тема")
    c_deps, c_task, c_old = tc("Опирается"), tc("Задание ЕГЭ"), tc("Где в методичке")
    c_pages, c_status, c_order = tc("Стр"), tc("Статус"), tc("Порядок")

    topics = []
    for r in trows:
        code = cell(r, c_code)
        ch_full = cell(r, c_ch)                       # «П3. Прямоугольный треугольник»
        ch_code, _, ch_name = ch_full.partition(". ")
        try:
            order = float(cell(r, c_order).replace(",", "."))
        except ValueError:
            order = 1e9
        topics.append(dict(code=code, tl=translit(code), sec=cell(r, c_sec),
                           ch=ch_code.strip(), ch_name=ch_name.strip(),
                           title=cell(r, c_title), deps=codes(cell(r, c_deps)),
                           tasks=cell(r, c_task), old=cell(r, c_old),
                           pages=cell(r, c_pages), status=cell(r, c_status),
                           order=order))
    known = {t["code"] for t in topics}

    # ---------- Разборы и связи ----------
    rrows, rc = read("разборы.csv")
    razbory = []
    for r in rrows:
        code = cell(r, rc("Код"))
        if not code or "ПРИМЕР" in cell(r, rc("Пример задачи")):
            continue
        task = cell(r, rc("Задание"))
        razbory.append(dict(code=code, tl=translit(code),
                            task=int(task) if task.isdigit() else 0,
                            type=cell(r, rc("Тип")), about=cell(r, rc("Пример задачи"))))
    known_r = {z["code"] for z in razbory}

    srows, sc = read("связи.csv")
    gde = defaultdict(list)                  # тема → ключевые разборы
    nuzhno = defaultdict(lambda: ([], []))   # разбор → (ключевые темы, вспомогательные)
    for r in srows:
        t, z, role = cell(r, sc("Код темы")), cell(r, sc("Код разбора")), cell(r, sc("Роль"))
        if t not in known or z not in known_r:
            continue
        key = role.startswith("ключ")
        if key:
            gde[t].append(z)
        nuzhno[z][0 if key else 1].append(t)

    problems = []
    for t in topics:
        for d in t["deps"]:
            if d not in known:
                problems.append(f"{t['code']}: «Опирается на» ссылается на неизвестную тему {d}")

    # ---------- мета.tex ----------
    chapters = OrderedDict()
    for t in sorted(topics, key=lambda t: t["order"]):
        chapters.setdefault(t["ch"], dict(name=t["ch_name"], sec=t["sec"], topics=[]))
        chapters[t["ch"]]["topics"].append(t)

    L = ["% СГЕНЕРИРОВАНО инструменты/generate.py — руками не править", ""]
    for ch, info in chapters.items():
        L.append(r"\pfDefGlava{%s}{%s}{%s}{%s}" % (ch, translit(ch), tex(info["name"]), tex(info["sec"])))
        L.append(r"\pfGlavaTemy{%s}{%s}" % (ch, ",".join(x["code"] for x in info["topics"])))
    L.append("")
    for t in topics:
        deps = ", ".join(r"\tref{%s}" % d for d in t["deps"])
        # «Где встречается»: до 3 конкретных примеров задач, остальное — «и ещё N»
        zs = gde.get(t["code"], [])
        g = "".join(r"\pfGde{%s}" % z for z in zs[:3])
        if len(zs) > 3:
            g += r"\pfGdeEshche{%d}" % (len(zs) - 3)
        old = t["old"] if t["old"].startswith("—") else (
            f"стр. {t['pages']} (старое задание {t['old']})" if t["pages"] else "")
        L.append(r"\pfDefTema{%s}{%s}{%s}{%s}{%s}{%s}{%s}{%s}" % (
            t["code"], t["tl"], tex(t["title"]), t["ch"], deps,
            tex(t["tasks"]), tex(old), g))
    L.append("")
    for z in razbory:
        k, a = nuzhno.get(z["code"], ([], []))
        L.append(r"\pfDefRazbor{%s}{%s}{%d}{%s}{%s}{%s}{%s}" % (
            z["code"], z["tl"], z["task"], tex(z["type"]),
            ", ".join(r"\tref{%s}" % c for c in k), ", ".join(r"\tref{%s}" % c for c in a),
            tex_bez_razryva(z["about"])))
    po_zad = defaultdict(list)
    for z in sorted(razbory, key=lambda z: z["code"]):
        po_zad[z["task"]].append(z["code"])
    for n in sorted(po_zad):
        L.append(r"\pfZadanieRazbory{%d}{%s}" % (n, ",".join(po_zad[n])))
    write("мета.tex", L)

    # ---------- Содержимое теории ----------
    L = ["% СГЕНЕРИРОВАНО — порядок глав и тем берётся из колонки «Порядок в шпоре»", ""]
    made = 0
    for ch, info in chapters.items():
        L.append(r"\pfEsliGlava{%s}{%%" % ch)
        L.append(r"  \pfGlava{%s}" % ch)
        for t in info["topics"]:
            rel = f"теория/{ch[0]}/{t['code']}.tex"
            L.append(r"  \input{%s}" % rel)
            made += stub_topic(rel, t)
        L.append("}")
    write("содержание-теории.tex", L)

    # ---------- Содержимое практики ----------
    L = ["% СГЕНЕРИРОВАНО — разборы по номерам заданий ЕГЭ-2027", ""]
    cur = None
    for z in sorted(razbory, key=lambda z: (z["task"], z["code"])):
        if z["task"] != cur:
            cur = z["task"]
            L.append(r"\pfZadanie{%d}" % cur)
        rel = f"практика/{z['code']}.tex"
        L.append(r"\input{%s}" % rel)
        made += stub_razbor(rel, z)
    write("содержание-практики.tex", L)

    # ---------- Оглавления ----------
    L = ["% СГЕНЕРИРОВАНО"]
    for ch, info in chapters.items():
        L.append(r"\pfEsliGlava{%s}{\pfStrokaGlavy{%s}}" % (ch, ch))
    write("оглавление-теории.tex", L)
    L = ["% СГЕНЕРИРОВАНО"]
    for task in sorted({z["task"] for z in razbory}):
        L.append(r"\pfStrokaZadaniya{%d}" % task)
    write("оглавление-практики.tex", L)

    # ---------- Указатель «задание → темы» ----------
    by_task = defaultdict(list)
    for t in sorted(topics, key=lambda t: t["order"]):
        for n in codes(t["tasks"]):
            if n.isdigit():
                by_task[int(n)].append(t["code"])
    L = ["% СГЕНЕРИРОВАНО"]
    for n in sorted(by_task):
        L.append(r"\pfUkazatel{%d}{%s}" % (n, ", ".join(r"\trefk{%s}" % c for c in by_task[n])))
    write("указатель.tex", L)

    print(f"Тем: {len(topics)}, глав: {len(chapters)}, разборов: {len(razbory)}, "
          f"связей: {sum(len(v) for v in gde.values())} ключевых. Новых заготовок: {made}.")
    for p in problems:
        print("ВНИМАНИЕ:", p)


def write(name, lines):
    with open(os.path.join(GEN, name), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def stub_topic(rel, t):
    path = os.path.join(ROOT, rel)
    if os.path.exists(path):
        return 0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"% {t['code']} — {t['title']}\n"
                f"% Старая методичка: {t['old']}" + (f", стр. {t['pages']}" if t['pages'] else "") + "\n"
                f"% Что поправить — в Google-таблице, лист «Темы».\n"
                f"% Название, «Опирается на» и «Где встречается» подставляются сами.\n\n"
                f"\\begin{{tema}}{{{t['code']}}}\n\\pfZagotovka\n\\end{{tema}}\n")
    return 1


def stub_razbor(rel, z):
    path = os.path.join(ROOT, rel)
    if os.path.exists(path):
        return 0
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"% {z['code']} — {z['type']}\n\n"
                f"\\begin{{razbor}}{{{z['code']}}}\n\\Uslovie\n\\pfZagotovka\n\\end{{razbor}}\n")
    return 1


if __name__ == "__main__":
    main()
