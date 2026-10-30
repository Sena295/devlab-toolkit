import assert from "node:assert/strict";
import { parseBlocks, render, renderInline, stripAnsi } from "./markdown.ts";

Deno.test("parses block kinds", () => {
  const blocks = parseBlocks("# T\n\ntexto\nlinha 2\n\n- a\n- b\n\n1. x\n2. y\n\n> citação\n\n---\n\n```js\nlet a = 1;\n```\n");
  assert.deepEqual(blocks.map((b) => b.kind), ["heading", "paragraph", "list", "list", "quote", "rule", "code"]);
  assert.equal((blocks[1] as { text: string }).text, "texto linha 2");
  assert.equal((blocks[3] as { ordered: boolean }).ordered, true);
  assert.deepEqual((blocks[6] as { lines: string[] }).lines, ["let a = 1;"]);
});

Deno.test("heading levels", () => {
  const [h] = parseBlocks("### Três ###");
  assert.deepEqual(h, { kind: "heading", level: 3, text: "Três" });
});

Deno.test("inline styles", () => {
  assert.equal(stripAnsi(renderInline("**negrito** e *itálico* e `code`")), "negrito e itálico e code");
  assert.ok(renderInline("**x**").includes("\x1b[1m"));
  assert.equal(stripAnsi(renderInline("[site](https://example.com)")), "site (https://example.com)");
});

Deno.test("snake_case words are not italicised", () => {
  assert.equal(stripAnsi(renderInline("use snake_case_name aqui")), "use snake_case_name aqui");
});

Deno.test("tables", () => {
  const out = stripAnsi(render("| Nome | Qtd |\n|---|---|\n| Maçã | 3 |\n| Uva | 10 |\n"));
  assert.ok(out.includes("│ Nome │ Qtd │"));
  assert.ok(out.includes("│ Uva  │ 10  │"));
});

Deno.test("long paragraphs wrap at the width", () => {
  const out = stripAnsi(render("palavra ".repeat(30), 40));
  for (const line of out.split("\n")) assert.ok(line.length <= 40, line);
});

Deno.test("list items keep their bullets", () => {
  const out = stripAnsi(render("- um\n- dois\n"));
  assert.ok(out.includes("• um") && out.includes("• dois"));
});

Deno.test("unterminated code fence does not hang", () => {
  const blocks = parseBlocks("```\nsem fim");
  assert.equal(blocks[0].kind, "code");
});

Deno.test("empty input", () => {
  assert.equal(render(""), "\n");
});
