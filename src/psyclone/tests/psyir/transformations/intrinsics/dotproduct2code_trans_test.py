# -----------------------------------------------------------------------------
# BSD 3-Clause License
#
# Copyright (c) 2022, Science and Technology Facilities Council
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
# Author: R. W. Ford, STFC Daresbury Lab

'''Module containing tests for the DotProduct2CodeTrans
transformation.

'''
import pytest

from psyclone.psyir.nodes import BinaryOperation, Literal
from psyclone.psyir.symbols import REAL_TYPE
from psyclone.psyir.transformations import TransformationError
from psyclone.psyir.transformations.intrinsics import dotproduct2code_trans
from psyclone.psyir.transformations.intrinsics.dotproduct2code_trans import \
    DotProduct2CodeTrans, _get_array_bound
from psyclone.tests.utilities import Compile


# Utilities

def check_validate(code, expected, fortran_reader, index=0):
    '''Utility function that takes Fortran code that is unsupported by the
    DotProduct2CodeTrans transformation and checks that the expected
    exception is raised when the validate function is applied.

    :param str code: the tangent linear code stored in a string.
    :param str expected: the expected exception text.
    :param fortran_reader: converts Fortran into PSyIR.
    :type fortran_reader: :py:class:`psyclone.psyir.frontend.fortran`
    :param integer index: specifies which binaryoperation to check in \
        code order. Defaults to 0 (which is the first).

    '''
    psyir = fortran_reader.psyir_from_source(code)
    dot_product = psyir.walk(BinaryOperation)[index]
    assert dot_product.operator == BinaryOperation.Operator.DOT_PRODUCT
    trans = DotProduct2CodeTrans()
    with pytest.raises(TransformationError) as info:
        trans.validate(dot_product)
    assert expected in str(info.value)


def check_trans(code, expected, fortran_reader, fortran_writer, tmpdir,
                index=0):
    '''Utility function that takes fortran code and checks that the
    expected code is produced when the DotProduct2CodeTrans
    transformation is applied. The code is also checked to see if it
    will compile.

    :param str code: the tangent linear code stored in a string.
    :param str expected: the expected adjoint code stored in a string.
    :param fortran_reader: converts Fortran into PSyIR.
    :type fortran_reader: :py:class:`psyclone.psyir.frontend.fortran`
    :param fortran_writer: converts PSyIR into Fortran.
    :type fortran_writer: :py:class:`psyclone.psyir.backend.fortran`
    :param tmpdir: path to a test-specific temporary directory in \
        which to test compilation.
    :type tmpdir: :py:class:`py._path.local.LocalPath`
    :param integer index: specifies which binaryoperation to check in \
        code order. Defaults to 0 (which is the first).

    '''
    psyir = fortran_reader.psyir_from_source(code)
    dot_product = psyir.walk(BinaryOperation)[index]
    assert dot_product.operator == BinaryOperation.Operator.DOT_PRODUCT
    trans = DotProduct2CodeTrans()
    trans.apply(dot_product)
    result = fortran_writer(psyir)
    assert expected in result
    assert Compile(tmpdir).string_compiles(result)


# _get_array_bound function

def test_bound_error(fortran_writer):
    '''Test that the expected exception is raised if both arguments are
    not references to arrays.

    '''
    with pytest.raises(TransformationError) as info:
        _get_array_bound(Literal("1.0", REAL_TYPE), Literal("2.0", REAL_TYPE),
                         fortran_writer)
    assert ("DotProduct2CodeTrans._get_array_bound requires at least one of "
            "the dotproduct arguments to be an array but found '1.0' and "
            "'2.0'." in str(info.value))


@pytest.mark.parametrize("dim1,dim2", [("2:10", "2:10"), (":", "2:10"),
                                       ("2:10", ":")])
def test_bound_explicit(fortran_reader, fortran_writer, dim1, dim2):
    '''Test that explicit bounds are returned if at least one argument is
    declared with explicit bounds.

    '''
    code = (
        f"subroutine dot_product_test(v1,v2)\n"
        f"real,intent(in) :: v1({dim1}), v2({dim2})\n"
        f"real :: result\n"
        f"result = dot_product(v1,v2)\n"
        f"end subroutine\n")
    psyir = fortran_reader.psyir_from_source(code)
    dot_product = psyir.walk(BinaryOperation)[0]
    assert dot_product.operator == BinaryOperation.Operator.DOT_PRODUCT
    lower, upper, step = _get_array_bound(
        dot_product.children[0], dot_product.children[1], fortran_writer)
    assert lower.value == '2'
    assert upper.value == '10'
    assert step.value == '1'


