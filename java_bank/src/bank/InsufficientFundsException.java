package bank;

public class InsufficientFundsException extends RuntimeException {
    private final long missingCents;

    public InsufficientFundsException(String accountId, long missingCents) {
        super("insufficient funds in " + accountId + ": missing " + Money.format(missingCents));
        this.missingCents = missingCents;
    }

    public long missingCents() { return missingCents; }
}
