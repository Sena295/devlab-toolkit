// Job scheduler with an injectable clock: jobs with cron expressions, retries with backoff, run history.
import { nextRun } from "./cron.ts";

export type JobFn = () => void | Promise<void>;
export type RunRecord = { job: string; at: Date; ok: boolean; attempts: number; error?: string };

type Job = { name: string; cron: string; fn: JobFn; next: Date; retries: number };

export class Scheduler {
  private jobs = new Map<string, Job>();
  readonly history: RunRecord[] = [];

  constructor(private now: () => Date = () => new Date(), private backoffMs = (attempt: number) => 2 ** attempt * 100) {}

  add(name: string, cron: string, fn: JobFn, opts: { retries?: number } = {}): void {
    if (this.jobs.has(name)) throw new Error(`job '${name}' já existe`);
    this.jobs.set(name, { name, cron, fn, next: nextRun(cron, this.now()), retries: opts.retries ?? 0 });
  }

  remove(name: string): boolean {
    return this.jobs.delete(name);
  }

  upcoming(): { name: string; next: Date }[] {
    return [...this.jobs.values()].map(({ name, next }) => ({ name, next })).sort((a, b) => a.next.getTime() - b.next.getTime());
  }

  /** Runs every job whose time has come. Call it from a timer (or manually in tests). */
  async tick(sleep: (ms: number) => Promise<void> = (ms) => new Promise((r) => setTimeout(r, ms))): Promise<RunRecord[]> {
    const now = this.now();
    const ran: RunRecord[] = [];
    for (const job of this.jobs.values()) {
      if (job.next > now) continue;
      const record = await this.execute(job, now, sleep);
      job.next = nextRun(job.cron, now); // schedule from now so a long outage does not cause a burst of catch-up runs
      this.history.push(record);
      ran.push(record);
    }
    return ran;
  }

  private async execute(job: Job, at: Date, sleep: (ms: number) => Promise<void>): Promise<RunRecord> {
    let attempts = 0;
    let lastError: string | undefined;
    while (attempts <= job.retries) {
      attempts++;
      try {
        await job.fn();
        return { job: job.name, at, ok: true, attempts };
      } catch (e) {
        lastError = e instanceof Error ? e.message : String(e);
        if (attempts <= job.retries) await sleep(this.backoffMs(attempts));
      }
    }
    return { job: job.name, at, ok: false, attempts, error: lastError };
  }
}
