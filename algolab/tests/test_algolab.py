import random
import unittest

from algolab import algorithms as alg
from algolab.structures import BST, BloomFilter, LinkedList, LRUCache, MinHeap, Trie


class SortingTests(unittest.TestCase):
    def test_all_sorts_match_builtin(self):
        rng = random.Random(1)
        samples = [[], [1], [2, 1], [5] * 10, list(range(50)), list(range(50, 0, -1))]
        samples += [[rng.randint(-100, 100) for _ in range(rng.randint(0, 80))] for _ in range(30)]
        for s in samples:
            expected = sorted(s)
            for fn in (alg.merge_sort, alg.quick_sort, alg.heap_sort, alg.counting_sort):
                self.assertEqual(fn(s), expected, f"{fn.__name__}({s})")

    def test_quick_sort_does_not_mutate_input(self):
        data = [3, 1, 2]
        alg.quick_sort(data)
        self.assertEqual(data, [3, 1, 2])


class SearchTests(unittest.TestCase):
    def test_binary_search(self):
        a = [1, 3, 5, 7, 9, 11]
        self.assertEqual([alg.binary_search(a, x) for x in a], list(range(6)))
        self.assertEqual(alg.binary_search(a, 4), -1)
        self.assertEqual(alg.binary_search([], 1), -1)

    def test_lower_bound(self):
        a = [1, 2, 2, 2, 5]
        self.assertEqual((alg.lower_bound(a, 2), alg.lower_bound(a, 3), alg.lower_bound(a, 9), alg.lower_bound(a, 0)), (1, 4, 5, 0))

    def test_bisect_answer(self):
        self.assertEqual(alg.bisect_answer(lambda x: x * x >= 50, 0, 100), 8)
        self.assertEqual(alg.bisect_answer(lambda x: False, 0, 10), 11)


class DynamicProgrammingTests(unittest.TestCase):
    def test_fib(self):
        self.assertEqual([alg.fib(i) for i in range(10)], [0, 1, 1, 2, 3, 5, 8, 13, 21, 34])
        self.assertEqual(alg.fib(90), 2880067194370816120)

    def test_lcs_and_edit_distance(self):
        self.assertEqual(len(alg.lcs("ABCBDAB", "BDCABA")), 4)
        self.assertEqual(alg.lcs("abc", "xyz"), "")
        self.assertEqual(alg.edit_distance("kitten", "sitting"), 3)
        self.assertEqual(alg.edit_distance("", "abc"), 3)

    def test_knapsack(self):
        value, chosen = alg.knapsack([(1, 1), (3, 4), (4, 5), (5, 7)], 7)
        self.assertEqual((value, chosen), (9, [1, 2]))

    def test_coin_change(self):
        self.assertEqual(alg.coin_change([1, 5, 10, 25], 63), 6)
        self.assertEqual(alg.coin_change([2], 3), -1)
        self.assertEqual(alg.coin_change([1], 0), 0)

    def test_lis(self):
        self.assertEqual(alg.longest_increasing_subsequence([10, 9, 2, 5, 3, 7, 101, 18]), 4)

    def test_n_queens(self):
        self.assertEqual([alg.n_queens(n) for n in range(1, 9)], [1, 0, 0, 2, 10, 4, 40, 92])

    def test_number_theory_and_combinatorics(self):
        self.assertEqual(alg.sieve(30), [2, 3, 5, 7, 11, 13, 17, 19, 23, 29])
        self.assertEqual(alg.sieve(1), [])
        self.assertEqual(alg.gcd(48, -18), 6)
        self.assertEqual(len(alg.permutations([1, 2, 3, 4])), 24)
        self.assertIn([3, 1, 2], alg.permutations([1, 2, 3]))


class StructureTests(unittest.TestCase):
    def test_lru(self):
        c = LRUCache(2)
        c.put("a", 1); c.put("b", 2)
        c.get("a")
        c.put("c", 3)  # evicts b
        self.assertEqual((c.get("b"), c.get("a"), c.get("c")), (None, 1, 3))
        self.assertEqual((c.hits, c.misses), (3, 1))
        with self.assertRaises(ValueError):
            LRUCache(0)

    def test_trie(self):
        t = Trie()
        for w in ["casa", "caso", "casaco", "carro", "cama"]:
            t.insert(w)
        self.assertTrue(t.contains("casa"))
        self.assertFalse(t.contains("cas"))
        self.assertEqual(t.complete("cas"), ["casa", "casaco", "caso"])
        self.assertEqual(t.complete("cas", limit=2), ["casa", "casaco"])
        self.assertEqual(t.complete("zzz"), [])

    def test_heap(self):
        rng = random.Random(3)
        data = [rng.randint(0, 1000) for _ in range(200)]
        h = MinHeap(data)
        self.assertEqual([h.pop() for _ in range(len(data))], sorted(data))
        mx = MinHeap([3, 9, 1], key=lambda x: -x)
        self.assertEqual(mx.pop(), 9)
        with self.assertRaises(IndexError):
            MinHeap().pop()

    def test_linked_list(self):
        ll = LinkedList([1, 2, 3])
        ll.append(4)
        ll.push_front(0)
        self.assertEqual(list(ll), [0, 1, 2, 3, 4])
        self.assertEqual(ll.middle(), 2)
        ll.reverse()
        self.assertEqual(list(ll), [4, 3, 2, 1, 0])
        self.assertTrue(ll.remove(3) and ll.remove(0))
        self.assertFalse(ll.remove(99))
        self.assertEqual((list(ll), len(ll)), ([4, 2, 1], 3))

    def test_bst(self):
        t = BST()
        for k in [50, 30, 70, 20, 40, 60, 80]:
            t.put(k, str(k))
        t.put(40, "quarenta")
        self.assertEqual([k for k, _ in t.items()], [20, 30, 40, 50, 60, 70, 80])
        self.assertEqual((t.get(40), t.get(99), len(t), t.height()), ("quarenta", None, 7, 3))
        self.assertTrue(t.delete(50))  # root with two children
        self.assertTrue(t.delete(20))
        self.assertFalse(t.delete(1234))
        self.assertEqual([k for k, _ in t.items()], [30, 40, 60, 70, 80])
        self.assertEqual(len(t), 5)

    def test_bloom_filter_has_no_false_negatives(self):
        bf = BloomFilter(bits=4096, hashes=3)
        words = [f"palavra{i}" for i in range(100)]
        for w in words:
            bf.add(w)
        self.assertTrue(all(bf.might_contain(w) for w in words))
        false_positives = sum(bf.might_contain(f"outra{i}") for i in range(1000))
        self.assertLess(false_positives, 100)


if __name__ == "__main__":
    unittest.main()
