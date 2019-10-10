# -----------------------------------------------------------------------------
# BSD 3-Clause License
#
# Copyright (c) 2019, Science and Technology Facilities Council.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# -----------------------------------------------------------------------------
# Authors: J. Henrichs, Bureau of Meteorology


''' Module containing py.test tests for dependency analysis.'''

from __future__ import print_function, absolute_import
import os
import pytest

from fparser.common.readfortran import FortranStringReader
from psyclone import nemo
from psyclone.core.access_info import VariablesAccessInfo
from psyclone.core.access_type import AccessType
from psyclone.psyGen import Assignment, IfBlock, Loop, PSyFactory
from psyclone.tests.utilities import get_invoke

# Constants
API = "nemo"
# Location of the Fortran files associated with these tests
BASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "test_files")


def test_assignment(parser):
    ''' Check that assignments set the right read/write accesses.
    '''
    reader = FortranStringReader('''program test_prog
                                 a = b
                                 c(i,j) = d(i,j+1)+e+f(x,y)
                                 c(i) = c(i) + 1
                                 d(i,j) = sqrt(e(i,j))
                                 end program test_prog''')
    ast = parser(reader)
    psy = PSyFactory(API).create(ast)
    schedule = psy.invokes.get("test_prog").schedule

    # Simple scalar assignment:  a = b
    scalar_assignment = schedule.children[0]
    assert isinstance(scalar_assignment, Assignment)
    var_accesses = VariablesAccessInfo()
    scalar_assignment.reference_accesses(var_accesses)
    # Test some test functions explicitly:
    assert var_accesses.is_written("a")
    assert not var_accesses.is_read("a")
    assert not var_accesses.is_written("b")
    assert var_accesses.is_read("b")

    # Array element assignment: c(i,j) = d(i,j+1)+e+f(x,y)
    array_assignment = schedule.children[1]
    assert isinstance(array_assignment, Assignment)
    var_accesses = VariablesAccessInfo()
    array_assignment.reference_accesses(var_accesses)
    assert str(var_accesses) == "c: WRITE, d: READ, e: READ, f: READ, "\
                                "i: READ, j: READ, x: READ, y: READ"

    # Increment operation: c(i) = c(i)+1
    increment_access = schedule.children[2]
    assert isinstance(increment_access, Assignment)
    var_accesses = VariablesAccessInfo()
    increment_access.reference_accesses(var_accesses)
    assert str(var_accesses) == "c: READ+WRITE, i: READ"

    # Using an intrinsic:
    sqrt_access = schedule.children[3]
    assert isinstance(sqrt_access, Assignment)
    var_accesses = VariablesAccessInfo()
    sqrt_access.reference_accesses(var_accesses)
    assert str(var_accesses) == "d: WRITE, e: READ, i: READ, j: READ"


def test_indirect_addressing(parser):
    ''' Check that we correctly handle indirect addressing, especially
    on the LHS. '''
    reader = FortranStringReader('''program test_prog
                                 g(h(i)) = a
                                 end program test_prog''')
    ast = parser(reader)
    psy = PSyFactory(API).create(ast)
    schedule = psy.invokes.get("test_prog").schedule

    indirect_addressing = schedule[0]
    assert isinstance(indirect_addressing, Assignment)
    var_accesses = VariablesAccessInfo()
    indirect_addressing.reference_accesses(var_accesses)
    assert str(var_accesses) == "a: READ, g: WRITE, h: READ, i: READ"


def test_double_variable_lhs(parser):
    ''' A variable on the LHS of an assignment must only occur once,
    which is a restriction of PSyclone.

    '''
    reader = FortranStringReader('''program test_prog
                                 g(g(1)) = 1
                                 end program test_prog''')
    ast = parser(reader)
    psy = PSyFactory(API).create(ast)
    schedule = psy.invokes.get("test_prog").schedule

    indirect_addressing = schedule[0]
    assert isinstance(indirect_addressing, Assignment)
    var_accesses = VariablesAccessInfo()
    from psyclone.parse.utils import ParseError
    with pytest.raises(ParseError) as err:
        indirect_addressing.reference_accesses(var_accesses)
    assert "The variable 'g' appears more than once on the left-hand side "\
           "of an assignment." in str(err)


