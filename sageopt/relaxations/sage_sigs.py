"""
   Copyright 2019 Riley John Murray

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
import numpy as np
import warnings
from sageopt import coniclifts as cl
from sageopt.symbolic.signomials import Signomial, is_feasible
from sageopt.relaxations import constraint_generators as con_gen
from sageopt.relaxations import symbolic_correspondences as sym_corr


def primal_sage_cone(sig, name, AbK):
    if AbK is None:
        con = cl.PrimalSageCone(sig.c, sig.alpha, name)
    else:
        A, b, K = AbK
        con = cl.PrimalGenSageCone(sig.c, sig.alpha, A, b, K, name)
    return con


def relative_dual_sage_cone(primal_sig, dual_var, name, AbK):
    if AbK is None:
        con = cl.DualSageCone(dual_var, primal_sig.alpha, name, primal_sig.c)
    else:
        A, b, K = AbK
        con = cl.DualGenSageCone(dual_var, primal_sig.alpha, A, b, K, name, primal_sig.c)
    return con


def sage_dual(f, ell=0, AbK=None):
    """
    :param f: a Signomial object.
    :param ell: a nonnegative integer
    :param AbK: None, or tuple of the form (A, b, K) defining a set X = { x : A @ x + b in K}.

    :return: a coniclifts Problem providing the dual formulation for f_{SAGE(X)}^{(ell)}, where
    X = R^n by default, but X = {x : A @ x + b in K} if AbK is not None.

    Notes:
        If f.n is not equal to A.shape[1], then we assume f.n < A.shape[1], and furthermore
        that the first "f.n" columns of A correspond (in order!) to the variables over which
        "f" is defined. Any remaining columns correspond to auxiliary variables needed to
        efficiently represent X.
    """
    f.remove_terms_with_zero_as_coefficient()
    # Signomial definitions (for the objective).
    t_mul = Signomial(f.alpha, np.ones(f.m)) ** ell
    lagrangian = f - cl.Variable(name='gamma')
    metadata = {'f': f, 'lagrangian': lagrangian, 'modulator': t_mul}
    lagrangian = lagrangian * t_mul
    f_mod = f * t_mul
    # C_SAGE^STAR (v must belong to the set defined by these constraints).
    v = cl.Variable(shape=(lagrangian.m, 1), name='v')
    con = relative_dual_sage_cone(lagrangian, v, name='Lagrangian SAGE dual constraint', AbK=AbK)
    constraints = [con]
    # Equality constraint (for the Lagrangian to be bounded).
    a = sym_corr.relative_coeff_vector(t_mul, lagrangian.alpha)
    a = a.reshape(a.size, 1)
    constraints.append(a.T @ v == 1)
    # Objective definition and problem creation.
    obj_vec = sym_corr.relative_coeff_vector(f_mod, lagrangian.alpha)
    obj = obj_vec.T @ v
    # Create coniclifts Problem
    prob = cl.Problem(cl.MIN, obj, constraints)
    prob.associated_data = metadata
    cl.clear_variable_indices()
    return prob


def sage_primal(f, ell=0, AbK=None, additional_cons=None):
    """
    :param f: a Signomial object.
    :param ell: a nonnegative integer
    :param AbK: None, or tuple of the form (A, b, K) defining a set X = { x : A @ x + b in K}.
    :param additional_cons: a list of coniclifts Constraint objects over the variables in f.c
    (unless you are working with SAGE polynomials, there likely won't be any of these).

    :return: a coniclifts Problem providing the primal formulation for f_{SAGE(X)}^{(ell)}, where
    X = R^(f.n) by default, but X = {x : A @ x + b in K} if AbK is not None.

    Unlike the sage_dual, this formulation can be stated in full generality without too much trouble.
    We define a multiplier signomial "t" (with the canonical choice t = Signomial(f.alpha, np.ones(f.m))),
    then return problem data representing

        max  gamma
        s.t.    f_mod.c in C_{SAGE}(f_mod.alpha, X)
        where   f_mod := (t ** ell) * (f - gamma).

    Our implementation of Signomial objects allows Variables in the coefficient vector c. As a result, the
    map from gamma to f_mod.c is an affine function that takes in a Variable and returns an Expression.
    This makes it very simple to represent "f_mod.c in C_{SAGE}(f_mod.alpha, X)" via coniclifts Constraints.

    Notes:
        If f.n is not equal to A.shape[1], then we assume f.n < A.shape[1], and furthermore
        that the first "f.n" columns of A correspond (in order!) to the variables over which
        "f" is defined. Any remaining columns correspond to auxiliary variables needed to
        efficiently represent X.
    """
    f.remove_terms_with_zero_as_coefficient()
    t = Signomial(f.alpha, np.ones(f.m))
    gamma = cl.Variable(name='gamma')
    s_mod = (f - gamma) * (t ** ell)
    s_mod.remove_terms_with_zero_as_coefficient()
    con = primal_sage_cone(s_mod, name=str(s_mod), AbK=AbK)
    constraints = [con]
    obj = gamma.as_expr()
    if additional_cons is not None:
        constraints += additional_cons
    prob = cl.Problem(cl.MAX, obj, constraints)
    cl.clear_variable_indices()
    return prob


def sage_feasibility(f, AbK=None, additional_cons=None):
    """
    :param f: a Signomial object
    :param AbK: None, or tuple of the form (A, b, K) defining a set X = { x : A @ x + b in K}.
    :param additional_cons: a list of coniclifts Constraint objects over the variables in f.c
    (unless you are working with SAGE polynomials, there likely won't be any of these).

    :return: coniclifts maximization Problem which is feasible iff f.c in C_{SAGE}(f.alpha, X),
    where X = R^(f.n) by default, but X = {x : A @ x + b in K} if AbK is not None.

    Notes:
        If f.n is not equal to A.shape[1], then we assume f.n < A.shape[1], and furthermore
        that the first "f.n" columns of A correspond (in order!) to the variables over which
        "f" is defined. Any remaining columns correspond to auxiliary variables needed to
        efficiently represent X.
    """
    f.remove_terms_with_zero_as_coefficient()
    con = primal_sage_cone(f, name=str(f), AbK=AbK)
    constraints = [con]
    if additional_cons is not None:
        constraints += additional_cons
    prob = cl.Problem(cl.MAX, cl.Expression([0]), constraints)
    cl.clear_variable_indices()
    return prob


def sage_multiplier_search(f, level=1, AbK=None):
    """
    :param f: a Signomial object
    :param level: a nonnegative integer; controls the complexity of the search space for SAGE multipliers.
    :param AbK: None, or a tuple of the form (A, b, K) defining a set X = { x : A @ x + b in K}.

    :return: a coniclifts Problem that is feasible iff f * mult is X-SAGE for some X-SAGE multiplier
    signomial "mult". X = R^(f.n) by default, but X = {x : A @ x + b in K} if AbK is not None.

    This function provides an alternative to moving up the SAGE hierarchy, for the goal of certifying
    nonnegativity of a signomial "f" over some convex set "X."  In general, the approach is to introduce
    a signomial

        mult = Signomial(alpha_hat, c_tilde)

    where the rows of alpha_hat are all level-wise sums of rows from f.alpha, and c_tilde is a coniclifts
    Variable defining a nonzero X-SAGE function. Then we check if f_mod := f * mult is X-SAGE for any
    choice of c_tilde.

    Notes:
        If f.n is not equal to A.shape[1], then we assume f.n < A.shape[1], and furthermore
        that the first "f.n" columns of A correspond (in order!) to the variables over which
        "f" is defined. Any remaining columns correspond to auxiliary variables needed to
        efficiently represent X.
    """
    f.remove_terms_with_zero_as_coefficient()
    constraints = []
    mult_alpha = hierarchy_e_k([f], k=level)
    c_tilde = cl.Variable(mult_alpha.shape[0], name='c_tilde')
    mult = Signomial(mult_alpha, c_tilde)
    constraints.append(cl.sum(c_tilde) >= 1)
    sig_under_test = mult * f
    con1 = primal_sage_cone(mult, name=str(mult), AbK=AbK)
    con2 = primal_sage_cone(sig_under_test, name=str(sig_under_test), AbK=AbK)
    constraints.append(con1)
    constraints.append(con2)
    prob = cl.Problem(cl.MAX, cl.Expression([0]), constraints)
    cl.clear_variable_indices()
    return prob


def constrained_sage_primal(f, gts, eqs, p=0, q=1, ell=0, AbK=None):
    """
    Construct the SAGE-(p, q, ell) primal problem for the signomial program

        inf{ f(x) : g(x) >= 0 for g in gts,
                    g(x) == 0 for g in eqs,
                    and x in X }

    where X = R^(f.n) by default, but X = {x : A @ x + b in K } if AbK is not None.

    :param f: a Signomial.
    :param gts: a list of Signomials.
    :param eqs: a list of Signomials.
    :param p: a nonnegative integer.
        Controls the complexity of Lagrange multipliers. p=0 corresponds to scalars.
    :param q: a positive integer.
        The number of folds applied to the constraints "gts" and "eqs". p=1 means "leave gts and eqs as-is."
    :param ell: a nonnegative integer.
        Controls the complexity of any modulator applied to the Lagrangian. ell=0 means that
        the Lagrangian must be SAGE. ell=1 means "tilde_L := modulator * Lagrangian" must be SAGE.
    :param AbK: None, or a tuple of the form (A, b, K) defining a set X = { x : A @ x + b in K}.

    :return: The primal form SAGE-(p, q, ell) relaxation for the given signomial program.

    Notes:
        If f.n is not equal to A.shape[1], then we assume f.n < A.shape[1], and furthermore
        that the first "f.n" columns of A correspond (in order!) to the variables over which
        "f" is defined. Any remaining columns correspond to auxiliary variables needed to
        efficiently represent X.
    """
    lagrangian, ineq_lag_mults, _, gamma = make_lagrangian(f, gts, eqs, p=p, q=q)
    metadata = {'lagrangian': lagrangian}
    if ell > 0:
        alpha_E_1 = hierarchy_e_k([f] + list(gts) + list(eqs), k=1)
        modulator = Signomial(alpha_E_1, np.ones(alpha_E_1.shape[0])) ** ell
        lagrangian = lagrangian * modulator
    else:
        modulator = Signomial({(0,) * f.n: 1})
    metadata['modulator'] = modulator
    # The Lagrangian (after possible multiplication, as above) must be a SAGE signomial.
    con = primal_sage_cone(lagrangian, name='Lagrangian is SAGE', AbK=AbK)
    constrs = [con]
    #  Lagrange multipliers (for inequality constraints) must be SAGE signomials.
    for i, (s_h, _) in enumerate(ineq_lag_mults):
        con_name = 'SAGE multiplier for signomial inequality # ' + str(i)
        con = primal_sage_cone(s_h, name=con_name, AbK=AbK)
        constrs.append(con)
    # Construct the coniclifts Problem.
    prob = cl.Problem(cl.MAX, gamma, constrs)
    prob.associated_data = metadata
    cl.clear_variable_indices()
    return prob


def constrained_sage_dual(f, gts, eqs, p=0, q=1, ell=0, AbK=None):
    """
    Construct the SAGE-(p, q, ell) dual problem for the signomial program

        inf{ f(x) : g(x) >= 0 for g in gts,
                    g(x) == 0 for g in eqs,
                    and x in X }

    where X = R^(f.n) by default, but X = {x : A @ x + b in K } if AbK is not None.

    :param f: a Signomial.
    :param gts: a list of Signomials.
    :param eqs: a list of Signomials.
    :param p: a nonnegative integer.
        Controls the complexity of Lagrange multipliers in the primal problem (p=0 corresponds to scalars),
        and in turn the complexity of constraints in this dual problem (p=0 corresponds to linear inequalities).
    :param q: a positive integer.
        The number of folds applied to the constraints "gts" and "eqs". p=1 means "leave gts and eqs as-is."
    :param ell: a nonnegative integer.
        Controls the complexity of any modulator applied to the Lagrangian in the primal problem.
        ell=0 means that the Lagrangian is unchanged / not modulated.
    :param AbK: None, or a tuple of the form (A, b, K) defining a set X = { x : A @ x + b in K}.

    :return: The dual form SAGE-(p, q, ell) relaxation for the given signomial program.

    Notes:
        If f.n is not equal to A.shape[1], then we assume f.n < A.shape[1], and furthermore
        that the first "f.n" columns of A correspond (in order!) to the variables over which
        "f" is defined. Any remaining columns correspond to auxiliary variables needed to
        efficiently represent X.
    """
    lagrangian, ineq_lag_mults, eq_lag_mults, _ = make_lagrangian(f, gts, eqs, p=p, q=q)
    metadata = {'lagrangian': lagrangian, 'f': f, 'gts': gts, 'eqs': eqs}
    if ell > 0:
        alpha_E_1 = hierarchy_e_k([f] + list(gts) + list(eqs), k=1)
        # ^ That's different than what I describe in the paper.
        # Really should just be alpha_E_1 = lagrangian.alpha
        modulator = Signomial(alpha_E_1, np.ones(alpha_E_1.shape[0])) ** ell
        lagrangian = lagrangian * modulator
        # ^ Some terms might be cancelling here? Possible that this function
        f = f * modulator
    else:
        modulator = Signomial({(0,) * f.n: 1})
    metadata['modulator'] = modulator
    # In primal form, the Lagrangian is constrained to be a SAGE signomial.
    # Introduce a dual variable "v" for this constraint.
    v = cl.Variable(shape=(lagrangian.m, 1), name='v')
    con = relative_dual_sage_cone(lagrangian, v, name='Lagrangian SAGE dual constraint', AbK=AbK)
    constraints = [con]
    for i, (s_h, h) in enumerate(ineq_lag_mults):
        # These generalized Lagrange multipliers "s_h" are SAGE signomials.
        # For each such multiplier, introduce an appropriate dual variable "v_h", along
        # with constraints over that dual variable.
        v_h = cl.Variable(name='v_' + str(h), shape=(s_h.m, 1))
        con_name = 'SAGE dual for signomial inequality # ' + str(i)
        con = relative_dual_sage_cone(s_h, v_h, name=con_name, AbK=AbK)
        constraints.append(con)
        h = h * modulator
        c_h = sym_corr.moment_reduction_array(s_h, h, lagrangian)
        constraints.append(c_h @ v == v_h)
    for s_h, h in eq_lag_mults:
        # These generalized Lagrange multipliers "s_h" are arbitrary signomials.
        # They dualize to homogeneous equality constraints.
        h = h * modulator
        c_h = sym_corr.moment_reduction_array(s_h, h, lagrangian)
        constraints.append(c_h @ v == 0)
    # Equality constraint (for the Lagrangian to be bounded).
    a = sym_corr.relative_coeff_vector(modulator, lagrangian.alpha)
    constraints.append(a.T @ v == 1)
    # Define the dual objective function.
    obj_vec = sym_corr.relative_coeff_vector(f, lagrangian.alpha)
    obj = obj_vec.T @ v
    # Return the coniclifts Problem.
    prob = cl.Problem(cl.MIN, obj, constraints)
    prob.associated_data = metadata
    cl.clear_variable_indices()
    return prob


def make_lagrangian(f, gts, eqs, p, q):
    """
    Given a problem

        inf_{x in X}{ f(x) : g(x) >= 0 for g in gts, g(x) == 0 for g in eqs },

    construct the q-fold constraints "folded_gts" and "folded_eqs," and the Lagrangian

        L = f - gamma - sum_{g in folded_gts} s_g * g - sum_{g in folded_eqs} z_g * g

    where gamma and the coefficients on Signomials s_g / z_g are coniclifts Variables.

    The values returned by this function are used to construct constrained SAGE relaxations.
    The basic primal SAGE relaxation is obtained by maximizing gamma, subject to the constraint
    that L and each s_g are SAGE functions. The dual SAGE relaxation is obtained by symbolically
    applying conic duality to the primal.

    :param f: a Signomial.
    :param gts: a list of Signomials.
    :param eqs: a list of Signomials.
    :param p: a nonnegative integer. Controls the complexity of s_g and z_g.
    :param q: a positive integer. The number of folds of constraints "gts" and "eqs".

    :return: L, ineq_dual_sigs, eq_dual_sigs, gamma.

        L : a Signomial object with coefficients as affine expressions of coniclifts Variables.

        ineq_dual_sigs : a list of pairs of Polynomial objects. If the pair (s1, s2) is in this list, then
            s1 is a generalized Lagrange multiplier to the constraint that s2(x) >= 0.

        eq_dual_sigs : a list of pairs of Signomial objects. If the pair (s1, s2) is in this list, then
            s1 is a generalized Lagrange multiplier to the constraint that s2(x) == 0.
            This return value is not accessed for primal-form SAGE relaxations.

        gamma : an unconstrained coniclifts Variable. This is the objective for primal-form SAGE relaxations,
            and induces a normalizing equality constraint in dual-form SAGE relaxations.
            This return value is not accessed for dual-form SAGE relaxations.
    """
    folded_gt = con_gen.up_to_q_fold_cons(gts, q)
    gamma = cl.Variable(name='gamma')
    L = f - gamma
    alpha_E_p = hierarchy_e_k([f] + list(gts) + list(eqs), k=p)
    ineq_dual_sigs = []
    for g in folded_gt:
        s_g_coeff = cl.Variable(name='s_' + str(g), shape=(alpha_E_p.shape[0],))
        s_g = Signomial(alpha_E_p, s_g_coeff)
        L -= s_g * g
        ineq_dual_sigs.append((s_g, g))
    eq_dual_sigs = []
    folded_eq = con_gen.up_to_q_fold_cons(eqs, q)
    for g in folded_eq:
        z_g_coeff = cl.Variable(name='z_' + str(g), shape=(alpha_E_p.shape[0],))
        z_g = Signomial(alpha_E_p, z_g_coeff)
        L -= z_g * g
        eq_dual_sigs.append((z_g, g))
    return L, ineq_dual_sigs, eq_dual_sigs, gamma


def generalized_sage_data(f, gts, eqs):
    # noinspection SpellCheckingInspection
    """
    :param f: objective signomial
    :param gts: inequality constraint signomials
    :param eqs: equality constraint signomials

    :return: "AbK" - either a tuple of length 3, or None. If a tuple of length 3, then the
    entries are (a sparse matrix, a 1darray, a list of coniclifts Cone objects).
    """
    x = cl.Variable(shape=(f.n,), name='x')
    cons = []
    conv_gt = con_gen.valid_posynomial_inequalities(gts)
    for g in conv_gt:
        nonconst_selector = np.ones(shape=(g.m,), dtype=bool)
        nonconst_selector[g.constant_location()] = False
        if g.m > 2:
            cst = g.c[~nonconst_selector]
            alpha = g.alpha[nonconst_selector, :]
            c = -g.c[nonconst_selector]
            expr = cl.weighted_sum_exp(c, alpha @ x)
            cons.append(expr <= cst)
        elif g.m == 2:
            expr = g.alpha[nonconst_selector, :] @ x
            cst = np.log(g.c[~nonconst_selector] / abs(g.c[nonconst_selector]))
            cons.append(expr <= cst)
        else:
            raise RuntimeError('Trivial (or infeasible) signomial constraint.')
    conv_eqs = con_gen.valid_monomial_equations(eqs)
    for g in conv_eqs:
        # g is of the form c1 - c2 * exp(a.T @ x) == 0, where c1, c2 > 0
        cst_loc = g.constant_location()
        non_cst_loc = 1 if cst_loc == 0 else 1
        rhs = np.log(g.c[cst_loc] / abs(g.c[non_cst_loc]))
        cons.append(g.alpha[non_cst_loc, :] @ x == rhs)
    if len(cons) > 0:
        A, b, K, sep_K, var_name_to_locs = cl.compile_constrained_system(cons)
        cl.clear_variable_indices()
        AbK = (A, b, K)
    else:
        AbK = None
    return AbK


def hierarchy_e_k(sigs, k):
    alpha_tups = sum([list(s.alpha_c.keys()) for s in sigs], [])
    alpha_tups = set(alpha_tups)
    s = Signomial(dict([(a, 1.0) for a in alpha_tups]))
    s = s ** k
    return s.alpha


def dual_solution_recovery(prob, diff_tol=1e-6, ineq_tol=1e-8, eq_tol=1e-6, exp_format=True):
    """
    One dangerous thing about this function, is that it assumes the dual solution is *actually feasible*.
    This assumption allows us to skip the check for membership in X = {x : A @ x + b in K},
    at least for solutions recovered from dual AGE cones. It does not allow us to skip this step
    for least-squares solutions, although this is something we do anyway.

    So, one way to move forward is to solve a feasibility problem for everything that passes "gts, eqs".
    Or rather- we'd solve the projection problem. Yeah, the projection problem makes more sense, especially
    since the description of X may need auxilliary variables, which we don't get from "mus", as I've
    implemented things...

    :param prob:
    :param diff_tol:
    :param ineq_tol:
    :param eq_tol:
    :param exp_format:
    :return:
    """
    con = prob.user_cons[0]
    if not con.name == 'Lagrangian SAGE dual constraint':
        raise RuntimeError('Unexpected first constraint in dual SAGE relaxation.')
    # Recover any constraints present in "prob"
    gts = []
    eqs = []
    if 'gts' in prob.associated_data:
        gts = prob.associated_data['gts']
        eqs = prob.associated_data['eqs']
    f = prob.associated_data['f']
    # Search for feasible solutions
    v = con.v.value()
    mus0 = _least_squares_solution_recovery(prob, con, v, gts, eqs, ineq_tol, eq_tol)
    mus1 = _dual_age_cone_solution_recovery(con, v, gts, eqs, ineq_tol, eq_tol)
    mus = mus0 + mus1
    if isinstance(con, cl.DualGenSageCone):
        A, b, K = con.A, con.b, con.K
        A = np.asarray(A)
        mus = [mu for mu in mus if _satisfies_AbK_constraints(A, b, K, mu, ineq_tol)]
    mus = np.hstack(mus)
    # Find the best solution(s) among the ones remaining
    obj_vals = f(mus)
    good_sols = np.nonzero(obj_vals - np.min(obj_vals) <= diff_tol)[0]
    good_mus = mus[:, good_sols]
    if not exp_format:
        good_mus = np.exp(good_mus)
    gaps = f(good_mus) - prob.value
    return good_mus, gaps


def _dual_age_cone_solution_recovery(con, v, gts, eqs, ineq_tol, eq_tol):
    mus = []
    for i, mu_i in con.mu_vars.items():
        val = mu_i.value()
        val = -val / v[i]
        val = val.reshape((-1, 1))  # make "val" an unambiguous column vector
        if is_feasible(val, gts, eqs, ineq_tol, eq_tol, exp_format=True):
            mus.append(val)
    return mus


def _least_squares_solution_recovery(prob, con, v, gts, eqs, ineq_tol, eq_tol):
    if not hasattr(con, 'alpha'):
        alpha = con.lifted_alpha[:, :con.n]
    else:
        alpha = con.alpha
    dummy_modulated_lagrangian = Signomial(alpha, np.ones(shape=(alpha.shape[0],)))
    dummy_modulated_lagrangian.alpha = alpha  # ensure that rows weren't permuted.
    lagrangian = prob.associated_data['lagrangian']
    modulator = prob.associated_data['modulator']
    M = sym_corr.moment_reduction_array(lagrangian, modulator, dummy_modulated_lagrangian)
    v_reduced = M @ v
    if isinstance(con, cl.DualGenSageCone):
        A, b, K = con.A, con.b, con.K
        A = np.asarray(A)
        # Now solve min{ || np.log(v_reduced) - alpha @ x || : A @ x + b in K }
        x = cl.Variable(shape=(A.shape[1],))
        t = cl.Variable(shape=(1,))
        cons = [cl.vector2norm(np.log(v_reduced) - lagrangian.alpha @ x[:con.n]) <= t, cl.ProductCone(A, x, b, K)]
        prob = cl.Problem(cl.MIN, t, cons)
        cl.clear_variable_indices()
        res = prob.solve(verbose=False)
        if res[0] == cl.SOLVED:
            mu_ls = x.value()[:con.n].reshape((-1, 1))
        else:
            warnings.warn('Constrained least-squares solution recovery failed, and has been skipped.')
            return []
    else:
        try:
            mu_ls = np.linalg.lstsq(lagrangian.alpha, np.log(v_reduced), rcond=None)[0].reshape((-1, 1))
        except np.linalg.linalg.LinAlgError:
            warnings.warn('Ordinary least-squares solution recovery failed, and has been skipped.')
            return []
    if is_feasible(mu_ls, gts, eqs, ineq_tol, eq_tol, exp_format=True):
        mus = [mu_ls]
    else:
        mus = []
    return mus


def _satisfies_AbK_constraints(A, b, K, mu, ineq_tol):
    x = cl.Variable(shape=(A.shape[1],))
    t = cl.Variable(shape=(1,))
    mu_flat = mu.ravel()
    cons = [cl.vector2norm(mu_flat - x[:mu.size]) <= t, cl.ProductCone(A, x, b, K)]
    prob = cl.Problem(cl.MIN, t, cons)
    cl.clear_variable_indices()
    res = prob.solve(verbose=False)
    if res[0] == cl.SOLVED and res[1] <= ineq_tol + 1e-8:
        return True
    else:
        return False
