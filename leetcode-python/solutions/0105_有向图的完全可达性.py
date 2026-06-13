"""Python solution extracted from problems/kamacoder/0105.有向图的完全可达性.md."""
from __future__ import annotations

import collections

path = set()  # 纪录 BFS 所经过之节点

def bfs(root, graph):
    global path
    
    que = collections.deque([root])
    while que:
        cur = que.popleft()
        path.add(cur)
        
        for nei in graph[cur]:
            que.append(nei)
        graph[cur] = []
    return

def main():
    N, K = map(int, input().strip().split())
    graph = collections.defaultdict(list)
    for _ in range(K):
        src, dest = map(int, input().strip().split())
        graph[src].append(dest)
    
    bfs(1, graph)
    if path == {i for i in range(1, N + 1)}:
        return 1
    return -1
        

if __name__ == "__main__":
    print(main())
