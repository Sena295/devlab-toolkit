# DevLab Toolkit

Coleção de mini-projetos de estudo, **sem front-end HTML**: tudo roda no terminal, com testes automatizados.

> **Aviso:** todos os dados são **100% fictícios**, gerados localmente (IPs de documentação RFC 5737, e-mails `@example.com`, nomes aleatórios). O repositório não contém chaves de API, senhas, tokens nem dados reais. Foi feito apenas para estudo.

| Módulo | Linguagem | O que treina |
|---|---|---|
| [`log_analyzer/`](log_analyzer) | Python | Regex, parsing de logs, detecção de SQLi/XSS/brute force |
| [`file_organizer/`](file_organizer) | Python | `argparse`, `pathlib`, dry-run, journal e *undo* |
| [`scheduler/`](scheduler) | Python + SQL | SQLite, regras de negócio, conflito de horários |
| [`kanban/`](kanban) | JavaScript (Node) | Estado imutável, mover cards (drag & drop lógico), WIP, persistência em JSON |
| [`datagen/`](datagen) | Python | Gerador de dados fictícios (CSV/JSON/SQLite) |
| [`finance_report/`](finance_report) | Python | CSV, regex de categorização, relatório em texto |
| [`url_shortener/`](url_shortener) | Python | API REST de encurtador: base62, alias, expiração, estatísticas de cliques |
| [`auth_service/`](auth_service) | Python | Autenticação: PBKDF2, JWT HS256 feito à mão, refresh com rotação, RBAC, bloqueio por tentativas |
| [`library_api/`](library_api) | Python + SQL | API REST de biblioteca: empréstimos, multa por atraso, ISBN-10 |
| [`httpkit/`](httpkit) | Python | Mini-framework HTTP (rotas, middlewares, testável sem sockets) usado pelas APIs acima |
| [`chat_server/`](chat_server) | JavaScript (Node) | Chat em tempo real via TCP: salas, apelidos, histórico |
| [`bot_engine/`](bot_engine) | Python | Motor de bot (Discord/Telegram): comandos, lembretes, enquetes, calculadora segura |
| [`weather_cli/`](weather_cli) | Python | Clima com Open-Meteo, cache em disco e fallback offline |
| [`tinylang/`](tinylang) | Python | Linguagem de script própria: lexer, parser recursivo descendente, closures, interpretador |
| [`algolab/`](algolab) | Python | Estruturas e algoritmos do zero: LRU, Trie, heap, BST, Bloom filter, DP, N-Rainhas |
| [`kvstore/`](kvstore) | Python | Banco chave-valor com log append-only, CRC, TTL e compactação |
| [`java_bank/`](java_bank) | Java | Domínio bancário: records, enums, transferências atômicas sem deadlock, juros |
| [`java_graph/`](java_graph) | Java | Grafos: BFS/DFS, Dijkstra, ordenação topológica, Kruskal, A* em labirinto |
| [`ts_validator/`](ts_validator) | TypeScript | Biblioteca de validação de schemas com inferência de tipos (estilo zod) |
| [`ts_scheduler/`](ts_scheduler) | TypeScript | Parser de cron + agendador de jobs com retry e backoff |
| [`ts_markdown/`](ts_markdown) | TypeScript | Renderizador de Markdown para o terminal (ANSI), com tabelas |
| [`sql/`](sql) | SQL | Joins, CTEs, *window functions* |
| [`scripts/`](scripts) | Shell | Orquestração dos testes e demos |

Somente biblioteca padrão — nada para instalar além de Python 3.10+, Node 18+, JDK 17+ e Deno 2 (para os módulos TypeScript).

## Como rodar

```bash
bash scripts/run_all.sh                 # testes + demos de tudo

python -m log_analyzer demo             # analisa logs sintéticos
python -m log_analyzer generate out/    # grava access.log e auth.log fictícios
python -m log_analyzer analyze --access out/access.log --auth out/auth.log --markdown relatorio.md

python -m file_organizer demo           # pasta temporária, organiza e desfaz
python -m file_organizer organize ~/Downloads --dry-run --by-date

python -m scheduler demo
python -m tinylang demo                 # interpretador próprio
(cd java_bank && javac -d out src/bank/*.java && java -cp out bank.Main)
(cd ts_markdown && deno run --allow-read src/markdown.ts ../README.md)
python -m bot_engine.engine               # bot interativo no terminal
python -m url_shortener.service         # API em http://127.0.0.1:8000
node chat_server/server.js              # chat TCP (use: nc 127.0.0.1 4000)
python -m weather_cli.weather "Recife"
python -m scheduler --db agenda.db book "Sala Azul" "Ana" 2025-03-10T09:00 2025-03-10T10:00

node kanban/cli.js demo
node kanban/cli.js --file q.json add "Estudar regex" -p high -t estudo

python -m finance_report.report            # relatório de finanças de exemplo
python -m datagen.generate out/ && sqlite3 out/loja.db < sql/analytics.sql
```

## Exemplo de saída (log analyzer)

```
[XXX]  CRITICAL  possible_compromise  198.51.100.7     x1
        login bem-sucedido de 'deploy' após 8 falhas
[!!]   HIGH      ssh_bruteforce       198.51.100.7     x8
[!!]   HIGH      sql_injection        192.0.2.99       x5
```

## Testes

```bash
for m in log_analyzer file_organizer scheduler datagen finance_report url_shortener auth_service library_api bot_engine weather_cli; do python -m unittest discover -s $m/tests -t .; done
(cd kanban && node --test); (cd chat_server && node --test)
```

## Segurança

- Sem credenciais ou serviços externos; nada faz chamadas de rede.
- `file_organizer` nunca sobrescreve arquivos (sufixo ` (1)`), ignora ocultos e grava um journal para desfazer.
- Consultas SQL usam parâmetros (`?`), nunca concatenação de strings.

## Licença

MIT
