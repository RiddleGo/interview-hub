"""Python solution extracted from problems/0332.重新安排行程.md."""
from __future__ import annotations

class Solution:
    def findItinerary(self, tickets: List[List[str]]) -> List[str]:
        self.adj = {}

        # sort by the destination alphabetically
        # 根据航班每一站的重点字母顺序排序
        tickets.sort(key=lambda x:x[1])

        # get all possible connection for each destination
        # 罗列每一站的下一个可选项
        for u,v in tickets:
            if u in self.adj: self.adj[u].append(v)
            else: self.adj[u] = [v]

        # 从JFK出发
        self.result = []
        self.dfs("JFK")  # start with JFK

        return self.result[::-1]  # reverse to get the result

    def dfs(self, s):
        # if depart city has flight and the flight can go to another city
        while s in self.adj and len(self.adj[s]) > 0:
            # 找到s能到哪里，选能到的第一个机场
            v = self.adj[s][0]  # we go to the 1 choice of the city
            # 在之后的可选项机场中去掉这个机场
            self.adj[s].pop(0)  # get rid of this choice since we used it
            # 从当前的新出发点开始
            self.dfs(v)  # we start from the new airport

        self.result.append(s)  # after append, it will back track to last node, thus the result list is in reversed order
