#!/usr/bin/env bash
# Полная сборка: таблица → заготовки и связи → рисунки → книги в PDF.
# Запуск из корня проекта:  ./инструменты/sobrat.sh
# Только одна книга:         ./инструменты/sobrat.sh пилот   (или теория / практика / шпора)
set -e
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
mkdir -p сборка выпуск рисунки/готовые

echo "1/3 Таблица → связи и заготовки"
python3 инструменты/generate.py

echo "2/3 Рисунки (пересобираются только изменённые)"
for f in рисунки/исходники/*.tex; do
  [ -e "$f" ] || continue
  n="$(basename "${f%.tex}")"
  if [ ! -f "рисунки/готовые/$n.pdf" ] || [ "$f" -nt "рисунки/готовые/$n.pdf" ] || [ стиль/рисунки.sty -nt "рисунки/готовые/$n.pdf" ]; then
    ( cd рисунки/исходники && TEXINPUTS="$ROOT:" xelatex -interaction=nonstopmode -halt-on-error \
        -output-directory=../готовые "$n.tex" >/dev/null ) \
      || { echo "   ОШИБКА в рисунке $n — смотри рисунки/готовые/$n.log"; exit 1; }
    rm -f "рисунки/готовые/$n.aux" "рисунки/готовые/$n.log"
    echo "   рисунок $n"
  fi
done

run() {  # $1 — имя книги
  TEXINPUTS="$ROOT/сборка:" xelatex -interaction=nonstopmode -halt-on-error \
    -output-directory=сборка "$1.tex" >/dev/null \
    || { echo "   ОШИБКА в $1 — смотри сборка/$1.log"; grep -m5 -A3 "^!" "сборка/$1.log"; exit 1; }
}

echo "3/3 Книги"
books="${1:-теория практика шпора пилот}"
for b in $books; do run "$b"; run "$b"; run "$b"; done   # 3 прохода: таблицы и колонтитулы берут позиции из прошлого прохода
# второй проход: номера страниц из соседней книги
for b in $books; do
  if [ "$b" = теория ] || [ "$b" = практика ]; then run "$b"; fi
done
for b in $books; do cp "сборка/$b.pdf" "выпуск/$b.pdf"; echo "   выпуск/$b.pdf"; done
# темы, которые не влезли на одну страницу и продолжаются на следующей
dl="$(for b in $books; do grep -h "^PF-DLINNAYA:" "сборка/$b.log" 2>/dev/null; done | sed 's/PF-DLINNAYA: //' | sort -u | tr '\n' ' ')"
[ -n "$dl" ] && echo "Длинные темы (больше страницы, идут с продолжением): $dl"
true
