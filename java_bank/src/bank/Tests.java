package bank;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Supplier;

/** Dependency-free test runner: `java -cp out bank.Tests` exits with 1 if anything fails. */
public class Tests {
    private static int passed, failed;

    static void check(String name, boolean condition) {
        if (condition) passed++;
        else { failed++; System.out.println("FAIL: " + name); }
    }

    static void throwsOf(String name, Class<? extends Throwable> type, Runnable r) {
        try { r.run(); check(name + " (no exception)", false); }
        catch (Throwable t) { check(name + " (got " + t.getClass().getSimpleName() + ")", type.isInstance(t)); }
    }

    static Bank newBank() {
        return new Bank(Clock.fixed(Instant.parse("2025-03-10T12:00:00Z"), ZoneOffset.UTC));
    }

    public static void main(String[] args) throws Exception {
        money();
        accounts();
        transfers();
        monthClose();
        concurrency();
        System.out.printf("%d passed, %d failed%n", passed, failed);
        System.exit(failed == 0 ? 0 : 1);
    }

    static void money() {
        check("parse comma", Money.parse("10,50") == 1050);
        check("parse int", Money.parse("7") == 700);
        check("format", Money.format(123456789).equals("R$ 1.234.567,89"));
        check("format negative", Money.format(-5).equals("-R$ 0,05"));
        throwsOf("3 decimals", IllegalArgumentException.class, () -> Money.parse("1,234"));
        check("rate half-up", Money.applyRate(1001, 0.005) == 5);
    }

    static void accounts() {
        Bank b = newBank();
        Account a = b.open("Ana", Account.Kind.CHECKING, 10_000);
        a.deposit(5_000, "x");
        check("balance", a.balanceCents() == 5_000);
        a.withdraw(12_000, "overdraft use");
        check("overdraft allowed", a.balanceCents() == -7_000);
        throwsOf("over limit", InsufficientFundsException.class, () -> a.withdraw(4_000, "too much"));
        check("failed withdraw changes nothing", a.balanceCents() == -7_000 && a.history().size() == 2);
        check("balance after recorded", a.history().get(1).balanceAfterCents() == -7_000);
        throwsOf("savings overdraft", IllegalArgumentException.class, () -> b.open("Bia", Account.Kind.SAVINGS, 1));
        throwsOf("blank owner", IllegalArgumentException.class, () -> b.open(" ", Account.Kind.CHECKING, 0));
        throwsOf("unknown id", IllegalArgumentException.class, () -> b.get("nope"));
        throwsOf("zero deposit", IllegalArgumentException.class, () -> a.deposit(0, "x"));
        throwsOf("history read-only", UnsupportedOperationException.class, () -> a.history().clear());
    }

    static void transfers() {
        Bank b = newBank();
        Account a = b.open("Ana", Account.Kind.CHECKING, 0), c = b.open("Caio", Account.Kind.CHECKING, 0);
        a.deposit(10_000, "seed");
        b.transfer(a.id(), c.id(), 4_000);
        check("debited", a.balanceCents() == 6_000);
        check("credited", c.balanceCents() == 4_000);
        throwsOf("insufficient", InsufficientFundsException.class, () -> b.transfer(a.id(), c.id(), 50_000));
        check("atomic: nothing moved", a.balanceCents() == 6_000 && c.balanceCents() == 4_000);
        throwsOf("self transfer", IllegalArgumentException.class, () -> b.transfer(a.id(), a.id(), 1));
        check("total preserved", b.totalDeposits() == 10_000);
    }

    static void monthClose() {
        Bank b = newBank();
        Account s = b.open("Bia", Account.Kind.SAVINGS, 0), c = b.open("Caio", Account.Kind.CHECKING, 0);
        s.deposit(100_000, "seed");
        c.deposit(20_000, "seed");
        long interest = b.closeMonth();
        check("interest 0.5%", interest == 500 && s.balanceCents() == 100_500);
        check("fee charged", c.balanceCents() == 20_000 - Bank.MONTHLY_CHECKING_FEE_CENTS);
        check("totals by type", Statement.totalsByType(s).get(Transaction.Type.INTEREST) == 500);
        check("statement text", Statement.render(s).contains("Saldo atual: R$ 1.005,00"));
        check("richest", b.richest().orElseThrow() == s);
    }

    static void concurrency() throws Exception {
        Bank b = newBank();
        Account a = b.open("A", Account.Kind.CHECKING, 0), c = b.open("B", Account.Kind.CHECKING, 0);
        a.deposit(1_000_000, "seed");
        c.deposit(1_000_000, "seed");
        List<Thread> threads = new ArrayList<>();
        for (int i = 0; i < 8; i++) {
            final boolean forward = i % 2 == 0;
            Thread t = new Thread(() -> {
                for (int k = 0; k < 500; k++) {
                    if (forward) b.transfer(a.id(), c.id(), 10); else b.transfer(c.id(), a.id(), 10);
                }
            });
            threads.add(t);
            t.start();
        }
        for (Thread t : threads) t.join(10_000);
        check("no deadlock, money conserved", threads.stream().noneMatch(Thread::isAlive) && b.totalDeposits() == 2_000_000);
        check("balances equal after symmetric transfers", a.balanceCents() == 1_000_000);
    }
}
