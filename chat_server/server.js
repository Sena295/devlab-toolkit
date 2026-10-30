'use strict';
// Real-time chat over TCP (line-based protocol, Node `net` only). Rooms, nicknames, history.
//
//   /nick <name>   /join <room>   /rooms   /who   /history   /quit     anything else = message

const net = require('node:net');

const NICK_RE = /^[A-Za-z0-9_]{2,16}$/;
const ROOM_RE = /^[a-z0-9-]{1,20}$/;
const HISTORY_LIMIT = 50;
const MAX_LINE = 500;

class ChatHub {
  constructor() {
    this.clients = new Map(); // socket -> { nick, room }
    this.history = new Map(); // room -> [{ at, nick, text }]
  }

  nicks() {
    return [...this.clients.values()].map((c) => c.nick);
  }

  roomMembers(room) {
    return [...this.clients.entries()].filter(([, c]) => c.room === room);
  }

  send(socket, text) {
    if (!socket.destroyed) socket.write(text + '\n');
  }

  broadcast(room, text, except = null) {
    for (const [socket] of this.roomMembers(room)) if (socket !== except) this.send(socket, text);
  }

  record(room, nick, text) {
    const list = this.history.get(room) ?? [];
    list.push({ at: Date.now(), nick, text });
    if (list.length > HISTORY_LIMIT) list.shift();
    this.history.set(room, list);
  }

  connect(socket) {
    this.clients.set(socket, { nick: `guest${this.clients.size + 1}`, room: 'lobby' });
    const me = this.clients.get(socket);
    this.send(socket, `* bem-vindo, ${me.nick}! Comandos: /nick /join /rooms /who /history /quit`);
    this.broadcast('lobby', `* ${me.nick} entrou em #lobby`, socket);
  }

  disconnect(socket) {
    const me = this.clients.get(socket);
    if (!me) return;
    this.clients.delete(socket);
    this.broadcast(me.room, `* ${me.nick} saiu`);
  }

  handle(socket, rawLine) {
    const me = this.clients.get(socket);
    const line = rawLine.trim().slice(0, MAX_LINE);
    if (!me || !line) return;
    if (!line.startsWith('/')) {
      this.record(me.room, me.nick, line);
      this.broadcast(me.room, `[#${me.room}] ${me.nick}: ${line}`);
      return;
    }
    const [cmd, ...rest] = line.split(/\s+/);
    const arg = rest.join(' ');
    switch (cmd) {
      case '/nick': {
        if (!NICK_RE.test(arg)) return this.send(socket, '! apelido inválido (2-16 letras, números ou _)');
        if (this.nicks().includes(arg)) return this.send(socket, '! apelido já em uso');
        this.broadcast(me.room, `* ${me.nick} agora é ${arg}`);
        me.nick = arg;
        return;
      }
      case '/join': {
        if (!ROOM_RE.test(arg)) return this.send(socket, '! sala inválida (a-z, 0-9, -)');
        this.broadcast(me.room, `* ${me.nick} saiu da sala`, socket);
        me.room = arg;
        this.broadcast(arg, `* ${me.nick} entrou em #${arg}`, socket);
        return this.send(socket, `* você está em #${arg} (${this.roomMembers(arg).length} online)`);
      }
      case '/rooms': {
        const counts = {};
        for (const c of this.clients.values()) counts[c.room] = (counts[c.room] ?? 0) + 1;
        return this.send(socket, '* salas: ' + Object.entries(counts).map(([r, n]) => `#${r}(${n})`).join(' '));
      }
      case '/who':
        return this.send(socket, '* na sala: ' + this.roomMembers(me.room).map(([, c]) => c.nick).join(', '));
      case '/history': {
        const list = this.history.get(me.room) ?? [];
        if (!list.length) return this.send(socket, '* sem histórico');
        for (const m of list.slice(-10)) this.send(socket, `  ${new Date(m.at).toISOString().slice(11, 19)} ${m.nick}: ${m.text}`);
        return;
      }
      case '/quit':
        return socket.end('* até logo\n');
      default:
        return this.send(socket, `! comando desconhecido: ${cmd}`);
    }
  }
}

function createServer(hub = new ChatHub()) {
  return net.createServer((socket) => {
    socket.setEncoding('utf8');
    hub.connect(socket);
    let buffer = '';
    socket.on('data', (chunk) => {
      buffer += chunk;
      if (buffer.length > 4096) return socket.destroy(); // protects against clients that never send "\n"
      let i;
      while ((i = buffer.indexOf('\n')) !== -1) {
        hub.handle(socket, buffer.slice(0, i));
        buffer = buffer.slice(i + 1);
      }
    });
    socket.on('close', () => hub.disconnect(socket));
    socket.on('error', () => socket.destroy());
  });
}

if (require.main === module) {
  const port = Number(process.env.PORT || 4000);
  createServer().listen(port, '127.0.0.1', () => console.log(`chat em 127.0.0.1:${port} (use: nc 127.0.0.1 ${port})`));
}

module.exports = { ChatHub, createServer };
