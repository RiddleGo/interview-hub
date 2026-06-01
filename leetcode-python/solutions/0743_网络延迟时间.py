"""Python solution extracted from problems/0743.网络延迟时间.md."""
from __future__ import annotations

"""Auto-generated placeholder converted from `cpp`.
Source: problems\0743.网络延迟时间.md
Manual rewrite may be required for algorithm equivalence.
"""

from typing import Any


def solve(*args: Any, **kwargs: Any) -> Any:
    """
    TODO: Replace this placeholder with a real Python implementation.
    Original source is preserved in ORIGINAL_SNIPPET.
    """
    raise NotImplementedError("Auto-generated placeholder; implement in Python")


ORIGINAL_SNIPPET = """
class Solution {
public:
    int networkDelayTime(vector<vector<int>>& times, int n, int k) {

        // 注意题目中给的二维数组并不是领接矩阵
        // 需要邻接矩阵来存图
        // 因为本题处理方式是节点标号从1开始，所以数组的大小都是 n+1
        vector<vector<int>> grid(n + 1, vector<int>(n + 1, INT_MAX));
        for(int i = 0; i < times.size(); i++){
            int p1 = times[i][0];
            int p2 = times[i][1];
            grid[p1][p2] = times[i][2];
        }

        // 存储从源点到每个节点的最短距离
        std::vector<int> minDist(n + 1, INT_MAX);  

        // 记录顶点是否被访问过
        std::vector<bool> visited(n + 1, false); 

        minDist[k] = 0;  // 起始点到自身的距离为0
        for (int i = 1; i <= n; i++) {

            int minVal = INT_MAX;
            int cur = 1;

            // 遍历每个节点，选择未被访问的节点集合中哪个节点到源点的距离最小
            for (int v = 1; v <= n; ++v) {
                if (!visited[v] && minDist[v] <= minVal) {
                    minVal = minDist[v];
                    cur = v;
                }
            }

            visited[cur] = true;  // 标记该顶点已被访问

            for (int v = 1; v <= n; v++) {
                if (!visited[v] && grid[cur][v] != INT_MAX && minDist[cur] + grid[cur][v] < minDist[v]) {
                    minDist[v] = minDist[cur] + grid[cur][v];
                }
            }


        }
        // 源点到最远的节点的时间，也就是寻找 源点到所有节点最短路径的最大值 
        int result = 0;
        for (int i = 1; i <= n; i++) {
            if (minDist[i] == INT_MAX) return -1;// 没有路径
            result = max(minDist[i], result);
        }
        return result;

    }
};
"""