def test_if_statement(parser):
    ''' Tests handling an if statement
    '''
    reader = FortranStringReader('''program test_prog
                                 if (a .eq. b) then
                                    p(i) = q(i)
                                 else
                                   q(i) = r(i)
                                 endif
                                 end program test_prog''')
    ast = parser(reader)
    psy = PSyFactory(API).create(ast)
    schedule = psy.invokes.get("test_prog").schedule

    if_stmt = schedule.children[0]
    assert isinstance(if_stmt, IfBlock)
    var_accesses = VariablesAccessInfo()
    if_stmt.reference_accesses(var_accesses)
    assert str(var_accesses) == "a: READ, b: READ, i: READ, p: WRITE, "\
                                "q: READ+WRITE, r: READ"
    # Test that the two accesses to 'q' indeed show up as
    q_accesses = var_accesses["q"].all_accesses
    assert len(q_accesses) == 2
    assert q_accesses[0].access_type == AccessType.READ
    assert q_accesses[1].access_type == AccessType.WRITE
    assert q_accesses[0].location < q_accesses[1].location


@pytest.mark.xfail(reason="Calls in the NEMO API are not yet supported #446")
def test_call(parser):
    ''' Check that we correctly handle a call in a program '''
    reader = FortranStringReader('''program test_prog
                                 call sub(a,b)
                                 end program test_prog''')
    ast = parser(reader)
    psy = PSyFactory(API).create(ast)
    schedule = psy.invokes.get("test_prog").schedule

    code_block = schedule.children[0]
    call_stmt = code_block.statements[0]
    var_accesses = VariablesAccessInfo()
    call_stmt.reference_accesses(var_accesses)
    assert str(var_accesses) == "a: UNKNOWN, b: UNKNOWN"


def test_do_loop(parser):
    ''' Check the handling of do loops.
    '''
    reader = FortranStringReader('''program test_prog
                                 do jj=1, n
                                    do ji=1, 10
                                       s(ji, jj)=t(ji, jj)+1
                                    enddo
                                 enddo
                                 end program test_prog''')
    ast = parser(reader)
    psy = PSyFactory(API).create(ast)
    schedule = psy.invokes.get("test_prog").schedule

    do_loop = schedule.children[0]
    assert isinstance(do_loop, nemo.NemoLoop)
    var_accesses = VariablesAccessInfo()
    do_loop.reference_accesses(var_accesses)
    assert str(var_accesses) == "ji: READ+WRITE, jj: READ+WRITE, n: READ, "\
                                "s: WRITE, t: READ"


@pytest.mark.xfail(reason="Implicit loops are not supported. TODO #440")
def test_nemo_implicit_loop(parser):
    ''' Check the handling of ImplicitLoops access information.
    '''
    reader = FortranStringReader('''program test_prog
                                 do jj=1, n
                                    s(:, jj)=t(:, jj)+a
                                 enddo
                                 end program test_prog''')
    ast = parser(reader)
    psy = PSyFactory(API).create(ast)
    schedule = psy.invokes.get("test_prog").schedule

    do_loop = schedule.children[0]
    assert isinstance(do_loop, nemo.NemoLoop)
    var_accesses = VariablesAccessInfo()
    do_loop.reference_accesses(var_accesses)
    assert str(var_accesses) == "jj: READ+WRITE, n: READ, a: READ"


def test_nemo_implicit_loop_partial(parser):
    ''' Check the handling of ImplicitLoops access information.
    '''
    # TODO #440: Same as the test above but does not check the
    # variables in the implicit loop construct, this test can
    # be deleted when the issue is fixed and the above test
    # passes.
    reader = FortranStringReader('''program test_prog
                                 do jj=1, n
                                    s(:, jj)=t(:, jj)+a
                                 enddo
                                 end program test_prog''')
    ast = parser(reader)
    psy = PSyFactory(API).create(ast)
    schedule = psy.invokes.get("test_prog").schedule

    do_loop = schedule.children[0]
    assert isinstance(do_loop, nemo.NemoLoop)
    var_accesses = VariablesAccessInfo()
    do_loop.reference_accesses(var_accesses)
    assert str(var_accesses) == "jj: READ+WRITE, n: READ"  # a is missing


@pytest.mark.xfail(reason="Gocean loops boundaries are strings #440")
def test_goloop():
    ''' Check the handling of non-NEMO do loops.
    TODO #440: Does not work atm, GOLoops also have start/stop as
    strings, which are even not defined. Only after genCode is called will
    they be defined.
    '''

    _, invoke = get_invoke("single_invoke_two_kernels_scalars.f90",
                           "gocean1.0", name="invoke_0")
    do_loop = invoke.schedule.children[0]
    assert isinstance(do_loop, Loop)
    var_accesses = VariablesAccessInfo()
    do_loop.reference_accesses(var_accesses)
    assert str(var_accesses) == ": READ, a_scalar: READ, i: READ+WRITE, "\
                                "j: READ+WRITE, " "ssh_fld: READ+WRITE, "\
                                "tmask: READ"
    # TODO #440: atm the return value starts with:  ": READ, cu_fld: WRITE ..."
    # The empty value is caused by not having start, stop, end of the loop
    # defined at this stage.


