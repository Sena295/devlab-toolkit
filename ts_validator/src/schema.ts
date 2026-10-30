// Tiny schema validation library (think zod, in ~250 lines) with full type inference.

export type Issue = { path: string; message: string };

export class ValidationError extends Error {
  constructor(public issues: Issue[]) {
    super(issues.map((i) => `${i.path || "(root)"}: ${i.message}`).join("; "));
  }
}

type Ctx = { path: string; issues: Issue[] };
type Check<T> = (value: T) => string | null;

export abstract class Schema<T> {
  protected checks: Check<T>[] = [];
  abstract parseInto(input: unknown, ctx: Ctx): T | undefined;

  refine(check: (v: T) => boolean, message: string): this {
    this.checks.push((v) => (check(v) ? null : message));
    return this;
  }

  protected runChecks(value: T, ctx: Ctx): T | undefined {
    for (const c of this.checks) {
      const msg = c(value);
      if (msg) ctx.issues.push({ path: ctx.path, message: msg });
    }
    return value;
  }

  safeParse(input: unknown): { ok: true; data: T } | { ok: false; issues: Issue[] } {
    const ctx: Ctx = { path: "", issues: [] };
    const data = this.parseInto(input, ctx);
    return ctx.issues.length ? { ok: false, issues: ctx.issues } : { ok: true, data: data as T };
  }

  parse(input: unknown): T {
    const r = this.safeParse(input);
    if (!r.ok) throw new ValidationError(r.issues);
    return r.data;
  }

  optional(): Schema<T | undefined> {
    return new OptionalSchema(this);
  }

  default(fallback: T): Schema<T> {
    return new DefaultSchema(this, fallback);
  }

  transform<U>(fn: (v: T) => U): Schema<U> {
    return new TransformSchema(this, fn);
  }
}

export type Infer<S> = S extends Schema<infer T> ? T : never;

class StringSchema extends Schema<string> {
  private trimInput = false;
  parseInto(input: unknown, ctx: Ctx) {
    if (typeof input !== "string") return void ctx.issues.push({ path: ctx.path, message: "esperado string" });
    return this.runChecks(this.trimInput ? input.trim() : input, ctx);
  }
  min(n: number) { return this.refine((s) => s.length >= n, `mínimo de ${n} caracteres`); }
  max(n: number) { return this.refine((s) => s.length <= n, `máximo de ${n} caracteres`); }
  email() { return this.refine((s) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(s), "e-mail inválido"); }
  regex(re: RegExp, message = "formato inválido") { return this.refine((s) => re.test(s), message); }
  trim() { this.trimInput = true; return this; } // trims before the other checks run
}

class NumberSchema extends Schema<number> {
  parseInto(input: unknown, ctx: Ctx) {
    if (typeof input !== "number" || Number.isNaN(input)) return void ctx.issues.push({ path: ctx.path, message: "esperado número" });
    return this.runChecks(input, ctx);
  }
  int() { return this.refine(Number.isInteger, "esperado inteiro"); }
  min(n: number) { return this.refine((v) => v >= n, `mínimo ${n}`); }
  max(n: number) { return this.refine((v) => v <= n, `máximo ${n}`); }
  positive() { return this.refine((v) => v > 0, "deve ser positivo"); }
}

class BooleanSchema extends Schema<boolean> {
  parseInto(input: unknown, ctx: Ctx) {
    if (typeof input !== "boolean") return void ctx.issues.push({ path: ctx.path, message: "esperado booleano" });
    return input;
  }
}

class LiteralUnion<T extends string> extends Schema<T> {
  constructor(private options: readonly T[]) { super(); }
  parseInto(input: unknown, ctx: Ctx) {
    if (!this.options.includes(input as T)) {
      return void ctx.issues.push({ path: ctx.path, message: `esperado um de: ${this.options.join(", ")}` });
    }
    return input as T;
  }
}

class ArraySchema<T> extends Schema<T[]> {
  constructor(private item: Schema<T>) { super(); }
  parseInto(input: unknown, ctx: Ctx) {
    if (!Array.isArray(input)) return void ctx.issues.push({ path: ctx.path, message: "esperado array" });
    const out: T[] = [];
    input.forEach((v, i) => {
      const r = this.item.parseInto(v, { path: `${ctx.path}[${i}]`, issues: ctx.issues });
      out.push(r as T);
    });
    return this.runChecks(out, ctx);
  }
  min(n: number) { return this.refine((a) => a.length >= n, `mínimo de ${n} itens`); }
  max(n: number) { return this.refine((a) => a.length <= n, `máximo de ${n} itens`); }
  nonEmpty() { return this.min(1); }
}

type Shape = Record<string, Schema<any>>;
type ObjectOut<S extends Shape> = { [K in keyof S]: Infer<S[K]> };

class ObjectSchema<S extends Shape> extends Schema<ObjectOut<S>> {
  constructor(private shape: S, private strictKeys = false) { super(); }
  strict() { return new ObjectSchema(this.shape, true); }
  parseInto(input: unknown, ctx: Ctx) {
    if (typeof input !== "object" || input === null || Array.isArray(input)) {
      return void ctx.issues.push({ path: ctx.path, message: "esperado objeto" });
    }
    const src = input as Record<string, unknown>;
    const out: Record<string, unknown> = {};
    for (const [key, schema] of Object.entries(this.shape)) {
      const sub = { path: ctx.path ? `${ctx.path}.${key}` : key, issues: ctx.issues };
      if (!(key in src) && !(schema instanceof OptionalSchema) && !(schema instanceof DefaultSchema)) {
        ctx.issues.push({ path: sub.path, message: "campo obrigatório" });
        continue;
      }
      const v = schema.parseInto(src[key], sub);
      if (v !== undefined) out[key] = v;
    }
    if (this.strictKeys) {
      for (const k of Object.keys(src)) {
        if (!(k in this.shape)) ctx.issues.push({ path: ctx.path ? `${ctx.path}.${k}` : k, message: "campo não permitido" });
      }
    }
    return this.runChecks(out as ObjectOut<S>, ctx);
  }
}

class OptionalSchema<T> extends Schema<T | undefined> {
  constructor(private inner: Schema<T>) { super(); }
  parseInto(input: unknown, ctx: Ctx) {
    return input === undefined ? undefined : this.inner.parseInto(input, ctx);
  }
}

class DefaultSchema<T> extends Schema<T> {
  constructor(private inner: Schema<T>, private fallback: T) { super(); }
  parseInto(input: unknown, ctx: Ctx) {
    return input === undefined ? this.fallback : this.inner.parseInto(input, ctx);
  }
}

class TransformSchema<T, U> extends Schema<U> {
  constructor(private inner: Schema<T>, private fn: (v: T) => U) { super(); }
  parseInto(input: unknown, ctx: Ctx) {
    const before = ctx.issues.length;
    const v = this.inner.parseInto(input, ctx);
    return ctx.issues.length > before ? undefined : this.fn(v as T);
  }
}

export const s = {
  string: () => new StringSchema(),
  number: () => new NumberSchema(),
  boolean: () => new BooleanSchema(),
  oneOf: <T extends string>(...options: T[]) => new LiteralUnion(options),
  array: <T>(item: Schema<T>) => new ArraySchema(item),
  object: <S extends Shape>(shape: S) => new ObjectSchema(shape),
};
