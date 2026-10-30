#!/usr/bin/env node
'use strict';
const board = require('./board');
const { renderBoard } = require('./render');
const store = require('./store');

const HELP = `Kanban CLI (dados fictícios)

uso: node kanban/cli.js [--file quadro.json] <comando>

  demo                                  mostra um quadro de exemplo
  show                                  imprime o quadro
  add "título" [-c coluna] [-p prioridade] [-t tag,tag]
  move <id> <coluna> [posição]
  rm <id>
  wip <coluna> <limite|off>
  find <termo>
  stats`;

function parseFlags(args) {
  const flags = {};
  const rest = [];
  for (let i = 0; i < args.length; i++) {
    if (args[i].startsWith('-') && args[i].length === 2) flags[args[i][1]] = args[++i];
    else rest.push(args[i]);
  }
  return { flags, rest };
}

function demoBoard() {
  const b = board.createBoard('Lançamento do app (fictício)');
  board.addCard(b, 'Definir escopo do MVP', { priority: 'high', tags: ['produto'] });
  board.addCard(b, 'Desenhar telas de login', { priority: 'medium', tags: ['design'] });
  board.addCard(b, 'Configurar CI', { priority: 'low', tags: ['infra'] });
  board.addCard(b, 'API de usuários', { priority: 'high', tags: ['backend'] });
  board.addCard(b, 'Escrever testes', { priority: 'medium', tags: ['backend', 'qa'] });
  board.setWip(b, 'doing', 2);
  board.moveCard(b, 1, 'done');
  board.moveCard(b, 4, 'doing');
  board.moveCard(b, 2, 'doing');
  board.moveCard(b, 5, 'review');
  return b;
}

function main(argv) {
  let file = 'quadro.json';
  const fi = argv.indexOf('--file');
  if (fi !== -1) file = argv.splice(fi, 2)[1];
  const [cmd, ...args] = argv;
  const { flags, rest } = parseFlags(args);

  if (!cmd || cmd === 'help') return console.log(HELP);
  if (cmd === 'demo') {
    const b = demoBoard();
    console.log(renderBoard(b));
    console.log('\n' + JSON.stringify(board.stats(b)));
    return;
  }

  const b = store.load(file);
  switch (cmd) {
    case 'show': break;
    case 'add': {
      const c = board.addCard(b, rest[0], { column: flags.c, priority: flags.p, tags: flags.t ? flags.t.split(',') : [] });
      console.log(`card #${c.id} criado`);
      break;
    }
    case 'move': board.moveCard(b, Number(rest[0]), rest[1], rest[2] === undefined ? undefined : Number(rest[2])); break;
    case 'rm': board.removeCard(b, Number(rest[0])); break;
    case 'wip': board.setWip(b, rest[0], rest[1] === 'off' ? null : Number(rest[1])); break;
    case 'find': {
      for (const c of board.search(b, rest[0])) console.log(`#${c.id} [${c.column}] ${c.title}`);
      return;
    }
    case 'stats': return console.log(JSON.stringify(board.stats(b), null, 2));
    default: throw new Error(`comando desconhecido: ${cmd}`);
  }
  store.save(file, b);
  console.log(renderBoard(b));
}

try {
  main(process.argv.slice(2));
} catch (err) {
  console.error(`erro: ${err.message}`);
  process.exit(1);
}
