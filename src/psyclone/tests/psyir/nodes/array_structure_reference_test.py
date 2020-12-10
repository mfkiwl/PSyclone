# -----------------------------------------------------------------------------
# BSD 3-Clause License
#
# Copyright (c) 2020, Science and Technology Facilities Council.
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
# Author: A. R. Porter, STFC Daresbury Lab
# -----------------------------------------------------------------------------

''' This module contains pytest tests for the ArrayStructureReference
    class. '''

from __future__ import absolute_import
import pytest
from psyclone.tests.utilities import check_links
from psyclone.psyir import symbols, nodes


def test_asr_create():
    ''' Check the create method. '''
    region_type = symbols.StructureType.create([
        ("startx", symbols.INTEGER_TYPE, symbols.Symbol.Visibility.PUBLIC)])
    region_type_symbol = symbols.TypeSymbol("region_type", region_type)
    grid_type = symbols.StructureType.create([
        ("nx", symbols.INTEGER_TYPE, symbols.Symbol.Visibility.PUBLIC),
        ("region", region_type_symbol, symbols.Symbol.Visibility.PUBLIC)])
    grid_type_symbol = symbols.TypeSymbol("grid_type", grid_type)
    grid_array_type = symbols.ArrayType(grid_type_symbol, [5])
    ssym = symbols.DataSymbol("grid", grid_array_type)
    int_one = nodes.Literal("1", symbols.INTEGER_TYPE)
    # Reference to scalar member of structure in array of structures
    asref = nodes.ArrayStructureReference.create(
        ssym, ["nx"], [int_one])
    assert isinstance(asref.children[0], nodes.MemberReference)
    assert isinstance(asref.children[1], nodes.Literal)
    check_links(asref, asref.children)
    # Reference to member of structure member of structure in array of
    # structures
    asref = nodes.ArrayStructureReference.create(
        ssym, ["region", "startx"], [int_one])
    assert isinstance(asref.children[0], nodes.StructureMemberReference)
    assert isinstance(asref.children[0].children[0], nodes.MemberReference)
    # Reference to range of structures
    lbound = nodes.BinaryOperation.create(
        nodes.BinaryOperation.Operator.LBOUND,
        nodes.ArrayStructureReference.create(ssym), int_one)
    ubound = nodes.BinaryOperation.create(
        nodes.BinaryOperation.Operator.UBOUND,
        nodes.ArrayStructureReference.create(ssym), int_one)
    my_range = nodes.Range.create(lbound, ubound)
    asref = nodes.ArrayStructureReference.create(ssym, ["nx"], [my_range])
    assert isinstance(asref.children[0], nodes.MemberReference)
    assert isinstance(asref.children[1], nodes.Range)
    check_links(asref, asref.children)
    check_links(asref.children[1], asref.children[1].children)


def test_asr_create_errors():
    ''' Test the validation checks within the create method. Most validation
    is done within the StructureReference class so there's not much to check
    here. '''
    with pytest.raises(TypeError) as err:
        _ = nodes.ArrayStructureReference.create(1)
    assert ("'symbol' argument to ArrayStructureReference.create() should "
            "be a DataSymbol but found 'int'" in str(err.value))
    scalar_symbol = symbols.DataSymbol("scalar", symbols.INTEGER_TYPE)
    with pytest.raises(TypeError) as err:
        _ = nodes.ArrayStructureReference.create(scalar_symbol)
    assert "ArrayType but symbol 'scalar' has type 'Scalar" in str(err.value)


def test_ast_str():
    ''' Test the __str__ method of the class. '''
    pass
