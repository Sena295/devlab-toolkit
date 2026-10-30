package graph;

import java.util.*;

/** Weighted directed graph with the classic algorithms: BFS/DFS, Dijkstra, topological sort, cycles, MST. */
public class Graph<V extends Comparable<V>> {
    public record Edge<V>(V from, V to, double weight) {}

    private final Map<V, List<Edge<V>>> adj = new TreeMap<>();
    private final boolean directed;

    public Graph(boolean directed) { this.directed = directed; }

    public void addVertex(V v) { adj.computeIfAbsent(v, k -> new ArrayList<>()); }

    public void addEdge(V from, V to, double weight) {
        if (weight < 0) throw new IllegalArgumentException("negative weights are not supported");
        addVertex(from);
        addVertex(to);
        adj.get(from).add(new Edge<>(from, to, weight));
        if (!directed) adj.get(to).add(new Edge<>(to, from, weight));
    }

    public Set<V> vertices() { return Collections.unmodifiableSet(adj.keySet()); }

    public List<Edge<V>> edgesFrom(V v) { return Collections.unmodifiableList(adj.getOrDefault(v, List.of())); }

    public int edgeCount() {
        int n = adj.values().stream().mapToInt(List::size).sum();
        return directed ? n : n / 2;
    }

    public List<V> bfs(V start) {
        requireVertex(start);
        List<V> order = new ArrayList<>();
        Set<V> seen = new HashSet<>(Set.of(start));
        Deque<V> queue = new ArrayDeque<>(List.of(start));
        while (!queue.isEmpty()) {
            V v = queue.poll();
            order.add(v);
            for (Edge<V> e : adj.get(v)) if (seen.add(e.to())) queue.add(e.to());
        }
        return order;
    }

    public List<V> dfs(V start) {
        requireVertex(start);
        List<V> order = new ArrayList<>();
        dfs(start, new HashSet<>(), order);
        return order;
    }

    private void dfs(V v, Set<V> seen, List<V> order) {
        if (!seen.add(v)) return;
        order.add(v);
        for (Edge<V> e : adj.get(v)) dfs(e.to(), seen, order);
    }

    /** Shortest path by total weight, or empty if unreachable. */
    public Optional<Path<V>> shortestPath(V from, V to) {
        requireVertex(from);
        requireVertex(to);
        Map<V, Double> dist = new HashMap<>();
        Map<V, V> prev = new HashMap<>();
        PriorityQueue<Map.Entry<V, Double>> pq = new PriorityQueue<>(Map.Entry.comparingByValue());
        dist.put(from, 0.0);
        pq.add(Map.entry(from, 0.0));
        while (!pq.isEmpty()) {
            var cur = pq.poll();
            V v = cur.getKey();
            if (cur.getValue() > dist.getOrDefault(v, Double.POSITIVE_INFINITY)) continue; // stale entry
            if (v.equals(to)) break;
            for (Edge<V> e : adj.get(v)) {
                double nd = cur.getValue() + e.weight();
                if (nd < dist.getOrDefault(e.to(), Double.POSITIVE_INFINITY)) {
                    dist.put(e.to(), nd);
                    prev.put(e.to(), v);
                    pq.add(Map.entry(e.to(), nd));
                }
            }
        }
        if (!dist.containsKey(to)) return Optional.empty();
        LinkedList<V> path = new LinkedList<>();
        for (V at = to; at != null; at = prev.get(at)) path.addFirst(at);
        return Optional.of(new Path<>(path, dist.get(to)));
    }

    public record Path<V>(List<V> vertices, double cost) {}

    /** Kahn's algorithm. Throws if the graph has a cycle. */
    public List<V> topologicalOrder() {
        if (!directed) throw new IllegalStateException("topological order needs a directed graph");
        Map<V, Integer> indegree = new TreeMap<>();
        adj.keySet().forEach(v -> indegree.put(v, 0));
        adj.values().forEach(es -> es.forEach(e -> indegree.merge(e.to(), 1, Integer::sum)));
        PriorityQueue<V> ready = new PriorityQueue<>();
        indegree.forEach((v, d) -> { if (d == 0) ready.add(v); });
        List<V> order = new ArrayList<>();
        while (!ready.isEmpty()) {
            V v = ready.poll();
            order.add(v);
            for (Edge<V> e : adj.get(v)) if (indegree.merge(e.to(), -1, Integer::sum) == 0) ready.add(e.to());
        }
        if (order.size() != adj.size()) throw new IllegalStateException("graph has a cycle");
        return order;
    }

    public boolean hasCycle() {
        try { topologicalOrder(); return false; } catch (IllegalStateException e) { return directed; }
    }

    /** Connected components of an undirected graph. */
    public List<Set<V>> components() {
        List<Set<V>> out = new ArrayList<>();
        Set<V> seen = new HashSet<>();
        for (V v : adj.keySet()) {
            if (seen.contains(v)) continue;
            Set<V> comp = new TreeSet<>(bfs(v));
            seen.addAll(comp);
            out.add(comp);
        }
        return out;
    }

    /** Kruskal minimum spanning forest (undirected graphs). */
    public List<Edge<V>> minimumSpanningTree() {
        if (directed) throw new IllegalStateException("MST needs an undirected graph");
        List<Edge<V>> edges = new ArrayList<>();
        for (var es : adj.values()) for (Edge<V> e : es) if (e.from().compareTo(e.to()) < 0) edges.add(e);
        edges.sort(Comparator.comparingDouble(Edge::weight));
        UnionFind<V> uf = new UnionFind<>(adj.keySet());
        List<Edge<V>> tree = new ArrayList<>();
        for (Edge<V> e : edges) if (uf.union(e.from(), e.to())) tree.add(e);
        return tree;
    }

    private void requireVertex(V v) {
        if (!adj.containsKey(v)) throw new NoSuchElementException("unknown vertex " + v);
    }
}
