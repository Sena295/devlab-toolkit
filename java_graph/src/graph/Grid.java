package graph;

import java.util.*;

/** Path finding on a text maze: '#' wall, '.' free, 'S' start, 'E' end. A* with Manhattan distance. */
public final class Grid {
    public record Point(int row, int col) {}

    private final char[][] cells;

    public Grid(String... rows) {
        cells = Arrays.stream(rows).map(String::toCharArray).toArray(char[][]::new);
        if (cells.length == 0 || Arrays.stream(cells).anyMatch(r -> r.length != cells[0].length))
            throw new IllegalArgumentException("grid must be a non-empty rectangle");
    }

    public Point find(char c) {
        for (int r = 0; r < cells.length; r++)
            for (int k = 0; k < cells[r].length; k++) if (cells[r][k] == c) return new Point(r, k);
        throw new NoSuchElementException("no '" + c + "' in grid");
    }

    private boolean open(int r, int c) {
        return r >= 0 && c >= 0 && r < cells.length && c < cells[0].length && cells[r][c] != '#';
    }

    public Optional<List<Point>> solve() {
        Point start = find('S'), end = find('E');
        record Node(Point p, int g, int f) {}
        PriorityQueue<Node> open = new PriorityQueue<>(Comparator.comparingInt(Node::f));
        Map<Point, Integer> best = new HashMap<>(Map.of(start, 0));
        Map<Point, Point> cameFrom = new HashMap<>();
        open.add(new Node(start, 0, h(start, end)));
        int[][] dirs = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
        while (!open.isEmpty()) {
            Node n = open.poll();
            if (n.p().equals(end)) {
                LinkedList<Point> path = new LinkedList<>();
                for (Point p = end; p != null; p = cameFrom.get(p)) path.addFirst(p);
                return Optional.of(path);
            }
            if (n.g() > best.getOrDefault(n.p(), Integer.MAX_VALUE)) continue;
            for (int[] d : dirs) {
                int r = n.p().row() + d[0], c = n.p().col() + d[1];
                if (!open(r, c)) continue;
                Point next = new Point(r, c);
                int g = n.g() + 1;
                if (g < best.getOrDefault(next, Integer.MAX_VALUE)) {
                    best.put(next, g);
                    cameFrom.put(next, n.p());
                    open.add(new Node(next, g, g + h(next, end)));
                }
            }
        }
        return Optional.empty();
    }

    private static int h(Point a, Point b) { return Math.abs(a.row() - b.row()) + Math.abs(a.col() - b.col()); }

    public String render(List<Point> path) {
        char[][] copy = Arrays.stream(cells).map(char[]::clone).toArray(char[][]::new);
        for (Point p : path) if (copy[p.row()][p.col()] == '.') copy[p.row()][p.col()] = '*';
        StringBuilder sb = new StringBuilder();
        for (char[] row : copy) sb.append(new String(row)).append('\n');
        return sb.toString();
    }
}
