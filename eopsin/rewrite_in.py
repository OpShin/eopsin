from ast import *
import typing

"""
Rewrites all occurences of in to a for loop
TODO alternative: efficiently compile to uplc in compiler.py
"""


class RewriteIn(NodeTransformer):

    unique_id = 0

    def visit_Compare(self, node: Compare) -> typing.List[stmt]:
        if len(node.comparators) != 1 or len(node.ops) != 1:
            return node
        if not isinstance(node.ops[0], In):
            return node
        uid = self.unique_id
        self.unique_id += 1
        return [
            Assign(
                targets=Name(id=f"{uid}_in_counter", ctx=Store()), value=Constant(0)
            ),
            For(
                expr_target=Name(id=f"{uid}_in", ctx=Load()),
                expr_iter=node.comparators[0],
                stmt=[If()],
            ),
        ]
