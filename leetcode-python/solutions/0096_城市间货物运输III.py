"""Python solution extracted from problems/kamacoder/0096.城市间货物运输III.md."""
from __future__ import annotations

def main():
    # 輸入
    n, m = map(int, input().split())
    edges = list()
    for _ in range(m):
        edges.append(list(map(int, input().split() )))
    
    start, end, k = map(int, input().split())
    min_dist = [float('inf') for _ in range(n + 1)]
    min_dist[start] = 0
    
    # 只能經過k個城市，所以從起始點到中間有(k + 1)個邊連接
    # 需要鬆弛(k + 1)次
    
    for _ in range(k + 1):
        update = False
        min_dist_copy = min_dist.copy()
        for src, desc, w in edges:
            if (min_dist_copy[src] != float('inf') and 
            min_dist_copy[src] + w < min_dist[desc]):
                min_dist[desc] = min_dist_copy[src] + w
                update = True
        if not update:
            break
    # 輸出
    if min_dist[end] == float('inf'):
        print('unreachable')
    else:
        print(min_dist[end])
            
            

if __name__ == "__main__":
    main()
