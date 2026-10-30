package graph;

import java.util.Collection;
import java.util.HashMap;
import java.util.Map;

/** Disjoint-set with path compression and union by rank. */
public class UnionFind<T> {
    private final Map<T, T> parent = new HashMap<>();
    private final Map<T, Integer> rank = new HashMap<>();
    private int sets;

    public UnionFind(Collection<T> items) {
        for (T t : items) { parent.put(t, t); rank.put(t, 0); }
        sets = parent.size();
    }

    public T find(T x) {
        T p = parent.get(x);
        if (p == null) throw new IllegalArgumentException("unknown element " + x);
        if (!p.equals(x)) { p = find(p); parent.put(x, p); }
        return p;
    }

    /** @return true if the two elements were in different sets. */
    public boolean union(T a, T b) {
        T ra = find(a), rb = find(b);
        if (ra.equals(rb)) return false;
        int ka = rank.get(ra), kb = rank.get(rb);
        if (ka < kb) parent.put(ra, rb);
        else if (ka > kb) parent.put(rb, ra);
        else { parent.put(rb, ra); rank.put(ra, ka + 1); }
        sets--;
        return true;
    }

    public boolean connected(T a, T b) { return find(a).equals(find(b)); }

    public int sets() { return sets; }
}
