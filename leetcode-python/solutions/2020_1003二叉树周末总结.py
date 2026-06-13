"""Python solution extracted from problems/周总结/20201003二叉树周末总结.md."""
from __future__ import annotations

"""Auto-generated placeholder converted from `cpp`.
Source: problems\周总结\20201003二叉树周末总结.md
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
    bool compare(TreeNode* left, TreeNode* right) {
        // 首先排除空节点的情况
        if (left == NULL && right != NULL) return false;
        else if (left != NULL && right == NULL) return false;
        else if (left == NULL && right == NULL) return true;
        // 排除了空节点，再排除数值不相同的情况
        else if (left->val != right->val) return false;

        // 此时就是：左右节点都不为空，且数值相同的情况
        // 此时才做递归，做下一层的判断
        bool outside = compare(left->left, right->left);   // 左子树：左、 右子树：左 （相对于求对称二叉树，只需改一下这里的顺序）
        bool inside = compare(left->right, right->right);    // 左子树：右、 右子树：右
        bool isSame = outside && inside;                    // 左子树：中、 右子树：中 （逻辑处理）
        return isSame;

    }
    bool isSymmetric(TreeNode* p, TreeNode* q) {
        return compare(p, q);
    }
};
"""
