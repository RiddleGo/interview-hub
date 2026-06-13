"""Python solution extracted from problems/1971.寻找图中是否存在路径.md."""
from __future__ import annotations

class Solution:
    def validPath(self, n: int, edges: List[List[int]], source: int, destination: int) -> bool:
        p = [i for i in range(n)]
        def find(i):
            if p[i] != i:
                p[i] = find(p[i])
            return p[i]
        for u, v in edges:
            p[find(u)] = find(v)
        return find(source) == find(destination)
