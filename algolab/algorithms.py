"""Sorting, searching and dynamic-programming classics."""
from __future__ import annotations

import random
from typing import Callable, Sequence


# --- sorting ---------------------------------------------------------------
def merge_sort(a: Sequence[int]) -> list[int]:
    if len(a) <= 1:
        return list(a)
    mid = len(a) // 2
    left, right = merge_sort(a[:mid]), merge_sort(a[mid:])
    out, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:  # <= keeps the sort stable
            out.append(left[i]); i += 1
        else:
            out.append(right[j]); j += 1
    return out + left[i:] + right[j:]


def quick_sort(a: Sequence[int], rng: random.Random | None = None) -> list[int]:
    rng = rng or random.Random(0)
    arr = list(a)

    def sort(lo: int, hi: int) -> None:
        while lo < hi:
            p = arr[rng.randint(lo, hi)]
            i, j = lo, hi
            while i <= j:  # Hoare partition
                while arr[i] < p: i += 1
                while arr[j] > p: j -= 1
                if i <= j:
                    arr[i], arr[j] = arr[j], arr[i]
                    i += 1; j -= 1
            if j - lo < hi - i:  # recurse into the smaller side, loop on the larger: O(log n) stack
                sort(lo, j); lo = i
            else:
                sort(i, hi); hi = j

    sort(0, len(arr) - 1)
    return arr


def heap_sort(a: Sequence[int]) -> list[int]:
    from .structures import MinHeap
    h = MinHeap(a)
    return [h.pop() for _ in range(len(h))]


def counting_sort(a: Sequence[int]) -> list[int]:
    if not a:
        return []
    lo, hi = min(a), max(a)
    counts = [0] * (hi - lo + 1)
    for x in a:
        counts[x - lo] += 1
    return [lo + i for i, c in enumerate(counts) for _ in range(c)]


# --- searching ---------------------------------------------------------------
def binary_search(a: Sequence[int], target: int) -> int:
    """Index of target in sorted a, or -1."""
    lo, hi = 0, len(a) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if a[mid] == target:
            return mid
        lo, hi = (mid + 1, hi) if a[mid] < target else (lo, mid - 1)
    return -1


def lower_bound(a: Sequence[int], target: int) -> int:
    """First index with a[i] >= target (insertion point)."""
    lo, hi = 0, len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo


def bisect_answer(ok: Callable[[int], bool], lo: int, hi: int) -> int:
    """Smallest x in [lo, hi] with ok(x) True, assuming ok is monotonic. Returns hi + 1 if none."""
    while lo <= hi:
        mid = (lo + hi) // 2
        if ok(mid):
            hi = mid - 1
        else:
            lo = mid + 1
    return lo


# --- dynamic programming ---------------------------------------------------------
def fib(n: int, memo: dict[int, int] | None = None) -> int:
    memo = {} if memo is None else memo
    if n < 2:
        return n
    if n not in memo:
        memo[n] = fib(n - 1, memo) + fib(n - 2, memo)
    return memo[n]


def lcs(a: str, b: str) -> str:
    """Longest common subsequence."""
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) - 1, -1, -1):
        for j in range(len(b) - 1, -1, -1):
            dp[i][j] = dp[i + 1][j + 1] + 1 if a[i] == b[j] else max(dp[i + 1][j], dp[i][j + 1])
    out, i, j = [], 0, 0
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            out.append(a[i]); i += 1; j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    return "".join(out)


def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def knapsack(items: Sequence[tuple[int, int]], capacity: int) -> tuple[int, list[int]]:
    """0/1 knapsack. items = (weight, value). Returns best value and chosen indexes."""
    n = len(items)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    for i, (w, v) in enumerate(items, 1):
        for c in range(capacity + 1):
            dp[i][c] = dp[i - 1][c]
            if w <= c:
                dp[i][c] = max(dp[i][c], dp[i - 1][c - w] + v)
    chosen, c = [], capacity
    for i in range(n, 0, -1):
        if dp[i][c] != dp[i - 1][c]:
            chosen.append(i - 1)
            c -= items[i - 1][0]
    return dp[n][capacity], sorted(chosen)


def coin_change(coins: Sequence[int], amount: int) -> int:
    """Fewest coins to make `amount`, or -1."""
    INF = amount + 1
    dp = [0] + [INF] * amount
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a:
                dp[a] = min(dp[a], dp[a - c] + 1)
    return dp[amount] if dp[amount] != INF else -1


def longest_increasing_subsequence(a: Sequence[int]) -> int:
    tails: list[int] = []
    for x in a:
        i = lower_bound(tails, x)
        if i == len(tails):
            tails.append(x)
        else:
            tails[i] = x
    return len(tails)


def n_queens(n: int) -> int:
    """Number of solutions, by backtracking with bitmasks."""
    full = (1 << n) - 1

    def place(cols: int, d1: int, d2: int) -> int:
        if cols == full:
            return 1
        total, free = 0, full & ~(cols | d1 | d2)
        while free:
            bit = free & -free
            free ^= bit
            total += place(cols | bit, ((d1 | bit) << 1) & full, (d2 | bit) >> 1)
        return total

    return place(0, 0, 0)


def permutations(items: Sequence) -> list[list]:
    if len(items) <= 1:
        return [list(items)]
    return [[items[i]] + rest for i in range(len(items)) for rest in permutations(list(items[:i]) + list(items[i + 1:]))]


def sieve(limit: int) -> list[int]:
    if limit < 2:
        return []
    flags = bytearray([1]) * (limit + 1)
    flags[0:2] = b"\x00\x00"
    for p in range(2, int(limit ** 0.5) + 1):
        if flags[p]:
            flags[p * p::p] = bytearray(len(flags[p * p::p]))
    return [i for i, f in enumerate(flags) if f]


def gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return abs(a)