def test_goloop_partially():
    ''' Check the handling of non-NEMO do loops.
    TODO #440: This test is identical to test_goloop above, but it asserts in a
    way that works before #440 is fixed, so that we make sure we test the rest
    of the gocean variable access handling.
    '''
    _, invoke = get_invoke("single_invoke_two_kernels_scalars.f90",
                           "gocean1.0", name="invoke_0")
    do_loop = invoke.schedule.children[0]
    assert isinstance(do_loop, Loop)

    # The third argument is GO_GRID_X_MAX_INDEX, which is scalar
    assert do_loop.args[2].is_scalar()
    # The fourth argument is GO_GRID_MASK_T, which is an array
    assert not do_loop.args[3].is_scalar()

    var_accesses = VariablesAccessInfo()
    do_loop.reference_accesses(var_accesses)
    assert "a_scalar: READ, i: READ+WRITE, j: READ+WRITE, "\
           "ssh_fld: READWRITE, ssh_fld%grid%subdomain%internal%xstop: READ, "\
           "ssh_fld%grid%tmask: READ" in str(var_accesses)


def test_dynamo():
    '''Test the handling of a dynamo0.3 loop. Note that the variable accesses
    are reported based on the user's point of view, not the code actually
    created by PSyclone, e.g. it shows a dependency on 'some_field', but not
    on some_field_proxy etc. Also the dependency is at this stage taken
    from the kernel metadata, not the actual kernel usage.
    '''
    from psyclone.parse.algorithm import parse
    _, info = parse(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "test_files", "dynamo0p3",
                                 "1_single_invoke.f90"),
                    api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=False).create(info)
    invoke = psy.invokes.get('invoke_0_testkern_type')
    schedule = invoke.schedule

    var_accesses = VariablesAccessInfo()
    schedule.reference_accesses(var_accesses)
    assert str(var_accesses) == "a: READ, cell: READ+WRITE, f1: WRITE, "\
        "f2: READ, m1: READ, m2: READ"


def test_location(parser):
    '''Test if the location assignment is working, esp. if each new statement
    gets a new location, but accesses in the same statement have the same
    location.
    '''

    reader = FortranStringReader('''program test_prog
                                 a = b
                                 if (a .eq. b) then
                                    p(i) = q(i)
                                 else
                                   q(i) = r(i)
                                 endif
                                 a = b
                                 do jj=1, n
                                    do ji=1, 10
                                       s(ji, jj)=t(ji, jj)+1
                                    enddo
                                 enddo
                                 a = b
                                 x = x + 1
                                 end program test_prog''')
    ast = parser(reader)
    psy = PSyFactory(API).create(ast)
    schedule = psy.invokes.get("test_prog").schedule

    var_accesses = VariablesAccessInfo()
    schedule.reference_accesses(var_accesses)
    # Test accesses for a:
    a_accesses = var_accesses["a"].all_accesses
    assert a_accesses[0].location == 0
    assert a_accesses[1].location == 1
    assert a_accesses[2].location == 6
    assert a_accesses[3].location == 12

    # b should have the same locations as a:
    b_accesses = var_accesses["b"].all_accesses
    assert len(a_accesses) == len(b_accesses)
    for (index, access) in enumerate(a_accesses):
        assert b_accesses[index].location == access.location

    q_accesses = var_accesses["q"].all_accesses
    assert q_accesses[0].location == 2
    assert q_accesses[1].location == 4

    # Test jj for the loop statement. Note that 'jj' has one read and
    # one write access for the DO statement
    jj_accesses = var_accesses["jj"].all_accesses
    assert jj_accesses[0].location == 7
    assert jj_accesses[1].location == 7
    assert jj_accesses[2].location == 9
    assert jj_accesses[3].location == 9

    ji_accesses = var_accesses["ji"].all_accesses
    assert ji_accesses[0].location == 8
    assert ji_accesses[1].location == 8
    assert ji_accesses[2].location == 9
    assert ji_accesses[3].location == 9

    # Verify that x=x+1 shows the READ access before the write access
    x_accesses = var_accesses["x"].all_accesses    # x=x+1
    assert x_accesses[0].access_type == AccessType.READ
    assert x_accesses[1].access_type == AccessType.WRITE
    assert x_accesses[0].location == x_accesses[1].location


