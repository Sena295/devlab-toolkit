// Markdown -> ANSI terminal renderer (headings, lists, code, quotes, emphasis, links, tables). No HTML output.

const ESC = "\x1b[";
const style = {
  bold: (s: string) => `${ESC}1m${s}${ESC}22m`,
  italic: (s: string) => `${ESC}3m${s}${ESC}23m`,
  dim: (s: string) => `${ESC}2m${s}${ESC}22m`,
  underline: (s: string) => `${ESC}4m${s}${ESC}24m`,
  red: (s: string) => `${ESC}31m${s}${ESC}39m`,
  cyan: (s: string) => `${ESC}36m${s}${ESC}39m`,
  yellow: (s: string) => `${ESC}33m${s}${ESC}39m`,
};

export type Block =
  | { kind: "heading"; level: number; text: string }
  | { kind: "paragraph"; text: string }
  | { kind: "list"; ordered: boolean; items: string[] }
  | { kind: "code"; lang: string; lines: string[] }
  | { kind: "quote"; lines: string[] }
  | { kind: "table"; header: string[]; rows: string[][] }
  | { kind: "rule" };

const isTableSep = (l: string) => /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(l);
const cells = (l: string) => l.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());

export function parseBlocks(src: string): Block[] {
  const lines = src.replace(/\r\n/g, "\n").split("\n");
  const blocks: Block[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }
    let m: RegExpMatchArray | null;
    if ((m = line.match(/^```(\w*)\s*$/))) {
      const code: string[] = [];
      i++;
      while (i < lines.length && !/^```\s*$/.test(lines[i])) code.push(lines[i++]);
      i++; // closing fence
      blocks.push({ kind: "code", lang: m[1], lines: code });
    } else if ((m = line.match(/^(#{1,6})\s+(.*?)\s*#*$/))) {
      blocks.push({ kind: "heading", level: m[1].length, text: m[2] });
      i++;
    } else if (/^(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) {
      blocks.push({ kind: "rule" });
      i++;
    } else if (/^>\s?/.test(line)) {
      const quote: string[] = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) quote.push(lines[i++].replace(/^>\s?/, ""));
      blocks.push({ kind: "quote", lines: quote });
    } else if (line.includes("|") && i + 1 < lines.length && isTableSep(lines[i + 1])) {
      const header = cells(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].includes("|") && lines[i].trim()) rows.push(cells(lines[i++]));
      blocks.push({ kind: "table", header, rows });
    } else if (/^\s*([-*+]|\d+\.)\s+/.test(line)) {
      const ordered = /^\s*\d+\./.test(line);
      const items: string[] = [];
      while (i < lines.length && /^\s*([-*+]|\d+\.)\s+/.test(lines[i])) items.push(lines[i++].replace(/^\s*([-*+]|\d+\.)\s+/, ""));
      blocks.push({ kind: "list", ordered, items });
    } else {
      const para: string[] = [];
      while (i < lines.length && lines[i].trim() && !/^(#{1,6}\s|```|>|\s*([-*+]|\d+\.)\s)/.test(lines[i])) para.push(lines[i++].trim());
      blocks.push({ kind: "paragraph", text: para.join(" ") });
    }
  }
  return blocks;
}

export function renderInline(text: string): string {
  return text
    .replace(/`([^`]+)`/g, (_, c) => style.yellow(c))
    .replace(/\*\*([^*]+)\*\*|__([^_]+)__/g, (_, a, b) => style.bold(a ?? b))
    .replace(/(?<![*\w])\*([^*\s][^*]*)\*(?!\*)|(?<![_\w])_([^_\s][^_]*)_(?![_\w])/g, (_, a, b) => style.italic(a ?? b))
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label, url) => `${style.underline(style.cyan(label))} ${style.dim(`(${url})`)}`);
}

export const stripAnsi = (s: string) => s.replace(/\x1b\[[0-9;]*m/g, "");

function wrap(text: string, width: number): string[] {
  const out: string[] = [];
  let line = "";
  for (const word of text.split(" ")) {
    if (line && stripAnsi(line).length + 1 + stripAnsi(word).length > width) { out.push(line); line = word; }
    else line = line ? `${line} ${word}` : word;
  }
  if (line) out.push(line);
  return out;
}

function renderTable(header: string[], rows: string[][]): string[] {
  const all = [header, ...rows].map((r) => r.map(renderInline));
  const widths = header.map((_, c) => Math.max(...all.map((r) => stripAnsi(r[c] ?? "").length)));
  const pad = (s: string, w: number) => s + " ".repeat(w - stripAnsi(s).length);
  const line = (r: string[]) => "│ " + widths.map((w, c) => pad(r[c] ?? "", w)).join(" │ ") + " │";
  const bar = (l: string, m: string, r: string) => l + widths.map((w) => "─".repeat(w + 2)).join(m) + r;
  return [bar("┌", "┬", "┐"), line(all[0].map(style.bold)), bar("├", "┼", "┤"), ...all.slice(1).map(line), bar("└", "┴", "┘")];
}

export function render(src: string, width = 80): string {
  const out: string[] = [];
  for (const b of parseBlocks(src)) {
    switch (b.kind) {
      case "heading": {
        const text = renderInline(b.text);
        out.push(b.level === 1 ? style.bold(style.red(text.toUpperCase())) : b.level === 2 ? style.bold(style.red(text)) : style.bold(text));
        if (b.level <= 2) out.push(style.dim((b.level === 1 ? "═" : "─").repeat(Math.min(width, stripAnsi(text).length))));
        break;
      }
      case "paragraph": out.push(...wrap(renderInline(b.text), width)); break;
      case "list":
        b.items.forEach((it, n) => {
          const bullet = b.ordered ? `${n + 1}.` : "•";
          wrap(renderInline(it), width - 4).forEach((l, k) => out.push(k === 0 ? `  ${bullet} ${l}` : `     ${l}`));
        });
        break;
      case "code": out.push(...b.lines.map((l) => style.dim("  │ ") + style.yellow(l))); break;
      case "quote": out.push(...b.lines.map((l) => style.dim("  ▎ ") + style.italic(renderInline(l)))); break;
      case "table": out.push(...renderTable(b.header, b.rows)); break;
      case "rule": out.push(style.dim("─".repeat(width))); break;
    }
    out.push("");
  }
  return out.join("\n").trimEnd() + "\n";
}

if (import.meta.main) {
  const path = Deno.args[0];
  console.log(render(path ? await Deno.readTextFile(path) : "# Demo\n\nUm **teste** com `código` e [link](https://example.com).\n\n- item 1\n- item 2\n"));
}
