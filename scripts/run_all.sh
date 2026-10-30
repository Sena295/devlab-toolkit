#!/usr/bin/env bash
# Roda os testes e as demos de todos os módulos.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== Testes Python =="
for m in log_analyzer file_organizer scheduler datagen finance_report url_shortener auth_service library_api bot_engine weather_cli tinylang algolab kvstore; do
  python -m unittest discover -s "$m/tests" -t .
done

echo "== Testes Node =="
(cd kanban && node --test)
(cd chat_server && node --test)

echo "== Testes Java =="
for m in java_bank java_graph; do
  (cd "$m" && rm -rf out && javac -d out src/*/*.java && java -cp out "$(ls src)".Tests)
done

echo "== Testes TypeScript (Deno) =="
for m in ts_validator ts_scheduler ts_markdown; do
  (cd "$m" && deno test)
done

echo "== Demos =="
python -m log_analyzer demo || true   # exit 1 = achados graves (esperado na demo)
python -m file_organizer demo
python -m scheduler demo
(cd kanban && node cli.js demo)
python -m finance_report.report
python -m tinylang demo | tail -3
(cd java_bank && java -cp out bank.Main | tail -3)
(cd java_graph && java -cp out graph.Main | tail -3)
