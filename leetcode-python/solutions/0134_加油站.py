"""Auto-sanitized placeholder after syntax validation failure."""
from typing import Any

def solve(*args: Any, **kwargs: Any) -> Any:
    raise NotImplementedError("Sanitized placeholder; manual Python rewrite required")

ORIGINAL_SNIPPET = """
\"\"\"Python solution extracted from problems/0134.加油站.md.\"\"\"
from __future__ import annotations

// 解法3
class Solution {
    public int canCompleteCircuit(int[] gas, int[] cost) {
        int tank = 0; // 当前油量
        int totalGas = 0;  // 总加油量
        int totalCost = 0; // 总油耗
        int start = 0; // 起点
        for (int i = 0; i < gas.length; i++) {
            totalGas += gas[i];
            totalCost += cost[i];
            
            tank += gas[i] - cost[i];
            if (tank < 0) { // tank 变为负数 意味着 从0到i之间出发都不能顺利环路一周，因为在此i点必会没油
                tank = 0; // reset tank，类似于题目53.最大子树和reset sum
                start = i + 1; // 起点变为i点往后一位
            }
        }
        if (totalCost > totalGas) return -1;
        return start;
    }
}

"""
