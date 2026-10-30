package graph;

public class Main {
    public static void main(String[] args) {
        Grid maze = new Grid(
                "S.#.....",
                ".##.###.",
                "....#...",
                ".####.#.",
                "......#E");
        System.out.println("Labirinto resolvido com A*:");
        maze.solve().ifPresentOrElse(
                p -> System.out.print(maze.render(p) + "Passos: " + (p.size() - 1) + "\n"),
                () -> System.out.println("Sem caminho."));

        Graph<String> deps = new Graph<>(true);
        deps.addEdge("compile", "test", 1);
        deps.addEdge("compile", "lint", 1);
        deps.addEdge("test", "package", 1);
        deps.addEdge("lint", "package", 1);
        System.out.println("\nOrdem de build: " + deps.topologicalOrder());
    }
}
