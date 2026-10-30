'use strict';
// Renders a board as text columns for the terminal.

const MARK = { high: '!!!', medium: '!! ', low: '!  ' };

function pad(text, width) {
  const s = String(text);
  return s.length > width ? s.slice(0, width - 1) + '…' : s.padEnd(width);
}

function renderBoard(board, width = 22) {
  const sep = '+' + board.columns.map(() => '-'.repeat(width + 2)).join('+') + '+';
  const row = (cells) => '| ' + cells.map((c) => pad(c, width)).join(' | ') + ' |';
  const header = board.columns.map((c) => {
    const limit = c.wip === null ? '' : `/${c.wip}`;
    return `${c.title.toUpperCase()} (${c.cards.length}${limit})`;
  });
  const height = Math.max(0, ...board.columns.map((c) => c.cards.length));
  const lines = [`# ${board.name}`, sep, row(header), sep];
  for (let i = 0; i < height; i++) {
    lines.push(row(board.columns.map((c) => (c.cards[i] ? `#${c.cards[i].id} ${c.cards[i].title}` : ''))));
    lines.push(row(board.columns.map((c) => (c.cards[i] ? `  ${MARK[c.cards[i].priority]} ${c.cards[i].tags.map((t) => '@' + t).join(' ')}` : ''))));
  }
  lines.push(sep);
  return lines.join('\n');
}

module.exports = { renderBoard };
