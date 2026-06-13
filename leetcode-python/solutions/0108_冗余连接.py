"""Python solution extracted from problems/kamacoder/0108.冗余连接.md."""
from __future__ import annotations

father = list()

def find(u):
    if u == father[u]:
        return u
    else:
        father[u] = find(father[u])
        return father[u]
        
def is_same(u, v):
    u = find(u)
    v = find(v)
    return u == v
    
def join(u, v):
    u = find(u)
    v = find(v)
    if u != v:
        father[u] = v
        
if __name__ == "__main__":
    # 輸入
    n = int(input())
    for i in range(n + 1):
        father.append(i)
    # 尋找冗余邊    
    result = None
    for i in range(n):
        s, t = map(int, input().split())
        if is_same(s, t):
            result = str(s) + ' ' + str(t)
        else:
            join(s, t)
        
    # 輸出
    print(result)
