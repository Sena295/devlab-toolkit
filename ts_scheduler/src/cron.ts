// Cron expression parser + "next run" calculator (5 fields: minute hour day-of-month month day-of-week).

export type CronFields = { minute: Set<number>; hour: Set<number>; dom: Set<number>; month: Set<number>; dow: Set<number>; domStar: boolean; dowStar: boolean };

const RANGES = {
  minute: [0, 59], hour: [0, 23], dom: [1, 31], month: [1, 12], dow: [0, 6],
} as const;
const NAMES: Record<string, Record<string, number>> = {
  month: { jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6, jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12 },
  dow: { sun: 0, mon: 1, tue: 2, wed: 3, thu: 4, fri: 5, sat: 6 },
};
const ALIASES: Record<string, string> = {
  "@hourly": "0 * * * *", "@daily": "0 0 * * *", "@weekly": "0 0 * * 0", "@monthly": "0 0 1 * *", "@yearly": "0 0 1 1 *",
};

export class CronError extends Error {}

function value(token: string, field: keyof typeof RANGES): number {
  const named = NAMES[field]?.[token.toLowerCase()];
  const n = named ?? (/^\d+$/.test(token) ? Number(token) : NaN);
  if (Number.isNaN(n)) throw new CronError(`valor inválido '${token}' em ${field}`);
  const [lo, hi] = RANGES[field];
  const v = field === "dow" && n === 7 ? 0 : n; // 7 is also Sunday
  if (v < lo || v > hi) throw new CronError(`${field} fora do intervalo ${lo}-${hi}: ${token}`);
  return v;
}

function parseField(text: string, field: keyof typeof RANGES): Set<number> {
  const [lo, hi] = RANGES[field];
  const out = new Set<number>();
  for (const part of text.split(",")) {
    const [rangePart, stepPart] = part.split("/");
    const step = stepPart === undefined ? 1 : Number(stepPart);
    if (!Number.isInteger(step) || step < 1) throw new CronError(`passo inválido '${stepPart}' em ${field}`);
    let from: number, to: number;
    if (rangePart === "*") [from, to] = [lo, hi];
    else if (rangePart.includes("-")) {
      const [a, b] = rangePart.split("-");
      [from, to] = [value(a, field), value(b, field)];
      if (from > to) throw new CronError(`intervalo invertido '${rangePart}' em ${field}`);
    } else {
      from = value(rangePart, field);
      to = stepPart === undefined ? from : hi;
    }
    for (let v = from; v <= to; v += step) out.add(v);
  }
  return out;
}

export function parseCron(expr: string): CronFields {
  const resolved = ALIASES[expr.trim().toLowerCase()] ?? expr;
  const parts = resolved.trim().split(/\s+/);
  if (parts.length !== 5) throw new CronError(`esperado 5 campos, recebido ${parts.length}`);
  const [minute, hour, dom, month, dow] = parts;
  return {
    minute: parseField(minute, "minute"), hour: parseField(hour, "hour"), dom: parseField(dom, "dom"),
    month: parseField(month, "month"), dow: parseField(dow, "dow"), domStar: dom === "*", dowStar: dow === "*",
  };
}

function dayMatches(f: CronFields, d: Date): boolean {
  const domOk = f.dom.has(d.getDate()), dowOk = f.dow.has(d.getDay());
  // classic cron rule: if both day fields are restricted, either one may match
  if (!f.domStar && !f.dowStar) return domOk || dowOk;
  return domOk && dowOk;
}

/** Next instant strictly after `after` that matches the expression (minute precision). */
export function nextRun(expr: string | CronFields, after: Date): Date {
  const f = typeof expr === "string" ? parseCron(expr) : expr;
  const d = new Date(after.getTime());
  d.setSeconds(0, 0);
  d.setMinutes(d.getMinutes() + 1);
  const limit = after.getFullYear() + 5;
  while (d.getFullYear() <= limit) {
    if (!f.month.has(d.getMonth() + 1)) { d.setMonth(d.getMonth() + 1, 1); d.setHours(0, 0, 0, 0); continue; }
    if (!dayMatches(f, d)) { d.setDate(d.getDate() + 1); d.setHours(0, 0, 0, 0); continue; }
    if (!f.hour.has(d.getHours())) { d.setHours(d.getHours() + 1, 0, 0, 0); continue; }
    if (!f.minute.has(d.getMinutes())) { d.setMinutes(d.getMinutes() + 1, 0, 0); continue; }
    return d;
  }
  throw new CronError("nenhuma execução nos próximos 5 anos");
}

export function nextRuns(expr: string, after: Date, count: number): Date[] {
  const out: Date[] = [];
  let cursor = after;
  for (let i = 0; i < count; i++) { cursor = nextRun(expr, cursor); out.push(cursor); }
  return out;
}