def test_bound_unknown(fortran_reader, fortran_writer):
    '''Test that range bounds are returned if neither argument is declared
    with explicit bounds.

    '''
    code = (
        f"subroutine dot_product_test(v1,v2)\n"
        f"real,intent(in) :: v1(:), v2(:)\n"
        f"real :: result\n"
        f"result = dot_product(v1,v2)\n"
        f"end subroutine\n")
    psyir = fortran_reader.psyir_from_source(code)
    dot_product = psyir.walk(BinaryOperation)[0]
    assert dot_product.operator == BinaryOperation.Operator.DOT_PRODUCT
    lower, upper, step = _get_array_bound(
        dot_product.children[0], dot_product.children[1], fortran_writer)
    assert fortran_writer(lower) == 'LBOUND(v1, 1)'
    assert fortran_writer(upper) == 'UBOUND(v1, 1)'
    assert step.value == '1'


# DotProduct2CodeTrans class init method

def test_initialise():
    '''Check that the class DotProduct2CodeTrans behaves as expected when
    an instance of the class is created. Note, this also tests that
    the parent constructor is also called as this sets the name and
    value of __str__.

    '''
    trans = DotProduct2CodeTrans()
    assert trans._operator_name == "DOTPRODUCT"
    assert (str(trans) == "Convert the PSyIR DOTPRODUCT intrinsic to "
            "equivalent PSyIR code.")
    assert trans.name == "Dotproduct2CodeTrans"


# DotProduct2CodeTrans class validate method

def test_validate_super():
    '''Test that the DotProduct2CodeTrans validate method calls the validate
    method of the parent class.

    '''
    trans = DotProduct2CodeTrans()
    with pytest.raises(TransformationError) as info:
        trans.validate(None)
    assert ("The supplied node argument is not a DOTPRODUCT operator, found "
            "'NoneType'." in str(info.value))


def test_validate_references(fortran_reader):
    '''Test that the DotProduct2CodeTrans validate method produces the
    expected exception when at least one of the arguments is not an
    array. In this case it is a matmul intrinsic.

    '''
    code = (
        f"subroutine dot_product_test(v1,v2,a3)\n"
        f"real,intent(in) :: v1(:), v2(:), a3(:,:)\n"
        f"real :: result\n"
        f"result = dot_product(matmul(a3,v1),v2)\n"
        f"end subroutine\n")
    expected = (
        "The DotProduct2CodeTrans transformation only supports the "
        "transformation of a dotproduct intrinsic if its arguments "
        "are arrays, but found MATMUL(a3, v1) in "
        "DOT_PRODUCT(MATMUL(a3, v1), v2)")
    check_validate(code, expected, fortran_reader)


def test_validate_1d_array(fortran_reader):
    '''Test that the DotProduct2CodeTrans validate method produces the
    expected exception when at least one of the arguments does not use
    array slice notation but is not known to be a 1D array.

    '''
    code = (
        f"subroutine dot_product_test(a1,a2)\n"
        f"real,intent(in) :: a1(:,:), a2(:,:)\n"
        f"real :: result\n"
        f"result = dot_product(a1,a2)\n"
        f"end subroutine\n")
    expected = (
        "The DotProduct2CodeTrans transformation only supports the "
        "transformation of a dotproduct intrinsic with an argument not "
        "containing an array slice if the argument is a 1D array, but "
        "found a1 in DOT_PRODUCT(a1, a2).")
    check_validate(code, expected, fortran_reader)


