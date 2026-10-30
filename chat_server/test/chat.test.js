'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const net = require('node:net');
const { createServer } = require('../server');

function connect(port) {
  return new Promise((resolve) => {
    const socket = net.connect(port, '127.0.0.1');
    socket.setEncoding('utf8');
    const lines = [];
    const waiters = [];
    let buf = '';
    socket.on('data', (d) => {
      buf += d;
      let i;
      while ((i = buf.indexOf('\n')) !== -1) {
        lines.push(buf.slice(0, i));
        buf = buf.slice(i + 1);
      }
      waiters.splice(0).forEach((w) => w());
    });
    const client = {
      socket,
      send: (t) => socket.write(t + '\n'),
      // resolves when a line matching `re` arrives (checks lines already received first)
      expect: (re, ms = 1000) => new Promise((res, rej) => {
        const timer = setTimeout(() => rej(new Error(`timeout esperando ${re}; recebido: ${JSON.stringify(lines)}`)), ms);
        const check = () => {
          const hit = lines.find((l) => re.test(l));
          if (hit) { clearTimeout(timer); res(hit); } else waiters.push(check);
        };
        check();
      }),
      lines,
    };
    socket.once('connect', () => resolve(client));
  });
}

async function withServer(fn) {
  const server = createServer();
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const clients = [];
  const open = async () => { const c = await connect(server.address().port); clients.push(c); await c.expect(/bem-vindo/); return c; };
  try {
    await fn(open);
  } finally {
    clients.forEach((c) => c.socket.destroy());
    await new Promise((r) => server.close(r));
  }
}

test('messages reach other users in the same room only', () => withServer(async (open) => {
  const a = await open(), b = await open(), c = await open();
  a.send('/nick ana'); b.send('/nick bia'); c.send('/nick caio');
  c.send('/join outra');
  await c.expect(/você está em #outra/);
  a.send('olá pessoal');
  await b.expect(/\[#lobby\] ana: olá pessoal/);
  await new Promise((r) => setTimeout(r, 50));
  assert.equal(c.lines.some((l) => l.includes('olá pessoal')), false);
}));

test('nickname validation and uniqueness', () => withServer(async (open) => {
  const a = await open(), b = await open();
  a.send('/nick ana');
  b.send('/nick x');
  await b.expect(/apelido inválido/);
  b.send('/nick ana');
  await b.expect(/já em uso/);
}));

test('history, who and rooms commands', () => withServer(async (open) => {
  const a = await open();
  a.send('/nick ana');
  a.send('primeira');
  a.send('/history');
  await a.expect(/ana: primeira/);
  a.send('/who');
  await a.expect(/na sala: ana/);
  a.send('/rooms');
  await a.expect(/#lobby\(1\)/);
  a.send('/foo');
  await a.expect(/comando desconhecido/);
}));

test('leave notification on disconnect', () => withServer(async (open) => {
  const a = await open(), b = await open();
  b.send('/nick bia');
  a.send('/nick ana');
  await a.expect(/ana/);
  b.socket.destroy();
  await a.expect(/bia saiu/);
}));
