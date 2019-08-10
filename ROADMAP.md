# Planned changes to sageopt

When substantial effort is undertaken to change sageopt, or add new features, the plans and
rationales for those changes should be listed here.


## Add tests for constraint violations (coniclifts)

This is a low-priority task.

The ability to compute constraint violations was added pretty late in the coniclifts development process.
Linear equations and inequalities, and SAGE cones have tests. Should add tests for other
SetMembership constraints, and for some nonlinear atoms (such as vector2norm, or exp).

## Populate the design_notes folder.

This is a high-priority task. It can be done incrementally.

Files in the design_notes folder should explain the overall architecture of sageopt and its
various submodules (e.g. coniclifts). These files should serve as both a guide to those who
are trying to understand how sageopt works for the first time, and as a reference for people
who are already deeply familiar with certain aspects of sageopt. These documents should keep
track of "lessons learned" throughout the life of the sageopt project (e.g. "We used to do X,
which was nice for Y reasons, but created problems for Z, so now we do W.")


## Create a flexible backend, that can use either coniclifts, or cvxpy.

This is a high-priority task. It will require large, coordinated changes to sageopt.

An earlier version of sageopt (called "sigpy") used cvxpy as its backend for constructing SAGE
relaxations. We moved to a custom backend for a few reasons:
1. CVXPY had slow performance for compile-time.
2. CVXPY lacked functionality to track user-defined variables through to the end of the
   compilation process. Thus although low-level solver data could be accessed with cvxpy,
   there was no way to understand how this data mapped to the original problem variables.
3. CVXPY has a C++ backend and significant solver dependencies, which often create problems
   for users trying to install or run cvxpy.
4. I had an idea for a different architecture for a rewriting system of convex programs, and
   I wanted to test out that idea. I implemented that architecture in "coniclifts", and once
   coniclifts resolved the three problems above with cvxpy, I moved to a coniclifts backend.

All that said -- there are several features of cvxpy which are relevant to the goals of sageopt,
but that would be a terrible mess to implement with coniclifts. The list of such things is
likely going to grow with time. My time (and the time of others in the optimization community)
is much better spent helping cvxpy, rather than continuing to add features to coniclifts.

My "vision" for the rewriting system behind sageopt is roughly as follows.
1. Have the ability to run core functionality of sageopt with only coniclifts.
2. Have a submodule "cvxtensions" which adds functionality to cvxpy (by properly subclassing
   existing parts of cvxpy) that is important for sageopt.
3. Have the "relaxations" submodule contain a setting which allows the user to switch between
   coniclifts and cvxpy as desired. Possibly default to cvxpy if cvxpy is installed, but
   whether or not we do that depends on if cvxpy's compilation process is slower than coniclifts.

The third part in that vision is the fuzziest bit. I don't want to make the relaxations submodule
a mess of code that is hard to read and hard to maintain. In addition, it will be important to
make sure that the coniclifts API is aligned with the cvxpy API as best as possible.


## Add support for more solvers (coniclifts)

This is a medium-priority task. It can be done with virtually no changes to existing files. 

Once we have a cvxpy backend, we will have access to essentially all exponential-cone solvers
that might be useful for SAGE relaxations. Until then, we need to add more solver interfaces
to coniclifts. It should be easy to add support for both SCS and SuperSCS. 


## Add support for SDPs in MOSEK's coniclifts interface.

This is a low-priority task.

Coniclifts currently allows users to create linear matrix inequality constraints, but
existing solver interfaces do not allow these constraints. (So right now, a user can construct
an SDP, but cannot solve an SDP.)


## Add more sophisticated dimension reduction for SAGE cones

Suppose we want to represent a constraint "c is X-SAGE with respect to exponents alpha".
Often, there are many indices "k" where the k^th X-AGE cone w.r.t. alpha is simply the
nonnegative orthant.

If X is a cone, then it is easy to identify these indices:

find a nonzero vector x \in X so that (alpha - alpha[k,:]) @ x < 0.

When X is not a cone, we can check that

    min{ t : x in X, (alpha - alpha[k,:]) @ x <= t } = -\infty.

In order to add this dimension-reduction to sageopt, it will be necessary to:

1. Enable a CVXPY backend.
2. Create "constraint factories", which perform this dimension reduction once,
and allow it to be re-used across multiple desired constraints.

The CVXPY backend is necessary because coniclifts does not allow a user to create
and solve smaller optimization problems while in the middle of constructing a larger
optimization problem.

## Coniclifts: address global scope of Variable objects

Coniclifts Variables have a "generation" attribute: the value of a counter
which is incremented whenever the user calls "clear_variable_indices()".
Coniclifts does not support compiling Problems with Variables from different
generations. This is a huge limitation, and one that should be circumvented.

A possible solution (to consider later): Add an "index_mapping" argument to
the "conic_form()" function of Constraint objects. This would be a dictionary
that maps a ScalarVariable's "id" to a contiguous index which places that
ScalarVariable in the scope of the calling Problem. One difficulty here
is how epigraph variables are not known until mid-way in the compilation
process.