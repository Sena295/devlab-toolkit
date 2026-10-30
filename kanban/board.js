'use strict';
// Kanban domain model. Pure functions over a plain object: easy to test, easy to persist.

const DEFAULT_COLUMNS = ['backlog', 'doing', 'review', 'done'];
const PRIORITIES = ['low', 'medium', 'high'];

function createBoard(name = 'Meu quadro', columns = DEFAULT_COLUMNS) {
  return {
    name,
    nextId: 1,
    columns: columns.map((title) => ({ title, wip: null, cards: [] })),
  };
}

function findColumn(board, title) {
  const col = board.columns.find((c) => c.title === title);
  if (!col) throw new Error(`coluna '${title}' não existe`);
  return col;
}

function locate(board, id) {
  for (const col of board.columns) {
    const index = col.cards.findIndex((c) => c.id === id);
    if (index !== -1) return { col, index, card: col.cards[index] };
  }
  throw new Error(`card #${id} não encontrado`);
}

function addCard(board, title, { column = board.columns[0].title, priority = 'medium', tags = [] } = {}) {
  if (!title || !title.trim()) throw new Error('título obrigatório');
  if (!PRIORITIES.includes(priority)) throw new Error(`prioridade inválida: ${priority}`);
  const col = findColumn(board, column);
  assertWip(col);
  const card = { id: board.nextId++, title: title.trim(), priority, tags: [...tags], createdAt: new Date().toISOString() };
  col.cards.push(card);
  return card;
}

function assertWip(col) {
  if (col.wip !== null && col.cards.length >= col.wip) {
    throw new Error(`limite WIP (${col.wip}) atingido em '${col.title}'`);
  }
}

// Equivalent of a drag & drop: take a card from wherever it is and drop it at `position` in `to`.
function moveCard(board, id, to, position = Infinity) {
  const { col: from, index } = locate(board, id);
  const dest = findColumn(board, to);
  if (dest !== from) assertWip(dest);
  const [card] = from.cards.splice(index, 1);
  const at = Math.max(0, Math.min(position, dest.cards.length));
  dest.cards.splice(at, 0, card);
  return card;
}

function removeCard(board, id) {
  const { col, index } = locate(board, id);
  return col.cards.splice(index, 1)[0];
}

function setWip(board, title, limit) {
  const col = findColumn(board, title);
  if (limit !== null && (!Number.isInteger(limit) || limit < 1)) throw new Error('WIP deve ser inteiro >= 1');
  col.wip = limit;
}

function search(board, term) {
  const t = term.toLowerCase();
  return board.columns.flatMap((col) =>
    col.cards
      .filter((c) => c.title.toLowerCase().includes(t) || c.tags.some((g) => g.toLowerCase() === t))
      .map((c) => ({ ...c, column: col.title })),
  );
}

function stats(board) {
  const total = board.columns.reduce((n, c) => n + c.cards.length, 0);
  const done = board.columns[board.columns.length - 1].cards.length;
  return {
    total,
    done,
    progress: total ? Math.round((done / total) * 100) : 0,
    perColumn: Object.fromEntries(board.columns.map((c) => [c.title, c.cards.length])),
  };
}

module.exports = { createBoard, addCard, moveCard, removeCard, setWip, search, stats, locate, findColumn, PRIORITIES };
