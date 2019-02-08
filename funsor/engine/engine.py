from __future__ import absolute_import, division, print_function

import opt_einsum

import funsor.ops as ops
from funsor.terms import Binary, Finitary, Funsor, Reduction, Tensor, Unitary

from .paths import greedy


def eval(x):
    r"""
    Optimized evaluation of deferred expressions.

    This handles a limited class of expressions, raising
    ``NotImplementedError`` in unhandled cases.

    :param Funsor x: An input funsor, typically deferred.
    :return: An evaluated funsor.
    :rtype: Funsor
    :raises: NotImplementedError
    """
    assert isinstance(x, Funsor)

    # evaluate the path
    if isinstance(x, Tensor):
        return x
   
    if isinstance(x, Reduction):
        return x.reduce(x.op, eval(x.terms))

    if isinstance(x, Binary):
        return _operators[x.op](eval(x.lhs), eval(x.rhs))

    if isinstance(x, Unary):
        return _operators[x.op](eval(x.v))

    if isinstance(x, Finitary):
        return reduce(x.op, [eval(tx) for tx in x.terms])

    if isinstance(x, Contract):
        return contract(*[eval(tx) for tx in x.operands], ops=x.ops)

    raise NotImplementedError


def _parse_reduction(op, x):
    if isinstance(x, Reduction) and x.op is op:
        yield x.arg, x.reduce_dims


def _parse_commutative(op, x):
    pending = [x]
    terms = []
    while pending:
        x = pending.pop()
        if isinstance(x, Binary) and x.op is op:
            pending.append(x.lhs)
            pending.append(x.rhs)
        else:
            terms.append(x)
    return terms


def contract(*operands, **kwargs):
    r"""
    Sum-product contraction operation.

    :param tuple dims: a tuple of strings of output dimensions. Any input dim
        not requested as an output dim will be summed out.
    :param \*operands: multiple :class:`Funsor`s.
    :param tuple dims: An optional tuple of output dims to preserve.
        Defaults to ``()``, meaning all dims are contracted.
    :param str backend: An opt_einsum backend, defaults to 'torch'.
    :return: A contracted funsor.
    :rtype: Funsor
    """
    # # Handle sum-product contractions.
    # for arg, reduce_dims in _parse_reduction(ops.add, x):
    #     operands = _parse_commutative(ops.mul, arg)
    #     dims = tuple(d for d in arg.dims if d not in reduce_dims)
    #     head = contract(*operands, dims=dims)

    # # Handle log-sum-product-exp contractions.
    # for arg, reduce_dims in _parse_reduction(ops.logaddexp, x):
    #     operands = _parse_commutative(ops.add, arg)
    #     dims = tuple(d for d in arg.dims if d not in reduce_dims)
    #     return contract(*operands, dims=dims, backend='pyro.ops.einsum.torch_log')


    assert all(isinstance(x, Funsor) for x in operands)
    dims = kwargs.pop('dims', ())
    assert isinstance(dims, tuple)
    assert all(isinstance(d, str) for d in dims)
    kwargs.setdefault('backend', 'torch')
    args = []
    for x in operands:
        x = x.materialize()
        if not isinstance(x, Tensor):
            raise NotImplementedError
        args.extend([x.data, x.dims])
    args.append(dims)
    data = opt_einsum.contract(*args, **kwargs)  # TODO use backend einsum directly
    return Tensor(dims, data)


__all__ = [
    'contract',
    'eval',
]