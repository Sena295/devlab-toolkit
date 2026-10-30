"""Classic data structures implemented from scratch (for study; Python's built-ins are faster)."""
from __future__ import annotations

from collections import OrderedDict
from typing import Generic, Hashable, Iterator, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")
T = TypeVar("T")


class LRUCache(Generic[K, V]):
    def __init__(self, capacity: int):
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self.capacity = capacity
        self._data: OrderedDict[K, V] = OrderedDict()
        self.hits = self.misses = 0

    def get(self, key: K, default: V | None = None) -> V | None:
        if key in self._data:
            self._data.move_to_end(key)
            self.hits += 1
            return self._data[key]
        self.misses += 1
        return default

    def put(self, key: K, value: V) -> None:
        self._data[key] = value
        self._data.move_to_end(key)
        if len(self._data) > self.capacity:
            self._data.popitem(last=False)

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: object) -> bool:
        return key in self._data

    def keys(self) -> list[K]:
        return list(self._data)  # least recently used first


class Trie:
    """Prefix tree with word counts and autocomplete."""

    def __init__(self) -> None:
        self.children: dict[str, Trie] = {}
        self.count = 0

    def insert(self, word: str) -> None:
        node = self
        for ch in word:
            node = node.children.setdefault(ch, Trie())
        node.count += 1

    def _walk(self, prefix: str) -> "Trie | None":
        node = self
        for ch in prefix:
            node = node.children.get(ch)
            if node is None:
                return None
        return node

    def contains(self, word: str) -> bool:
        node = self._walk(word)
        return node is not None and node.count > 0

    def complete(self, prefix: str, limit: int = 10) -> list[str]:
        node = self._walk(prefix)
        out: list[str] = []

        def visit(n: Trie, acc: str) -> None:
            if len(out) >= limit:
                return
            if n.count:
                out.append(acc)
            for ch in sorted(n.children):
                visit(n.children[ch], acc + ch)

        if node:
            visit(node, prefix)
        return out


class MinHeap(Generic[T]):
    """Binary heap stored in a list; `key` customises ordering (use it for max-heaps)."""

    def __init__(self, items=(), key=lambda x: x):
        self._a: list[T] = []
        self._key = key
        for it in items:
            self.push(it)

    def __len__(self) -> int:
        return len(self._a)

    def peek(self) -> T:
        if not self._a:
            raise IndexError("heap is empty")
        return self._a[0]

    def push(self, item: T) -> None:
        a = self._a
        a.append(item)
        i = len(a) - 1
        while i > 0:
            parent = (i - 1) // 2
            if self._key(a[i]) >= self._key(a[parent]):
                break
            a[i], a[parent] = a[parent], a[i]
            i = parent

    def pop(self) -> T:
        a = self._a
        if not a:
            raise IndexError("heap is empty")
        top, last = a[0], a.pop()
        if a:
            a[0] = last
            i = 0
            while True:
                left, right, small = 2 * i + 1, 2 * i + 2, i
                if left < len(a) and self._key(a[left]) < self._key(a[small]):
                    small = left
                if right < len(a) and self._key(a[right]) < self._key(a[small]):
                    small = right
                if small == i:
                    break
                a[i], a[small] = a[small], a[i]
                i = small
        return top


class _Node(Generic[T]):
    __slots__ = ("value", "next")

    def __init__(self, value: T, next: "_Node[T] | None" = None):
        self.value, self.next = value, next


class LinkedList(Generic[T]):
    def __init__(self, items=()):
        self.head: _Node[T] | None = None
        self._size = 0
        for it in reversed(list(items)):
            self.push_front(it)

    def __len__(self) -> int:
        return self._size

    def __iter__(self) -> Iterator[T]:
        n = self.head
        while n:
            yield n.value
            n = n.next

    def push_front(self, value: T) -> None:
        self.head = _Node(value, self.head)
        self._size += 1

    def append(self, value: T) -> None:
        node = _Node(value)
        if not self.head:
            self.head = node
        else:
            n = self.head
            while n.next:
                n = n.next
            n.next = node
        self._size += 1

    def remove(self, value: T) -> bool:
        prev, n = None, self.head
        while n:
            if n.value == value:
                if prev:
                    prev.next = n.next
                else:
                    self.head = n.next
                self._size -= 1
                return True
            prev, n = n, n.next
        return False

    def reverse(self) -> None:
        prev, n = None, self.head
        while n:
            n.next, prev, n = prev, n, n.next
        self.head = prev

    def middle(self) -> T:
        """Tortoise and hare: the middle element in a single pass."""
        if not self.head:
            raise IndexError("empty list")
        slow = fast = self.head
        while fast.next and fast.next.next:
            slow, fast = slow.next, fast.next.next
        return slow.value


class BST(Generic[K, V]):
    """Unbalanced binary search tree with in-order iteration and deletion."""

    class _N:
        __slots__ = ("key", "value", "left", "right")

        def __init__(self, key, value):
            self.key, self.value, self.left, self.right = key, value, None, None

    def __init__(self) -> None:
        self.root = None
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def put(self, key: K, value: V) -> None:
        if self.root is None:
            self.root = self._N(key, value)
            self._size = 1
            return
        n = self.root
        while True:
            if key == n.key:
                n.value = value
                return
            side = "left" if key < n.key else "right"
            nxt = getattr(n, side)
            if nxt is None:
                setattr(n, side, self._N(key, value))
                self._size += 1
                return
            n = nxt

    def get(self, key: K, default=None):
        n = self.root
        while n:
            if key == n.key:
                return n.value
            n = n.left if key < n.key else n.right
        return default

    def height(self) -> int:
        def h(n):
            return 0 if n is None else 1 + max(h(n.left), h(n.right))
        return h(self.root)

    def items(self) -> Iterator[tuple[K, V]]:
        stack, n = [], self.root
        while stack or n:
            while n:
                stack.append(n)
                n = n.left
            n = stack.pop()
            yield n.key, n.value
            n = n.right

    def delete(self, key: K) -> bool:
        def remove(n, key):
            if n is None:
                return None, False
            if key < n.key:
                n.left, ok = remove(n.left, key)
                return n, ok
            if key > n.key:
                n.right, ok = remove(n.right, key)
                return n, ok
            if n.left is None:
                return n.right, True
            if n.right is None:
                return n.left, True
            succ = n.right
            while succ.left:
                succ = succ.left
            n.key, n.value = succ.key, succ.value
            n.right, _ = remove(n.right, succ.key)
            return n, True

        self.root, ok = remove(self.root, key)
        if ok:
            self._size -= 1
        return ok


class BloomFilter:
    """Probabilistic set: no false negatives, tunable false-positive rate."""

    def __init__(self, bits: int = 1024, hashes: int = 3):
        self.bits, self.hashes = bits, hashes
        self.array = bytearray(bits)

    def _positions(self, item: str):
        import hashlib
        digest = hashlib.sha256(item.encode()).digest()
        for i in range(self.hashes):
            yield int.from_bytes(digest[i * 4:i * 4 + 4], "big") % self.bits

    def add(self, item: str) -> None:
        for p in self._positions(item):
            self.array[p] = 1

    def might_contain(self, item: str) -> bool:
        return all(self.array[p] for p in self._positions(item))
