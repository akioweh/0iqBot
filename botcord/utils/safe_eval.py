"""Helpers to safely evaluate different expressions as strings.

Currently only contains a MathParser"""

import ast
import operator as op
from numbers import Number
from typing import Callable, Final, NoReturn


class MathParser:
    """Basic Safe Arithmetic Expression Parser
    Expressions must follow Python code syntax -
    i.e. 2**3 and not 2^3; 2*3 and not 2(3)"""

    _BIN_OPs: Final[dict[ast.operator, Callable[[Number, Number], Number]]] = {
        ast.Add     : op.add,
        ast.Sub     : op.sub,
        ast.Mult    : op.mul,
        ast.Div     : op.truediv,
        ast.FloorDiv: op.floordiv,
        ast.Mod     : op.mod,
        ast.Pow     : op.pow,
        ast.LShift  : op.lshift,
        ast.RShift  : op.rshift,
        ast.BitOr   : op.or_,
        ast.BitXor  : op.xor,
        ast.BitAnd  : op.and_,
        ast.MatMult : op.matmul
    }

    _UN_OPs: Final[dict[ast.unaryop, Callable[[Number], Number]]] = {
        ast.Not   : op.not_,
        ast.Invert: op.inv,
        ast.USub  : op.neg,
        ast.UAdd  : op.pos
    }

    def __init__(self, allowed_operations: set = None):
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

            def disallowed_op(op_type: ast.operator | ast.unaryop) -> Callable[[...], NoReturn]:
                def func(*_):
                    raise ArithmeticError(f'Operation {op_type.__name__} is not allowed')
                return func

            for k, v in self.bin_ops.items():
                if v not in allowed_operations:
                    self.bin_ops[k] = disallowed_op(k)
            for k, v in self.un_ops.items():
                if v not in allowed_operations:
                    self.un_ops[k] = disallowed_op(k)

    def eval(self, node: ast.Expression | ast.expr) -> ast.expr | int | float:
        if isinstance(node, ast.Expression):
            return self.eval(node.body)

        elif isinstance(node, ast.expr):
            if isinstance(node, ast.BinOp):
                # noinspection PyTypeChecker
                return self.bin_ops[type(node.op)](self.eval(node.left), self.eval(node.right))

            elif isinstance(node, ast.UnaryOp):
                # noinspection PyTypeChecker
                return self.un_ops[type(node.op)](self.eval(node.operand))

            elif isinstance(node, ast.Constant):
                if not isinstance(val := node.value, Number):
                    raise TypeError(f'Non-Number constant literal found: {val!r} of type {type(val)}')
                return val

            else:
                # noinspection PyTypeChecker
                raise TypeError(f'Non-math-y expression {ast.dump(node)} of type {type(node)}')

        else:
            raise TypeError(f'WTF, this should not have happened. Expression.body should always return ast.expr'
                            f'but got {type(node)}')

    def parse(self, expr: str) -> int | float:
        # ast.parse() in eval mode always returns ast.Expression object; the stub type is inaccurate
        # noinspection PyTypeChecker
        ast_data: ast.Expression = ast.parse(expr, mode='eval')
        return self.eval(ast_data)
