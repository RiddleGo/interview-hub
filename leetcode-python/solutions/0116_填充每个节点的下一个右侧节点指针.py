"""Python solution extracted from problems/0116.填充每个节点的下一个右侧节点指针.md."""
from __future__ import annotations

# 递归法
class Solution:
    def connect(self, root: 'Node') -> 'Node':
        def traversal(cur: 'Node') -> 'Node':
            if not cur: return []
            if cur.left: cur.left.next = cur.right # 操作1
            if cur.right:
                if cur.next:
                    cur.right.next = cur.next.left # 操作2
                else:
                    cur.right.next = None
            traversal(cur.left) # 左
            traversal(cur.right) # 右
        traversal(root)
        return root