def test_validate_array_slice_dim1(fortran_reader):
    '''Test that the DotProduct2CodeTrans validate method produces the
    expected exception when at least one of the arguments uses array
    slice notation but the array slice is not used in the the first
    dimension of the array.

    '''
    code = (
        f"subroutine dot_product_test(a1,a2)\n"
        f"real,intent(in) :: a1(:,:), a2(:,:)\n"
        f"real :: result\n"
        f"result = dot_product(a1(:,1),a2(1,:))\n"
        f"end subroutine\n")
    expected = (
        "The DotProduct2CodeTrans transformation only supports the "
        "transformation of a dotproduct intrinsic with an argument "
        "containing an array slice if the array slice is for the 1st "
        "dimension of the array, but found a2(1,:) in "
        "DOT_PRODUCT(a1(:,1), a2(1,:)).")
    check_validate(code, expected, fortran_reader)


def test_validate_array_full_slice(fortran_reader):
    '''Test that the DotProduct2CodeTrans validate method produces the
    expected exception when at least one of the arguments uses array
    slice notation but the array slice is not for the full range of
    the dimension.

    '''
    code = (
        f"subroutine dot_product_test(a1,a2)\n"
        f"real,intent(in) :: a1(:,:), a2(:,:)\n"
        f"real :: result\n"
        f"result = dot_product(a1(2:4,1),a2(:,10))\n"
        f"end subroutine\n")
    expected = (
        "The DotProduct2CodeTrans transformation only supports the "
        "transformation of a dotproduct intrinsic with an argument not "
        "an array slice if the argument is for the 1st dimension of "
        "the array and is for the full range of that dimension, but "
        "found a1(2:4,1) in DOT_PRODUCT(a1(2:4,1), a2(:,10)).")
    check_validate(code, expected, fortran_reader)


def test_validate_real(fortran_reader):
    '''Test that the DotProduct2CodeTrans validate method raises the
    expected exception if the datatype of the arguments is not
    real.

    '''
    code = (
        f"subroutine dot_product_test(v1,v2)\n"
        f"integer,intent(in) :: v1(:), v2(:)\n"
        f"integer :: result\n"
        f"result = dot_product(v1,v2)\n"
        f"end subroutine\n")
    expected = (
        "The DotProduct2CodeTrans transformation only supports arrays of "
        "real data, but found v1 of type INTEGER in DOT_PRODUCT(v1, v2).")
    check_validate(code, expected, fortran_reader)


def test_validate_get_array_bound(monkeypatch, fortran_reader):
    '''Test that the DotProduct2CodeTrans validate method calls the
    _get_array_bound method.

    '''
    code = (
        f"subroutine dot_product_test(v1,v2)\n"
        f"real,intent(in) :: v1(:), v2(:)\n"
        f"real :: result\n"
        f"result = dot_product(v1,v2)\n"
        f"end subroutine\n")
    expected = "Transformation Error: dummy"

    def dummy(_1, _2, _3):
        '''Utility used to raise the required exception.'''
        raise TransformationError("dummy")

    monkeypatch.setattr(dotproduct2code_trans, "_get_array_bound", dummy)
    check_validate(code, expected, fortran_reader)


# DotProduct2CodeTrans class apply method

def test_apply_calls_validate():
    '''Test that the DotProduct2CodeTrans apply method calls the validate
    method.

    '''
    trans = DotProduct2CodeTrans()
    with pytest.raises(TransformationError) as info:
        trans.apply(None)
    assert ("The supplied node argument is not a DOTPRODUCT operator, found "
            "'NoneType'." in str(info.value))


@pytest.mark.parametrize("dim1,dim2", [("10", "10"), (":", "10"), ("10", ":")])
def test_apply_known_dims(tmpdir, fortran_reader, fortran_writer, dim1, dim2):
    '''Test that the DotProduct2CodeTrans apply method produces the
    expected PSyIR when at least one of the vectors has a known
    dimension.

    '''
    code = (
        f"subroutine dot_product_test(v1,v2)\n"
        f"real,intent(in) :: v1({dim1}), v2({dim2})\n"
        f"real :: result\n"
        f"result = dot_product(v1,v2)\n"
        f"end subroutine\n")
    expected = (
        "  integer :: i\n"
        "  real :: res_dot_product\n\n"
        "  res_dot_product = 0.0\n"
        "  do i = 1, 10, 1\n"
        "    res_dot_product = res_dot_product + v1(i) * v2(i)\n"
        "  enddo\n"
        "  result = res_dot_product\n\n")
    check_trans(code, expected, fortran_reader, fortran_writer, tmpdir)


