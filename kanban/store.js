'use strict';
// JSON file persistence (the Node counterpart of localStorage).
const fs = require('node:fs');
const { createBoard } = require('./board');

function load(file) {
  if (!fs.existsSync(file)) return createBoard();
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function save(file, board) {
  // write to a temp file first so a crash never leaves a half-written board
  const tmp = `${file}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(board, null, 2));
  fs.renameSync(tmp, file);
}

module.exports = { load, save };
