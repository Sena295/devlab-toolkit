import assert from "node:assert/strict";
import { Infer, s, ValidationError } from "./schema.ts";

const User = s.object({
  name: s.string().trim().min(2).max(40),
  email: s.string().email(),
  age: s.number().int().min(0).max(130).optional(),
  role: s.oneOf("user", "admin").default("user"),
  tags: s.array(s.string().min(1)).max(3),
});
type User = Infer<typeof User>;

Deno.test("valid input is parsed, trimmed and defaulted", () => {
  const u: User = User.parse({ name: "  Ana ", email: "ana@example.com", tags: ["a"] });
  assert.deepEqual(u, { name: "Ana", email: "ana@example.com", role: "user", tags: ["a"] });
});

Deno.test("collects every issue with its path", () => {
  const r = User.safeParse({ name: "A", email: "x", age: 1.5, tags: ["ok", ""], role: "root" });
  assert.equal(r.ok, false);
  if (r.ok) return;
  const byPath = Object.fromEntries(r.issues.map((i) => [i.path, i.message]));
  assert.equal(byPath["name"], "mínimo de 2 caracteres");
  assert.equal(byPath["email"], "e-mail inválido");
  assert.equal(byPath["age"], "esperado inteiro");
  assert.equal(byPath["role"], "esperado um de: user, admin");
  assert.equal(byPath["tags[1]"], "mínimo de 1 caracteres");
});

Deno.test("missing required fields", () => {
  const r = User.safeParse({});
  assert.ok(!r.ok && r.issues.some((i) => i.path === "name" && i.message === "campo obrigatório"));
});

Deno.test("wrong root type", () => {
  for (const bad of [null, 1, "x", []]) assert.equal(User.safeParse(bad).ok, false);
});

Deno.test("parse throws ValidationError", () => {
  assert.throws(() => User.parse({}), ValidationError);
});

Deno.test("strict objects reject unknown keys", () => {
  const strict = s.object({ a: s.number() }).strict();
  assert.equal(strict.safeParse({ a: 1 }).ok, true);
  assert.equal(strict.safeParse({ a: 1, b: 2 }).ok, false);
});

Deno.test("array limits and nesting", () => {
  const Order = s.object({ items: s.array(s.object({ sku: s.string(), qty: s.number().positive() })).nonEmpty() });
  assert.equal(Order.safeParse({ items: [] }).ok, false);
  const bad = Order.safeParse({ items: [{ sku: "A", qty: 0 }] });
  assert.ok(!bad.ok && bad.issues[0].path === "items[0].qty");
});

Deno.test("refine adds custom rules", () => {
  const Pwd = s.string().refine((v) => /\d/.test(v), "precisa de um número");
  assert.equal(Pwd.safeParse("abc").ok, false);
  assert.equal(Pwd.safeParse("abc1").ok, true);
});

Deno.test("transform converts the output type", () => {
  const Len = s.string().transform((v) => v.length);
  assert.equal(Len.parse("quatro"), 6);
});
