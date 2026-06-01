"""Python solution extracted from problems/二叉树中递归带着回溯.md."""
from __future__ import annotations

"""Auto-generated placeholder converted from `cpp`.
Source: problems\二叉树中递归带着回溯.md
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
    bool compare(TreeNode* tree1, TreeNode* tree2) {
        if (tree1 == NULL && tree2 != NULL) return false;
        else if (tree1 != NULL && tree2 == NULL) return false;
        else if (tree1 == NULL && tree2 == NULL) return true;
        else if (tree1->val != tree2->val) return false; // 注意这里我没有使用else

        // 此时就是：左右节点都不为空，且数值相同的情况
        // 此时才做递归，做下一层的判断
        bool compareLeft = compare(tree1->left, tree2->left);       // 左子树：左、 右子树：左
        bool compareRight = compare(tree1->right, tree2->right);    // 左子树：右、 右子树：右
        bool isSame = compareLeft && compareRight;                  // 左子树：中、 右子树：中（逻辑处理）
        return isSame;

    }
    bool isSameTree(TreeNode* p, TreeNode* q) {
        return compare(p, q);
    }
};
"""
