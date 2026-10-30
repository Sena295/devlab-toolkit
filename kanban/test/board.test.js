'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const b = require('../board');
const store = require('../store');
const { renderBoard } = require('../render');

test('addCard assigns incremental ids and validates input', () => {
  const board = b.createBoard();
  assert.equal(b.addCard(board, 'A').id, 1);
  assert.equal(b.addCard(board, 'B').id, 2);
  assert.throws(() => b.addCard(board, '  '), /título/);
  assert.throws(() => b.addCard(board, 'C', { priority: 'urgent' }), /prioridade/);
  assert.throws(() => b.addCard(board, 'D', { column: 'nope' }), /não existe/);
});

test('moveCard works across columns and respects position', () => {
  const board = b.createBoard();
  [1, 2, 3].forEach((n) => b.addCard(board, `T${n}`));
  b.moveCard(board, 3, 'doing');
  b.moveCard(board, 1, 'doing', 0);
  assert.deepEqual(board.columns[1].cards.map((c) => c.id), [1, 3]);
  assert.deepEqual(board.columns[0].cards.map((c) => c.id), [2]);
});

test('reordering inside the same column', () => {
  const board = b.createBoard();
  [1, 2, 3].forEach((n) => b.addCard(board, `T${n}`));
  b.moveCard(board, 3, 'backlog', 0);
  assert.deepEqual(board.columns[0].cards.map((c) => c.id), [3, 1, 2]);
});

test('WIP limit blocks adds and moves', () => {
  const board = b.createBoard();
  b.setWip(board, 'doing', 1);
  b.addCard(board, 'A');
  b.addCard(board, 'B');
  b.moveCard(board, 1, 'doing');
  assert.throws(() => b.moveCard(board, 2, 'doing'), /WIP/);
  assert.throws(() => b.setWip(board, 'doing', 0), /inteiro/);
});

test('removeCard and unknown ids', () => {
  const board = b.createBoard();
  b.addCard(board, 'A');
  b.removeCard(board, 1);
  assert.throws(() => b.removeCard(board, 1), /não encontrado/);
});

test('search matches title and exact tag', () => {
  const board = b.createBoard();
  b.addCard(board, 'Corrigir login', { tags: ['bug'] });
  b.addCard(board, 'Outra coisa', { tags: ['login'] });
  assert.equal(b.search(board, 'login').length, 2);
  assert.equal(b.search(board, 'bug').length, 1);
});

test('stats computes progress from the last column', () => {
  const board = b.createBoard();
  b.addCard(board, 'A');
  b.addCard(board, 'B');
  b.moveCard(board, 1, 'done');
  assert.deepEqual(b.stats(board), { total: 2, done: 1, progress: 50, perColumn: { backlog: 1, doing: 0, review: 0, done: 1 } });
});

test('store roundtrip', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'kanban-'));
  const file = path.join(dir, 'q.json');
  const board = b.createBoard('X');
  b.addCard(board, 'A');
  store.save(file, board);
  assert.deepEqual(store.load(file), board);
  assert.equal(store.load(path.join(dir, 'missing.json')).name, 'Meu quadro');
  fs.rmSync(dir, { recursive: true });
});

test('render includes column headers and cards', () => {
  const board = b.createBoard('Demo');
  b.addCard(board, 'Tarefa');
  const out = renderBoard(board);
  assert.match(out, /BACKLOG \(1\)/);
  assert.match(out, /#1 Tarefa/);
});
