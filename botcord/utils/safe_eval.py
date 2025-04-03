"""
Helpers to safely evaluate different expressions as strings.

Currently only contains a MathParser
"""

import ast
import operator as op
from typing import Callable, Final, NoReturn

type Num = int | float


class MathParser:
    """Basic Safe Arithmetic Expression Parser
    Expressions must follow Python code syntax -
    i.e. 2**3 and not 2^3; 2*3 and not 2(3)"""

    # todo: this seems really dumb... also, the typing issue is not my problem; typeshed bad
    _BIN_OPs: Final[dict[ast.operator, Callable[[Num, Num], Num]]] = {
        ast.Add: op.add,  # type: ignore
        ast.Sub: op.sub,  # type: ignore
        ast.Mult: op.mul,  # type: ignore
        ast.Div: op.truediv,  # type: ignore
        ast.FloorDiv: op.floordiv,  # type: ignore
        ast.Mod: op.mod,  # type: ignore
        ast.Pow: op.pow,  # type: ignore
        ast.LShift: op.lshift,  # type: ignore
        ast.RShift: op.rshift,  # type: ignore
        ast.BitOr: op.or_,  # type: ignore
        ast.BitXor: op.xor,  # type: ignore
        ast.BitAnd: op.and_,  # type: ignore
        ast.MatMult: op.matmul  # type: ignore
    }

    _UN_OPs: Final[dict[ast.unaryop, Callable[[Num], Num]]] = {
        ast.Not: op.not_,  # type: ignore
        ast.Invert: op.inv,  # type: ignore
        ast.USub: op.neg,  # type: ignore
        ast.UAdd: op.pos  # type: ignore
    }

    def __init__(self, allowed_operations: set | None = None):
        """
        :param allowed_operations: set of functions from the builtin operator module
        that are allowed in an expression.
        If None (default), all operations are allowed.

        :raises ValueError when allowed_operations is incorrect
        :raises ArithmeticError when expression contains disallowed operations
        :raises TypeError when expression contains non-math items
        :raises SyntaxError when expression is syntactically invalid (it must be valid as a Python expression)
        """
        self.bin_ops = MathParser._BIN_OPs.copy()
        self.un_ops = MathParser._UN_OPs.copy()

        if allowed_operations is not None:
            for i in allowed_operations:
                if i not in self.bin_ops.values() and i not in self.un_ops.values():
                    raise ValueError(f'Trying to set {i!r} as an allowed operation, but it is not a valid operation')

            def disallowed_op(op_type: ast.operator | ast.unaryop) -> Callable[..., NoReturn]:
                def func(*_):
                    raise ArithmeticError(f'Operation {op_type.__name__} is not allowed')

                return func

            for k, v in self.bin_ops.items():
                if v not in allowed_operations:
                    self.bin_ops[k] = disallowed_op(k)
            for k_, v_ in self.un_ops.items():
                if v_ not in allowed_operations:
                    self.un_ops[k_] = disallowed_op(k_)

    def eval(self, node: ast.Expression | ast.expr) -> Num:
        if isinstance(node, ast.Expression):
            return self.eval(node.body)

        elif isinstance(node, ast.expr):
            if isinstance(node, ast.BinOp):
                return self.bin_ops[node.op](self.eval(node.left), self.eval(node.right))

            elif isinstance(node, ast.UnaryOp):
                return self.un_ops[node.op](self.eval(node.operand))

            elif isinstance(node, ast.Constant):
                if not isinstance(val := node.value, (int, float)):
                    raise TypeError(f'Non-Number constant literal found: {val!r} of type {type(val)}')
                return val

            else:
                raise TypeError(f'Non-math-y expression {ast.dump(node)} of type {type(node)}')

        else:
            raise TypeError(f'WTF, this should not have happened. Expression.body should always return ast.expr'
                            f'but got {type(node)}')

    def parse(self, expr: str) -> Num:
        ast_data: ast.Expression = ast.parse(expr, mode='eval')
        return self.eval(ast_data)
