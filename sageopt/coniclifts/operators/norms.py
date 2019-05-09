import numpy as np
from sageopt.coniclifts.base import NonlinearScalarAtom, Expression, ScalarExpression, Variable
from sageopt.coniclifts.cones import Cone


def vector2norm(x):
    if not isinstance(x, Expression):
        x = Expression(x)
    x = x.ravel()
    d = {Vector2Norm(x): 1}
    return ScalarExpression(d, 0).as_expr()


class Vector2Norm(NonlinearScalarAtom):

    _VECTOR_2_NORM_COUNTER_ = 0

    @staticmethod
    def __atom_text__():
        return 'Vector2Norm'

    def __init__(self, args):
        args = args.as_expr().ravel()
        self._args = tuple(self.parse_arg(v) for v in args)
        self.aux_var = None
        self._id = Vector2Norm._VECTOR_2_NORM_COUNTER_
        Vector2Norm._VECTOR_2_NORM_COUNTER_ += 1

    def is_convex(self):
        return True

    def is_concave(self):
        return False

    def epigraph_conic_form(self):
        """
        Generate conic constraint for epigraph
            np.linalg.norm( np.array(self.args), ord=2) <= self.aux_var
        The coniclifts standard for the second order cone (of length n) is
            { (t,x) : x \in R^{n-1}, t \in R, || x ||_2 <= t }.
        """
        if self.aux_var is None:
            v = Variable(shape=(), name='_vec2norm_epi[' + str(self.id) + ']_')
            self.aux_var = v[()].scalar_variables()[0]
        m = len(self.args) + 1
        b = np.zeros(m,)
        A_rows, A_cols, A_vals = [0], [self.aux_var.id], [1]  # for first row
        for i, arg in enumerate(self.args):
            A_rows += (len(arg)-1) * [i + 1]
            for var, coeff in arg[:-1]:
                A_cols.append(var.id)
                A_vals.append(coeff)
            b[i+1] = arg[-1][1]
        K = [Cone('S', m)]
        A_rows = np.array(A_rows)
        return A_vals, A_rows, A_cols, b, K, self.aux_var

    def value(self):
        raise NotImplementedError()

