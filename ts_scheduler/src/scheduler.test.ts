import assert from "node:assert/strict";
import { CronError, nextRun, nextRuns, parseCron } from "./cron.ts";
import { Scheduler } from "./scheduler.ts";

const at = (s: string) => new Date(s); // local time, no zone suffix

Deno.test("parseCron expands lists, ranges and steps", () => {
  const f = parseCron("*/15 9-11 * jan,mar mon-fri");
  assert.deepEqual([...f.minute], [0, 15, 30, 45]);
  assert.deepEqual([...f.hour], [9, 10, 11]);
  assert.deepEqual([...f.month], [1, 3]);
  assert.deepEqual([...f.dow], [1, 2, 3, 4, 5]);
});

Deno.test("parseCron rejects bad input", () => {
  for (const bad of ["* * * *", "61 * * * *", "* 24 * * *", "5-1 * * * *", "*/0 * * * *", "a * * * *", "* * 0 * *"]) {
    assert.throws(() => parseCron(bad), CronError, bad);
  }
});

Deno.test("aliases and sunday as 7", () => {
  assert.deepEqual([...parseCron("@daily").hour], [0]);
  assert.deepEqual([...parseCron("0 0 * * 7").dow], [0]);
});

Deno.test("nextRun is strictly after the reference", () => {
  const n = nextRun("*/5 * * * *", at("2025-03-10T10:05:00"));
  assert.equal(n.getTime(), at("2025-03-10T10:10:00").getTime());
});

Deno.test("nextRun rolls over hour, day, month and year", () => {
  assert.equal(nextRun("0 0 * * *", at("2025-03-10T23:30:00")).getTime(), at("2025-03-11T00:00:00").getTime());
  assert.equal(nextRun("30 8 1 * *", at("2025-12-15T00:00:00")).getTime(), at("2026-01-01T08:30:00").getTime());
});

Deno.test("weekday restriction", () => {
  // 2025-03-10 is a Monday; the next Friday 09:00 is the 14th
  assert.equal(nextRun("0 9 * * fri", at("2025-03-10T12:00:00")).getTime(), at("2025-03-14T09:00:00").getTime());
});

Deno.test("day-of-month OR day-of-week when both are restricted", () => {
  // the 13th OR any Friday
  const runs = nextRuns("0 0 13 * fri", at("2025-06-01T00:00:00"), 3).map((d) => d.getDate());
  assert.deepEqual(runs, [6, 13, 20]);
});

Deno.test("feb 29 only on leap years", () => {
  assert.equal(nextRun("0 0 29 2 *", at("2025-01-01T00:00:00")).getFullYear(), 2028);
});

Deno.test("scheduler runs due jobs and reschedules", async () => {
  let clock = at("2025-03-10T10:00:00");
  const s = new Scheduler(() => clock);
  let count = 0;
  s.add("tick", "* * * * *", () => { count++; });
  assert.equal((await s.tick()).length, 0); // nothing due yet
  clock = at("2025-03-10T10:01:00");
  assert.equal((await s.tick()).length, 1);
  assert.equal((await s.tick()).length, 0); // already ran this minute
  assert.equal(count, 1);
  assert.equal(s.history[0].ok, true);
});

Deno.test("retries with backoff then reports failure", async () => {
  let clock = at("2025-03-10T10:00:00");
  const s = new Scheduler(() => clock, () => 1);
  let calls = 0;
  s.add("flaky", "* * * * *", () => { calls++; if (calls < 3) throw new Error("falhou"); }, { retries: 2 });
  s.add("broken", "* * * * *", () => { throw new Error("sempre falha"); }, { retries: 1 });
  clock = at("2025-03-10T10:01:00");
  const noSleep = () => Promise.resolve();
  const ran = await s.tick(noSleep);
  const byJob = Object.fromEntries(ran.map((r) => [r.job, r]));
  assert.deepEqual([byJob.flaky.ok, byJob.flaky.attempts], [true, 3]);
  assert.deepEqual([byJob.broken.ok, byJob.broken.attempts, byJob.broken.error], [false, 2, "sempre falha"]);
});

Deno.test("duplicate and removal", () => {
  const s = new Scheduler(() => at("2025-03-10T10:00:00"));
  s.add("a", "@hourly", () => {});
  assert.throws(() => s.add("a", "@hourly", () => {}));
  assert.equal(s.remove("a"), true);
  assert.equal(s.remove("a"), false);
});
