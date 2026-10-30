package bank;

import java.time.Clock;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicLong;

/** Owns the accounts and performs operations that span more than one account. */
public class Bank {
    public static final double SAVINGS_MONTHLY_RATE = 0.005;
    public static final long MONTHLY_CHECKING_FEE_CENTS = 1590;

    private final Map<String, Account> accounts = new LinkedHashMap<>();
    private final AtomicLong txIds = new AtomicLong(1);
    private final AtomicLong accountSeq = new AtomicLong(1000);
    private final Clock clock;

    public Bank() { this(Clock.systemDefaultZone()); }

    public Bank(Clock clock) { this.clock = clock; }

    public Account open(String owner, Account.Kind kind, long overdraftLimitCents) {
        if (owner == null || owner.isBlank()) throw new IllegalArgumentException("owner required");
        if (overdraftLimitCents < 0) throw new IllegalArgumentException("overdraft must be >= 0");
        if (kind == Account.Kind.SAVINGS && overdraftLimitCents > 0)
            throw new IllegalArgumentException("savings accounts cannot have overdraft");
        String id = "AC" + accountSeq.getAndIncrement();
        Account acc = new Account(id, owner.trim(), kind, overdraftLimitCents, txIds::getAndIncrement, clock);
        accounts.put(id, acc);
        return acc;
    }

    public Account get(String id) {
        return Optional.ofNullable(accounts.get(id))
                .orElseThrow(() -> new IllegalArgumentException("unknown account " + id));
    }

    /** Moves money atomically: if the debit fails nothing is credited. */
    public void transfer(String fromId, String toId, long cents) {
        if (fromId.equals(toId)) throw new IllegalArgumentException("cannot transfer to the same account");
        Account from = get(fromId), to = get(toId);
        // lock in a fixed order so two opposite transfers cannot deadlock
        Account first = from.id().compareTo(to.id()) < 0 ? from : to;
        Account second = first == from ? to : from;
        synchronized (first) {
            synchronized (second) {
                from.debit(Transaction.Type.TRANSFER_OUT, cents, "transfer to " + toId);
                to.credit(Transaction.Type.TRANSFER_IN, cents, "transfer from " + fromId);
            }
        }
    }

    /** Month-end batch: interest for savings, flat fee for checking. Returns total interest paid. */
    public long closeMonth() {
        long interest = 0;
        for (Account a : accounts.values()) {
            if (a.kind() == Account.Kind.SAVINGS && a.balanceCents() > 0) {
                long amount = Money.applyRate(a.balanceCents(), SAVINGS_MONTHLY_RATE);
                if (amount > 0) {
                    a.credit(Transaction.Type.INTEREST, amount, "monthly interest");
                    interest += amount;
                }
            } else if (a.kind() == Account.Kind.CHECKING) {
                // bank-side charge: may push the account past its overdraft limit
                a.forceDebit(Transaction.Type.FEE, MONTHLY_CHECKING_FEE_CENTS, "monthly fee");
            }
        }
        return interest;
    }

    public long totalDeposits() {
        return accounts.values().stream().mapToLong(Account::balanceCents).sum();
    }

    public Optional<Account> richest() {
        return accounts.values().stream().max(Comparator.comparingLong(Account::balanceCents));
    }

    public Map<String, Account> accounts() { return Map.copyOf(accounts); }
}
