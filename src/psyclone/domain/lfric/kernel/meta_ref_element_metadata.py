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
# Author R. W. Ford, STFC Daresbury Lab

'''Module containing the MetaRefElementMetadata class which captures
the values for the LFRic kernel meta_ref_element metadata.

'''
from psyclone.domain.lfric import LFRicConstants
from psyclone.domain.lfric.kernel.common_declaration_metadata import \
    CommonDeclarationMetadata
from psyclone.domain.lfric.kernel.meta_ref_element_arg_metadata import \
    MetaRefElementArgMetadata


class MetaRefElementMetadata(CommonDeclarationMetadata):
    '''Class to capture the values of the LFRic kernel
    meta_ref_element metadata. This class supports the creation,
    modification and Fortran output of this metadata.

    meta_ref_element metadata specifies whether any quadrature
    or evaluator data is required for a given function space.

    :param meta_ref_element_args: a list of meta_ref_element arguments.
    :type meta_ref_element_args: List[:py:class:`psyclone.domain.lfric.kernel.\
        MetaRefElementArgMetadata`]

    '''
    def __init__(self, meta_ref_element_args):
        self.meta_ref_element_args = meta_ref_element_args

    def fortran_string(self):
        '''
         :returns: the meta_ref_element metadata as Fortran.
         :rtype: str
        '''
        return MetaRefElementMetadata.type_declaration_string(
            "REFERENCE_ELEMENT_DATA_TYPE", "META_REFERENCE_ELEMENT",
            self._meta_ref_element_args)

    @staticmethod
    def create_from_fparser2(fparser2_tree):
        '''Create an instance of MetaRefElementMetadata from an fparser2
        tree.

        LFRic meta ref element metadata is in array form. Two
        versions of the array form are supported:

        type(func_type) :: meta_ref_element(1) = (/ ... /)
        type(func_type), dimension(1) :: meta_ref_element = (/ ... /)

        :param fparser2_tree: fparser2 tree capturing the meta \
            ref element metadata.

        :type fparser2_tree: :py:class:`fparser.two.Fortran2003.\
            Data_Component_Def_Stmt`

        :returns: an instance of MetaRefElementMetadata.
        :rtype: :py:class:`psyclone.domain.lfric.kernel.\
            MetaRefElementMetadata`

        '''
        values_list = MetaRefElementMetadata.validate_derived_array_declaration(
            fparser2_tree, "REFERENCE_ELEMENT_DATA_TYPE",
            "META_REFERENCE_ELEMENT")
        meta_obj_list = []
        for value in values_list:
            meta_obj_list.append(
                MetaRefElementArgMetadata.create_from_fortran_string(value))
        return MetaRefElementMetadata(meta_obj_list)

    @property
    def meta_ref_element_args(self):
        '''
        :returns: a list of meta ref element argument objects.
        :rtype: List[:py:class:`psyclone.domain.lfric.kernel.\
            MetaRefElementArgMetadata`]
        '''
        return self._meta_ref_element_args[:]

    @meta_ref_element_args.setter
    def meta_ref_element_args(self, values):
        '''
        :param values: set the meta_ref_element metadata to the \
            supplied list of values.
        :type values: List[:py:class:`psyclone.domain.lfric.kernel.\
            MetaRefElementArgMetadata`]

        raises TypeError: if the supplied value is not a list.
        raises TypeError: if the supplied value is an empty list.
        raises TypeError: if any entry in the list is not of the \
            required type.

        '''
        if not isinstance(values, list):
            raise TypeError(f"meta_ref_element values should be provided as "
                            f"a list but found '{type(values).__name__}'.")
        if not values:
            raise TypeError(
                "The meta_ref_element list should contain at least one "
                "entry, but it is empty.")
        const = LFRicConstants()
        for value in values:
            if not isinstance(value, MetaRefElementArgMetadata):
                raise TypeError(
                    f"The meta_ref_element list should be a list containing objects "
                    f"of type MetaRefElementArgMetadata but found "
                    f"'{type(value).__name__}'.")
        # Take a copy of the list so that it can't be modified
        # externally.
        self._meta_ref_element_args = values[:]
