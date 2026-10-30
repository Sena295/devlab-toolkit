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
| [`sql/`](sql) | SQL | Joins, CTEs, *window functions* |
| [`scripts/`](scripts) | Shell | Orquestração dos testes e demos |

Somente biblioteca padrão — nada para instalar além de Python 3.10+ e Node 18+.

## Como rodar

```bash
bash scripts/run_all.sh                 # testes + demos de tudo

python -m log_analyzer demo             # analisa logs sintéticos
python -m log_analyzer generate out/    # grava access.log e auth.log fictícios
python -m log_analyzer analyze --access out/access.log --auth out/auth.log --markdown relatorio.md

python -m file_organizer demo           # pasta temporária, organiza e desfaz
python -m file_organizer organize ~/Downloads --dry-run --by-date

python -m scheduler demo
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
for m in log_analyzer file_organizer scheduler datagen finance_report; do python -m unittest discover -s $m/tests -t .; done
cd kanban && node --test
```

## Segurança

- Sem credenciais ou serviços externos; nada faz chamadas de rede.
- `file_organizer` nunca sobrescreve arquivos (sufixo ` (1)`), ignora ocultos e grava um journal para desfazer.
- Consultas SQL usam parâmetros (`?`), nunca concatenação de strings.

## Licença

MIT