def test_user_defined_variables(parser):
    ''' Test reading and writing to user defined variables, which
    is only partially supported atm.
    '''
    # TODO #363: this uses a work around for user defined types atm.
    reader = FortranStringReader('''program test_prog
                                       a%b%c(ji, jj) = d
                                       e%f = d
                                    end program test_prog''')
    prog = parser(reader)
    psy = PSyFactory("nemo", distributed_memory=False).create(prog)
    loops = psy.invokes.get("test_prog").schedule

    var_accesses = VariablesAccessInfo()
    loops.reference_accesses(var_accesses)
    assert var_accesses["a % b % c"].is_array()
    assert not var_accesses["e % f"].is_array()


def test_math_equal(parser):
    '''Tests the math_equal function of nodes in the PSyIR.'''

    # A dummy program to easily create the PSyIR for the
    # expressions we need. We just take the RHS of the assignments
    reader = FortranStringReader('''program test_prog
                                    x = a                 !  0
                                    x = a                 !  1
                                    x = b                 !  2
                                    x = a+12*b*sin(c)     !  3
                                    x = 12*b*sin(c)+a     !  4
                                    x = i+j               !  5
                                    x = j+i               !  6
                                    x = i-j               !  7
                                    x = j-i               !  8
                                    x = max(1, 2, 3, 4)   !  9
                                    x = max(1, 2, 3)      ! 10
                                    x = a(1,2)            ! 11
                                    x = i+j+k             ! 12
                                    x = j+i+k             ! 13
                                    end program test_prog
                                 ''')
    prog = parser(reader)
    psy = PSyFactory("nemo", distributed_memory=False).create(prog)
    schedule = psy.invokes.get("test_prog").schedule

    # Compare a and a
    exp0 = schedule[0].rhs
    exp1 = schedule[1].rhs
    assert exp0.math_equal(exp1)

    # Different node types: assignment and expression
    assert not schedule[0].math_equal(exp1)

    # Compare a and b
    assert not exp1.math_equal(schedule[2].rhs)

    # Compare a+12*b... and 12*b...+a - both commutative and
    # complex expression
    assert schedule[3].rhs.math_equal(schedule[4].rhs)

    # Compare i+j and j+i - we do support _simple_ commutative changes:
    exp5 = schedule[5].rhs
    exp6 = schedule[6].rhs
    assert exp5.math_equal(exp6)

    # Compare i-j and j-i
    exp7 = schedule[7].rhs
    assert not exp7.math_equal(schedule[8].rhs)

    # Same node type, but different number of children
    # max(1, 2, 3, 4) and max(1, 2, 3)
    exp9 = schedule[9].rhs
    assert not exp9.math_equal(schedule[10].rhs)

    # Compare a and a(1,2), which triggers the recursion in Reference
    # to be false.
    assert not exp0.math_equal(schedule[11].rhs)

    # Compare i+j and max(1,2,3,4) to trigger different types
    # in the recursion in BinaryOperator
    assert not exp5.math_equal(exp9)

    # Different operator: j+i vs i-j. Do not compare
    # i+j with i-j, since this will not trigger the
    # additional tests in commutative law handling
    assert not exp6.math_equal(exp7)

    # i+j+k and j+i+k are the same - note that i and j are
    # on the same node, since the expression is stored as
    # (i+j)+j. See #533 and test_math_equal_limitations
    exp12 = schedule[12].rhs
    assert exp12.math_equal(schedule[13].rhs)


@pytest.mark.xfail(reason="Limitation when using commutative law - #533")
def test_math_equal_limitations(parser):
    '''Shows that the current math_equal implementation can not
    detect that i+j+k and i+k+j are the same'''

    # A dummy program to easily create the PSyIR for the
    # expressions we need. We just take the RHS of the assignments
    reader = FortranStringReader('''program test_prog
                                    x = i+j+k
                                    x = i+k+j
                                    end program test_prog
                                 ''')
    prog = parser(reader)
    psy = PSyFactory("nemo", distributed_memory=False).create(prog)
    schedule = psy.invokes.get("test_prog").schedule

    # Compare i+j+k and i+k+j - they should be equal, but due to
    # TODO #533 it is not detected.
    exp0 = schedule[0].rhs
    exp1 = schedule[1].rhs
    assert exp0.math_equal(exp1)
