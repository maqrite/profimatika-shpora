#!/usr/bin/env bash
# Полная сборка: таблица → заготовки и связи → рисунки → три PDF.
# Запуск из корня проекта:  ./instrumenty/sobrat.sh
# Только одна книга:         ./instrumenty/sobrat.sh shpora   (или teoriya / praktika)
set -e
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
mkdir -p sborka vypusk risunki/build

echo "1/3 Таблица → связи и заготовки"
python3 instrumenty/generate.py

echo "2/3 Рисунки (пересобираются только изменённые)"
for f in risunki/src/*.tex; do
  [ -e "$f" ] || continue
  n="$(basename "${f%.tex}")"
  if [ ! -f "risunki/build/$n.pdf" ] || [ "$f" -nt "risunki/build/$n.pdf" ] || [ stil/profig.sty -nt "risunki/build/$n.pdf" ]; then
    ( cd risunki/src && TEXINPUTS="$ROOT:" xelatex -interaction=nonstopmode -halt-on-error \
        -output-directory=../build "$n.tex" >/dev/null ) \
      || { echo "   ОШИБКА в рисунке $n — смотри risunki/build/$n.log"; exit 1; }
    rm -f "risunki/build/$n.aux" "risunki/build/$n.log"
    echo "   рисунок $n"
  fi
done

run() {  # $1 — имя книги
  TEXINPUTS="$ROOT/sborka:" xelatex -interaction=nonstopmode -halt-on-error \
    -output-directory=sborka "$1.tex" >/dev/null \
    || { echo "   ОШИБКА в $1 — смотри sborka/$1.log"; grep -m5 -A3 "^!" "sborka/$1.log"; exit 1; }
}

echo "3/3 Книги"
books="${1:-teoriya praktika shpora pilot}"
for b in $books; do run "$b"; run "$b"; run "$b"; done   # 3 прохода: таблицы и колонтитулы берут позиции из прошлого прохода
# второй проход: номера страниц из соседней книги
for b in $books; do
  if [ "$b" = teoriya ] || [ "$b" = praktika ]; then run "$b"; fi
done
for b in $books; do cp "sborka/$b.pdf" "vypusk/$b.pdf"; echo "   vypusk/$b.pdf"; done
# темы, которые не влезли на одну страницу и продолжаются на следующей
dl="$(for b in $books; do grep -h "^PF-DLINNAYA:" "sborka/$b.log" 2>/dev/null; done | sed 's/PF-DLINNAYA: //' | sort -u | tr '\n' ' ')"
[ -n "$dl" ] && echo "Длинные темы (больше страницы, идут с продолжением): $dl"
true
