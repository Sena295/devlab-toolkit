package graph;

import java.util.List;
import java.util.Set;

public class Tests {
    private static int passed, failed;

    static void check(String name, boolean ok) {
        if (ok) passed++; else { failed++; System.out.println("FAIL: " + name); }
    }

    static void throwsOf(String name, Class<? extends Throwable> type, Runnable r) {
        try { r.run(); check(name + " (no exception)", false); }
        catch (Throwable t) { check(name + " (got " + t.getClass().getSimpleName() + ")", type.isInstance(t)); }
    }

    public static void main(String[] args) {
        traversal();
        shortestPaths();
        ordering();
        spanning();
        unionFind();
        maze();
        System.out.printf("%d passed, %d failed%n", passed, failed);
        System.exit(failed == 0 ? 0 : 1);
    }

    static Graph<String> cities() {
        Graph<String> g = new Graph<>(false);
        g.addEdge("A", "B", 4);
        g.addEdge("A", "C", 2);
        g.addEdge("C", "B", 1);
        g.addEdge("B", "D", 5);
        g.addEdge("C", "D", 8);
        g.addEdge("D", "E", 3);
        g.addVertex("Z");
        return g;
    }

    static void traversal() {
        Graph<String> g = cities();
        check("bfs", g.bfs("A").equals(List.of("A", "B", "C", "D", "E")));
        check("dfs", g.dfs("A").equals(List.of("A", "B", "C", "D", "E")));
        check("counts", g.vertices().size() == 6 && g.edgeCount() == 6);
        check("components", g.components().equals(List.of(Set.of("A", "B", "C", "D", "E"), Set.of("Z"))));
        throwsOf("unknown start", java.util.NoSuchElementException.class, () -> g.bfs("?"));
        throwsOf("negative weight", IllegalArgumentException.class, () -> g.addEdge("A", "Q", -1));
    }

    static void shortestPaths() {
        Graph<String> g = cities();
        var p = g.shortestPath("A", "E").orElseThrow();
        check("path A-E", p.vertices().equals(List.of("A", "C", "B", "D", "E")) && p.cost() == 11);
        check("trivial path", g.shortestPath("A", "A").orElseThrow().cost() == 0);
        check("unreachable", g.shortestPath("A", "Z").isEmpty());
    }

    static void ordering() {
        Graph<String> deps = new Graph<>(true);
        deps.addEdge("compile", "test", 1);
        deps.addEdge("test", "package", 1);
        deps.addEdge("compile", "lint", 1);
        deps.addEdge("lint", "package", 1);
        check("topological", deps.topologicalOrder().equals(List.of("compile", "lint", "test", "package")));
        check("acyclic", !deps.hasCycle());
        deps.addEdge("package", "compile", 1);
        check("cycle detected", deps.hasCycle());
        throwsOf("cycle throws", IllegalStateException.class, deps::topologicalOrder);
        throwsOf("undirected topo", IllegalStateException.class, () -> cities().topologicalOrder());
    }

    static void spanning() {
        var mst = cities().minimumSpanningTree();
        double total = mst.stream().mapToDouble(Graph.Edge::weight).sum();
        check("mst edges", mst.size() == 4);
        check("mst weight", total == 11);
    }

    static void unionFind() {
        UnionFind<Integer> uf = new UnionFind<>(List.of(1, 2, 3, 4, 5));
        check("initial sets", uf.sets() == 5);
        check("union", uf.union(1, 2) && uf.union(2, 3));
        check("redundant union", !uf.union(1, 3));
        check("connected", uf.connected(1, 3) && !uf.connected(1, 4));
        check("set count", uf.sets() == 3);
    }

    static void maze() {
        Grid g = new Grid(
                "S.#.....",
                ".##.###.",
                "....#...",
                ".####.#.",
                "......#E");
        var path = g.solve().orElseThrow();
        check("maze length", path.size() == 16); // 15 steps = 16 cells
        check("maze endpoints", path.get(0).equals(g.find('S')) && path.get(path.size() - 1).equals(g.find('E')));
        Grid blocked = new Grid("S#E");
        check("no route", blocked.solve().isEmpty());
        throwsOf("ragged grid", IllegalArgumentException.class, () -> new Grid("..", "."));
    }
}
