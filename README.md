<div align="center">

# DevLab Toolkit

**Coleção de mini-projetos de estudo em Python, Java, TypeScript, JavaScript e SQL, todos no terminal e com testes automatizados.**

[![CI](https://github.com/Sena295/devlab-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/Sena295/devlab-toolkit/actions/workflows/ci.yml)
[![Licença MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-blue?style=for-the-badge)](LICENSE)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Java](https://img.shields.io/badge/Java-ED8B00?style=flat-square&logo=openjdk&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![SQL](https://img.shields.io/badge/SQL-4479A1?style=flat-square&logo=sqlite&logoColor=white)

[**Ver os módulos**](#módulos) · [Como usar](#como-usar) · [Reportar problema](https://github.com/Sena295/devlab-toolkit/issues)

</div>

---

## Sobre o projeto

Cada pasta é um projeto independente que treina um tema: regex e análise de logs, CLI com `argparse`, APIs REST, autenticação JWT, interpretador próprio, grafos, banco chave-valor, validação de schemas, chat em tempo real e mais. Não há interface web: o resultado aparece no terminal e é garantido por testes.

> **Todos os dados são fictícios.** IPs de documentação (RFC 5737), e-mails `@example.com`, nomes e valores gerados aleatoriamente, apenas para estudo. O repositório não contém chaves de API, senhas, tokens nem dados reais.

## Módulos

| Módulo | Linguagem | O que treina |
|---|---|---|
| [`log_analyzer/`](log_analyzer) | Python | Regex, parsing de logs, detecção de SQLi/XSS/brute force |
| [`file_organizer/`](file_organizer) | Python | `argparse`, `pathlib`, dry-run, journal e *undo* |
| [`scheduler/`](scheduler) | Python + SQL | SQLite, regras de negócio, conflito de horários |
| [`kanban/`](kanban) | JavaScript (Node) | Estado imutável, mover cards (drag & drop lógico), WIP, persistência em JSON |
| [`datagen/`](datagen) | Python | Gerador de dados fictícios (CSV/JSON/SQLite) |
| [`finance_report/`](finance_report) | Python | CSV, regex de categorização, relatório em texto |
| [`url_shortener/`](url_shortener) | Python | API REST de encurtador: base62, alias, expiração, estatísticas de cliques |
| [`auth_service/`](auth_service) | Python | PBKDF2, JWT HS256 feito à mão, refresh com rotação, RBAC, bloqueio por tentativas |
| [`library_api/`](library_api) | Python + SQL | API REST de biblioteca: empréstimos, multa por atraso, ISBN-10 |
| [`httpkit/`](httpkit) | Python | Mini-framework HTTP (rotas, middlewares, testável sem sockets) usado pelas APIs |
| [`chat_server/`](chat_server) | JavaScript (Node) | Chat em tempo real via TCP: salas, apelidos, histórico |
| [`bot_engine/`](bot_engine) | Python | Motor de bot (Discord/Telegram): comandos, lembretes, enquetes, calculadora segura |
| [`weather_cli/`](weather_cli) | Python | Clima com Open-Meteo, cache em disco e fallback offline |
| [`tinylang/`](tinylang) | Python | Linguagem de script própria: lexer, parser recursivo descendente, closures, interpretador |
| [`algolab/`](algolab) | Python | Estruturas e algoritmos do zero: LRU, Trie, heap, BST, Bloom filter, DP, N-Rainhas |
| [`kvstore/`](kvstore) | Python | Banco chave-valor com log append-only, CRC, TTL e compactação |
| [`java_bank/`](java_bank) | Java | Records, enums, transferências atômicas sem deadlock, juros |
| [`java_graph/`](java_graph) | Java | BFS/DFS, Dijkstra, ordenação topológica, Kruskal, A* em labirinto |
| [`ts_validator/`](ts_validator) | TypeScript | Validação de schemas com inferência de tipos (estilo zod) |
| [`ts_scheduler/`](ts_scheduler) | TypeScript | Parser de cron + agendador de jobs com retry e backoff |
| [`ts_markdown/`](ts_markdown) | TypeScript | Renderizador de Markdown para o terminal (ANSI), com tabelas |
| [`sql/`](sql) | SQL | Joins, CTEs, *window functions* |
| [`scripts/`](scripts) | Shell | Orquestração dos testes e das demos |

## Como usar

Requisitos: **Python 3.10+**, **Node 18+**, **JDK 17+** e **Deno 2** (só para os módulos TypeScript). Não há dependências externas a instalar.

```bash
git clone https://github.com/Sena295/devlab-toolkit.git
cd devlab-toolkit

bash scripts/run_all.sh                 # testes + demos de tudo
```

Exemplos por módulo:

```bash
python -m log_analyzer demo             # analisa logs sintéticos
python -m log_analyzer generate out/    # grava access.log e auth.log fictícios
python -m log_analyzer analyze --access out/access.log --auth out/auth.log --markdown relatorio.md

python -m file_organizer demo           # pasta temporária: organiza e desfaz
python -m file_organizer organize ~/Downloads --dry-run --by-date

python -m scheduler demo
python -m scheduler --db agenda.db book "Sala Azul" "Ana" 2025-03-10T09:00 2025-03-10T10:00

python -m tinylang demo                 # interpretador próprio
python -m bot_engine.engine             # bot interativo no terminal
python -m url_shortener.service         # API em http://127.0.0.1:8000
python -m weather_cli.weather "Recife"
python -m finance_report.report         # relatório de finanças de exemplo
python -m datagen.generate out/ && sqlite3 out/loja.db < sql/analytics.sql

node kanban/cli.js demo
node kanban/cli.js --file q.json add "Estudar regex" -p high -t estudo
node chat_server/server.js              # chat TCP (use: nc 127.0.0.1 4000)

(cd java_bank && javac -d out src/bank/*.java && java -cp out bank.Main)
(cd ts_markdown && deno run --allow-read src/markdown.ts ../README.md)
```

## Exemplo de saída

Analisador de logs (`python -m log_analyzer demo`):

```
[XXX]  CRITICAL  possible_compromise  198.51.100.7     x1
        login bem-sucedido de 'deploy' após 8 falhas
[!!]   HIGH      ssh_bruteforce       198.51.100.7     x8
[!!]   HIGH      sql_injection        192.0.2.99       x5
```

## Testes

Cada módulo tem a sua suíte, e o GitHub Actions roda todas a cada push (Python, Node, Java e Deno).

```bash
for m in log_analyzer file_organizer scheduler datagen finance_report url_shortener auth_service library_api bot_engine weather_cli tinylang algolab kvstore; do
  python -m unittest discover -s $m/tests -t .
done
(cd kanban && node --test); (cd chat_server && node --test)
(cd java_bank && javac -d out src/*/*.java && java -cp out bank.Tests)
(cd ts_validator && deno test)
```

## Estrutura

```
devlab-toolkit/
├── log_analyzer/  file_organizer/  scheduler/  datagen/  finance_report/
├── url_shortener/ auth_service/    library_api/ httpkit/  bot_engine/ weather_cli/
├── tinylang/      algolab/         kvstore/                # Python
├── java_bank/     java_graph/                              # Java
├── ts_validator/  ts_scheduler/    ts_markdown/            # TypeScript
├── kanban/        chat_server/                             # JavaScript (Node)
├── sql/           scripts/
├── .github/workflows/ci.yml
├── LICENSE
└── README.md
```

## Segurança

- Sem credenciais nem serviços externos: nada além do `weather_cli` faz chamadas de rede, e ele usa uma API pública sem chave.
- `file_organizer` nunca sobrescreve arquivos (sufixo ` (1)`), ignora arquivos ocultos e grava um journal para desfazer.
- Consultas SQL usam parâmetros (`?`), nunca concatenação de strings.
- `auth_service` e `kvstore` são implementações de estudo; em produção prefira bibliotecas auditadas.

## Pacotes

Este projeto usa apenas a biblioteca padrão de cada linguagem (sem npm, pip nem Maven) e não publica pacotes.

## Licença

Distribuído sob a licença **MIT**. Veja [LICENSE](LICENSE).

## Autor

Desenvolvido por **Carlos Sena**, [@Sena295](https://github.com/Sena295).
