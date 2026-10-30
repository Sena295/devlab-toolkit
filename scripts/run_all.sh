#!/usr/bin/env bash
# Roda os testes e as demos de todos os módulos.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== Testes Python =="
for m in log_analyzer file_organizer scheduler datagen finance_report; do
  python -m unittest discover -s "$m/tests" -t .
done

echo "== Testes Node =="
(cd kanban && node --test)

echo "== Demos =="
python -m log_analyzer demo || true   # exit 1 = achados graves (esperado na demo)
python -m file_organizer demo
python -m scheduler demo
(cd kanban && node cli.js demo)
python -m finance_report.report