def test_apply_unknown_dims(tmpdir, fortran_reader, fortran_writer):
    '''Test that the DotProduct2CodeTrans apply method produces the
    expected PSyIR when neither of the vectors have a known size.

    '''
    code = (
        "subroutine dot_product_test(v1,v2)\n"
        "real,intent(in) :: v1(:), v2(:)\n"
        "real :: result\n"
        "result = dot_product(v1,v2)\n"
        "end subroutine\n")
    expected = (
        "  integer :: i\n"
        "  real :: res_dot_product\n\n"
        "  res_dot_product = 0.0\n"
        "  do i = LBOUND(v1, 1), UBOUND(v1, 1), 1\n"
        "    res_dot_product = res_dot_product + v1(i) * v2(i)\n"
        "  enddo\n"
        "  result = res_dot_product\n\n")
    check_trans(code, expected, fortran_reader, fortran_writer, tmpdir)


def test_apply_multi_rhs(tmpdir, fortran_reader, fortran_writer):
    '''Test that the DotProduct2CodeTrans apply method produces the
    expected PSyIR when the expression on the rhs contains more than
    just the DOT_PRODUCT.

    '''
    code = (
        "subroutine dot_product_test(v1,v2)\n"
        "real,intent(in) :: v1(10), v2(:)\n"
        "real :: a, b, c, result\n"
        "result = a + b*dot_product(v1,v2) + c\n"
        "end subroutine\n")
    expected = (
        "  integer :: i\n"
        "  real :: res_dot_product\n\n"
        "  res_dot_product = 0.0\n"
        "  do i = 1, 10, 1\n"
        "    res_dot_product = res_dot_product + v1(i) * v2(i)\n"
        "  enddo\n"
        "  result = a + b * res_dot_product + c\n\n")
    check_trans(code, expected, fortran_reader, fortran_writer, tmpdir,
                index=3)


@pytest.mark.parametrize("arg1,arg2", [("", "(:)"), ("(:)", ""),
                                       ("(:)", "(:)")])
def test_apply_array_notation(
        tmpdir, fortran_reader, fortran_writer, arg1, arg2):
    '''Test that the DotProduct2CodeTrans apply method produces the
    expected PSyIR when array notation is used on the rhs by one or
    both of the dot_product arguments.

    '''
    code = (
        f"subroutine dot_product_test(v1,v2)\n"
        f"real,intent(in) :: v1(:), v2(:)\n"
        f"real :: result\n"
        f"result = dot_product(v1{arg1},v2{arg2})\n"
        f"end subroutine\n")
    expected = (
        "  integer :: i\n"
        "  real :: res_dot_product\n\n"
        "  res_dot_product = 0.0\n"
        "  do i = LBOUND(v1, 1), UBOUND(v1, 1), 1\n"
        "    res_dot_product = res_dot_product + v1(i) * v2(i)\n"
        "  enddo\n"
        "  result = res_dot_product\n\n")
    check_trans(code, expected, fortran_reader, fortran_writer, tmpdir)


@pytest.mark.parametrize("arg1,arg2,res1,res2",
                         [("(:,n)", "(:,1)", "(i,n)", "(i,1)")])
def test_apply_extra_dims(tmpdir, fortran_reader, fortran_writer, arg1, arg2,
                          res1, res2):
    '''Test that the DotProduct2CodeTrans apply method produces the
    expected PSyIR when the supplied dot_product arguments are arrays
    with different dimensions having array notation.

    '''
    code = (
        f"subroutine dot_product_test(v1,v2)\n"
        f"integer :: n\n"
        f"real,intent(in) :: v1(:,:), v2(:,:)\n"
        f"real :: result\n"
        f"result = dot_product(v1{arg1},v2{arg2})\n"
        f"end subroutine\n")
    expected = (
        f"  integer :: i\n"
        f"  real :: res_dot_product\n\n"
        f"  res_dot_product = 0.0\n"
        f"  do i = LBOUND(v1, 1), UBOUND(v1, 1), 1\n"
        f"    res_dot_product = res_dot_product + v1{res1} * v2{res2}\n"
        f"  enddo\n"
        f"  result = res_dot_product\n\n")
    check_trans(code, expected, fortran_reader, fortran_writer, tmpdir)
