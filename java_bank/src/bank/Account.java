package bank;

import java.time.Clock;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.function.LongSupplier;

/** A bank account with an append-only transaction history. */
public class Account {
    public enum Kind { CHECKING, SAVINGS }

    private final String id;
    private final String owner;
    private final Kind kind;
    private final long overdraftLimitCents;
    private final List<Transaction> history = new ArrayList<>();
    private final LongSupplier ids;
    private final Clock clock;
    private long balanceCents;

    Account(String id, String owner, Kind kind, long overdraftLimitCents, LongSupplier ids, Clock clock) {
        this.id = id;
        this.owner = owner;
        this.kind = kind;
        this.overdraftLimitCents = overdraftLimitCents;
        this.ids = ids;
        this.clock = clock;
    }

    public String id() { return id; }
    public String owner() { return owner; }
    public Kind kind() { return kind; }
    public long balanceCents() { return balanceCents; }
    public List<Transaction> history() { return Collections.unmodifiableList(history); }

    public synchronized void deposit(long cents, String description) {
        record(Transaction.Type.DEPOSIT, cents, description);
    }

    public synchronized void withdraw(long cents, String description) {
        requireFunds(cents);
        record(Transaction.Type.WITHDRAWAL, cents, description);
    }

    synchronized void debit(Transaction.Type type, long cents, String description) {
        requireFunds(cents);
        record(type, cents, description);
    }

    synchronized void forceDebit(Transaction.Type type, long cents, String description) {
        record(type, cents, description);
    }

    synchronized void credit(Transaction.Type type, long cents, String description) {
        record(type, cents, description);
    }

    private void requireFunds(long cents) {
        long available = balanceCents + overdraftLimitCents;
        if (cents > available) throw new InsufficientFundsException(id, cents - available);
    }

    private void record(Transaction.Type type, long cents, String description) {
        Transaction probe = new Transaction(ids.getAsLong(), type, cents, 0, LocalDateTime.now(clock), description);
        balanceCents += probe.delta();
        history.add(new Transaction(probe.id(), type, cents, balanceCents, probe.at(), description));
    }

    /** Transactions between two instants (inclusive start, exclusive end). */
    public List<Transaction> between(LocalDateTime from, LocalDateTime to) {
        return history.stream().filter(t -> !t.at().isBefore(from) && t.at().isBefore(to)).toList();
    }
}
