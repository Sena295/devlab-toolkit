package bank;

import java.math.BigDecimal;
import java.math.RoundingMode;

/** Conversions between decimal strings and cents, plus pt-BR formatting. */
public final class Money {
    private Money() {}

    public static long parse(String text) {
        BigDecimal value = new BigDecimal(text.trim().replace(",", "."));
        if (value.scale() > 2) throw new IllegalArgumentException("at most 2 decimal places: " + text);
        return value.movePointRight(2).longValueExact();
    }

    public static String format(long cents) {
        long abs = Math.abs(cents);
        String units = String.format("%,d", abs / 100).replace(',', '.');
        return (cents < 0 ? "-" : "") + "R$ " + units + "," + String.format("%02d", abs % 100);
    }

    /** Applies a monthly rate (e.g. 0.01 = 1%) rounding half-up to the cent. */
    public static long applyRate(long cents, double monthlyRate) {
        return BigDecimal.valueOf(cents).multiply(BigDecimal.valueOf(monthlyRate))
                .setScale(0, RoundingMode.HALF_UP).longValueExact();
    }
}
