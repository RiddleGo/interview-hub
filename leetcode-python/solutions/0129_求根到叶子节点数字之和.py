"""Python solution extracted from problems/0129.求根到叶子节点数字之和.md."""
from __future__ import annotations

class Solution:
    def sumNumbers(self, root: TreeNode) -> int:
        res = 0
        path = []
        def backtrace(root):
            nonlocal res
            if not root: return # 节点空则返回
            path.append(root.val)
            if not root.left and not root.right: # 遇到了叶子节点
                res += get_sum(path)
            if root.left: # 左子树不空
                backtrace(root.left)
            if root.right: # 右子树不空
                backtrace(root.right)
            path.pop()

        def get_sum(arr):
            s = 0
            for i in range(len(arr)):
                s = s * 10 + arr[i]
            return s

        backtrace(root)
        return res
