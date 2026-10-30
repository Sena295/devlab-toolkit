package bank;

import java.time.format.DateTimeFormatter;
import java.util.EnumMap;
import java.util.Map;

/** Renders an account statement as plain text. */
public final class Statement {
    private static final DateTimeFormatter DATE = DateTimeFormatter.ofPattern("dd/MM HH:mm");

    private Statement() {}

    public static String render(Account account) {
        StringBuilder sb = new StringBuilder();
        sb.append(String.format("Extrato %s - %s (%s)%n", account.id(), account.owner(), account.kind()));
        sb.append("-".repeat(64)).append('\n');
        for (Transaction t : account.history()) {
            sb.append(String.format("%-11s %-13s %14s %14s  %s%n",
                    t.at().format(DATE), t.type(), Money.format(t.delta()), Money.format(t.balanceAfterCents()),
                    t.description() == null ? "" : t.description()));
        }
        sb.append("-".repeat(64)).append('\n');
        sb.append(String.format("Saldo atual: %s%n", Money.format(account.balanceCents())));
        return sb.toString();
    }

    public static Map<Transaction.Type, Long> totalsByType(Account account) {
        Map<Transaction.Type, Long> totals = new EnumMap<>(Transaction.Type.class);
        for (Transaction t : account.history()) totals.merge(t.type(), t.amountCents(), Long::sum);
        return totals;
    }
}
