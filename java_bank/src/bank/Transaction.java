package bank;

import java.time.LocalDateTime;

/** Immutable ledger entry. Amounts are stored in cents to avoid floating point errors. */
public record Transaction(long id, Type type, long amountCents, long balanceAfterCents,
                          LocalDateTime at, String description) {

    public enum Type { DEPOSIT, WITHDRAWAL, TRANSFER_IN, TRANSFER_OUT, INTEREST, FEE }

    public Transaction {
        if (amountCents <= 0) throw new IllegalArgumentException("amount must be positive");
    }

    /** Signed effect on the balance. */
    public long delta() {
        return switch (type) {
            case DEPOSIT, TRANSFER_IN, INTEREST -> amountCents;
            case WITHDRAWAL, TRANSFER_OUT, FEE -> -amountCents;
        };
    }
}
