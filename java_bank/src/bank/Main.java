package bank;

/** Console demo with fictitious customers. */
public class Main {
    public static void main(String[] args) {
        Bank bank = new Bank();
        Account ana = bank.open("Ana Souza", Account.Kind.CHECKING, Money.parse("500"));
        Account bia = bank.open("Bia Lima", Account.Kind.SAVINGS, 0);

        ana.deposit(Money.parse("2500,00"), "salário fictício");
        bank.transfer(ana.id(), bia.id(), Money.parse("1000"));
        ana.withdraw(Money.parse("300,50"), "mercado");
        try {
            ana.withdraw(Money.parse("5000"), "compra grande");
        } catch (InsufficientFundsException e) {
            System.out.println("Recusado: " + e.getMessage());
        }
        long interest = bank.closeMonth();

        System.out.print(Statement.render(ana));
        System.out.println();
        System.out.print(Statement.render(bia));
        System.out.println("\nJuros pagos no mês: " + Money.format(interest));
        System.out.println("Total em depósitos: " + Money.format(bank.totalDeposits()));
    }
}
