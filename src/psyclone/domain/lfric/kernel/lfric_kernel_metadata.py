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

'''Module containing the LFRicKernelMetadata
kernel-layer-specific class that captures the LFRic kernel metadata.

'''
from fparser.common.readfortran import FortranStringReader
from fparser.two import Fortran2003
from fparser.two.parser import ParserFactory
from fparser.two.utils import walk, get_child

from psyclone.configuration import Config
from psyclone.domain.lfric import LFRicConstants
from psyclone.domain.lfric.kernel.columnwise_operator_arg_metadata import \
    ColumnwiseOperatorArgMetadata
from psyclone.domain.lfric.kernel.common_metadata import CommonMetadata
from psyclone.domain.lfric.kernel.common_arg_metadata import CommonArgMetadata
from psyclone.domain.lfric.kernel.evaluator_targets_metadata import \
    EvaluatorTargetsMetadata
from psyclone.domain.lfric.kernel.field_arg_metadata import FieldArgMetadata
from psyclone.domain.lfric.kernel.field_vector_arg_metadata import \
    FieldVectorArgMetadata
from psyclone.domain.lfric.kernel.inter_grid_arg_metadata import \
    InterGridArgMetadata
from psyclone.domain.lfric.kernel.inter_grid_vector_arg_metadata import \
    InterGridVectorArgMetadata
from psyclone.domain.lfric.kernel.meta_args_metadata import \
    MetaArgsMetadata
from psyclone.domain.lfric.kernel.meta_mesh_metadata import \
    MetaMeshMetadata
from psyclone.domain.lfric.kernel.meta_funcs_metadata import \
    MetaFuncsMetadata
from psyclone.domain.lfric.kernel.operates_on_metadata import \
    OperatesOnMetadata
from psyclone.domain.lfric.kernel.operator_arg_metadata import \
    OperatorArgMetadata
from psyclone.domain.lfric.kernel.meta_ref_element_metadata import \
    MetaRefElementMetadata
from psyclone.domain.lfric.kernel.scalar_arg_metadata import ScalarArgMetadata
from psyclone.domain.lfric.kernel.shapes_metadata import ShapesMetadata
from psyclone.errors import InternalError
from psyclone.parse.utils import ParseError
from psyclone.psyir.symbols import DataTypeSymbol, UnknownFortranType


class LFRicKernelMetadata(CommonMetadata):
    '''Contains LFRic kernel metadata. This class supports kernel
    metadata creation, modification, loading from a fortran string,
    writing to a fortran string, raising from existing language-level
    PSyIR and lowering to language-level PSyIR.

    :param meta_args: a list of 'meta_arg' objects which capture the \
        metadata values of the kernel arguments.
    :type meta_args: List[:py:class:`psyclone.domain.lfric.kernel.CommonArg`]
    :param meta_funcs: a list of 'meta_func' objects which capture whether \
        quadrature or evaluator data is required for a given function space.
    :type meta_funcs: Optional[List[:py:class:`psyclone.domain.lfric.kernel.\
        MetaFuncsArgMetadata`]]
    :param meta_ref_element: a kernel that requires properties \
        of the reference element in LFRic specifies those properties \
        through the meta_reference_element metadata entry.
    :type meta_ref_element: :py:class:`psyclone.domain.lfric.kernel.\
        RefElementArgMetadata`
    :param meta_mesh: a kernel that requires properties of the LFRic \
        mesh object specifies those properties through the meta_mesh \
        metadata entry.
    :type meta_mesh: :py:class:`psyclone.domain.lfric.kernel.\
        MetaMeshArgMetadata`
    :param shapes: if a kernel requires basis or differential-basis \
        functions then the metadata must also specify the set of points on \
        which these functions are required. This information is provided \
        by the gh_shape component of the metadata.
    :type shapes: List[str]
    :param evaluator_targets: the function spaces on which an \
        evaluator is required.
    :type evaluator_targets: List[str]
    :param operates_on: the name of the quantity that this kernel is \
        intended to iterate over.
    :type operates_on: Optional[str]
    :param procedure_name: the name of the kernel procedure to call.
    :type procedure_name: Optional[str]
    :param name: the name of the symbol to use for the metadata in \
        language-level PSyIR.
    :type name: Optional[str]

    '''
    # The fparser2 class that captures this metadata.
    fparser2_class = Fortran2003.Derived_Type_Def
    
    def __init__(self, operates_on=None, shapes=None, evaluator_targets=None,
                 meta_args=None, meta_funcs=None, meta_ref_element=None,
                 meta_mesh=None, procedure_name=None, name=None):
        # Initialise internal variables
        self._operates_on = None
        self._shapes = None
        self._evaluator_targets = None
        self._meta_args = None
        self._meta_funcs = None
        self._meta_ref_element = None
        self._meta_mesh = None
        self._procedure_name = None
        self._name = None

        if operates_on is not None:
            self._operates_on = OperatesOnMetadata(operates_on)
        if shapes is not None:
            self._shapes = ShapesMetadata(shapes)
        if evaluator_targets is not None:
            self._evaluator_targets = EvaluatorTargetsMetadata(
                evaluator_targets)
        if meta_args is not None:
            self._meta_args = MetaArgsMetadata(meta_args)
        if meta_funcs is not None:
            self._meta_funcs = MetaFuncsMetadata(meta_funcs)
        if meta_ref_element is not None:
            self._meta_ref_element = MetaRefElementMetadata(
                meta_ref_element)
        if meta_mesh is not None:
            self._meta_mesh = MetaMeshMetadata(meta_mesh)
        if procedure_name is not None:
            # Validate procedure_name via setter
            self.procedure_name = procedure_name
        if name is not None:
            # Validate name via setter
            self.name = name

    @staticmethod
    def create_from_psyir(symbol):
        '''Create a new instance of LFRicKernelMetadata populated with
        metadata from a kernel in language-level PSyIR.

        :param symbol: the symbol in which the metadata is stored \
            in language-level PSyIR.
        :type symbol: :py:class:`psyclone.psyir.symbols.DataTypeSymbol`

        :returns: an instance of LFRicKernelMetadata.
        :rtype: :py:class:`psyclone.domain.lfric.kernel.psyir.\
            LFRicKernelMetadata`

        :raises TypeError: if the symbol argument is not the expected \
            type.
        :raises InternalError: if the datatype of the provided symbol \
            is not the expected type.

        '''
        if not isinstance(symbol, DataTypeSymbol):
            raise TypeError(
                f"Expected a DataTypeSymbol but found a "
                f"{type(symbol).__name__}.")

        datatype = symbol.datatype

        if not isinstance(datatype, UnknownFortranType):
            raise InternalError(
                f"Expected kernel metadata to be stored in the PSyIR as "
                f"an UnknownFortranType, but found "
                f"{type(datatype).__name__}.")

        # In an UnknownFortranType, the declaration is stored as a
        # string, so use create_from_fortran_string()
        return LFRicKernelMetadata.create_from_fortran_string(
            datatype.declaration)

    @staticmethod
    def create_from_fparser2(fparser2_tree):
        '''Create an instance of this class from an fparser2 tree.

        :param fparser2_tree: fparser2 tree containing the metadata \
            for an LFRic Kernel.
        :type fparser2_tree: \
            :py:class:`fparser.two.Fortran2003.Derived_Type_Ref`

        :returns: an instance of LFRicKernelMetadata.
        :rtype: :py:class:`psyclone.domain.lfric.kernel.psyir.\
            LFRicKernelMetadata`

        :raises ParseError: if one of the meta_args entries is an \
            unexpected type.

        '''
        LFRicKernelMetadata.check_fparser2(
            fparser2_tree, Fortran2003.Derived_Type_Def)

        kernel_metadata = LFRicKernelMetadata()

        for fparser2_node in walk(
                fparser2_tree, Fortran2003.Data_Component_Def_Stmt):

            if "operates_on" in (str(fparser2_node)).lower():
                # the value of operates on (CELL_COLUMN, ...)
                kernel_metadata._operates_on = OperatesOnMetadata.\
                    create_from_fparser2(fparser2_node)
            elif "meta_args" in (str(fparser2_node)).lower():
                kernel_metadata._meta_args = MetaArgsMetadata.\
                    create_from_fparser2(fparser2_node)
            elif "meta_funcs" in (str(fparser2_node)).lower():
                kernel_metadata._meta_funcs = MetaFuncsMetadata.\
                    create_from_fparser2(fparser2_node)
            elif "gh_shape" in (str(fparser2_node)).lower():
                # the gh_shape values (gh_quadrature_XYoZ, ...)
                kernel_metadata._shapes = ShapesMetadata.create_from_fparser2(
                    fparser2_node)
            elif "gh_evaluator_targets" in (str(fparser2_node)).lower():
                # the gh_evaluator_targets values (w0, w1, ...)
                kernel_metadata._evaluator_targets = EvaluatorTargetsMetadata.\
                    create_from_fparser2(fparser2_node)
            elif "meta_reference_element" in (str(fparser2_node)).lower():
                kernel_metadata._meta_ref_element = MetaRefElementMetadata.\
                    create_from_fparser2(fparser2_node)
            elif "meta_mesh" in (str(fparser2_node)).lower():
                kernel_metadata._meta_mesh = MetaMeshMetadata.\
                    create_from_fparser2(fparser2_node)
            else:
                raise ParseError(
                    f"Found unexpected metadata declaration "
                    f"'{str(fparser2_node)}' in '{str(fparser2_tree)}'.")

        kernel_metadata.name = fparser2_tree.children[0].children[1].tostr()
        kernel_metadata.procedure_name = LFRicKernelMetadata._get_property(
            fparser2_tree, "code").string

        return kernel_metadata

    def lower_to_psyir(self):
        '''Lower the metadata to language-level PSyIR.

        :returns: metadata as stored in language-level PSyIR.
        :rtype: :py:class:`psyclone.psyir.symbols.DataTypeSymbol`

        '''
        return DataTypeSymbol(
            str(self.name), UnknownFortranType(self.fortran_string()))

    @staticmethod
    def _get_property(spec_part, property_name):
        '''Internal utility that gets the property 'property_name' from an
        fparser2 tree capturing LFRic metadata. It is assumed that
        the code property is part of a type bound procedure and that
        the other properties are part of the data declarations.

        :param spec_part: the fparser2 parse tree containing the metadata.
        :type spec_part: :py:class:`fparser.two.Fortran2003.Derived_Type_Def`
        :param str property_name: the name of the property whose value \
            is being extracted from the metadata.

        :returns: the value of the property.
        :rtype: :py:class:`fparser.two.Fortran2003.Name | \
            :py:class:`fparser.two.Fortran2003.Array_Constructor`

        :raises ParseError: if the metadata is invalid.

        '''
        # TODO issue #1879. What to do if we have an interface.
        if property_name.lower() == "code":
            # The value of 'code' should be found in a type bound
            # procedure (after the contains keyword)
            type_bound_procedure = get_child(
                spec_part, Fortran2003.Type_Bound_Procedure_Part)
            if not type_bound_procedure:
                raise ParseError(
                    f"No type-bound procedure found within a 'contains' "
                    f"section in '{spec_part}'.")
            if len(type_bound_procedure.children) != 2:
                raise ParseError(
                    f"Expecting a type-bound procedure, but found "
                    f"'{spec_part}'.")
            specific_binding = type_bound_procedure.children[1]
            if not isinstance(specific_binding, Fortran2003.Specific_Binding):
                raise ParseError(
                    f"Expecting a specific binding for the type-bound "
                    f"procedure, but found '{specific_binding}' in "
                    f"'{spec_part}'.")
            binding_name = specific_binding.children[3]
            procedure_name = specific_binding.children[4]
            if binding_name.string.lower() != "code" and procedure_name:
                raise ParseError(
                    f"Expecting the type-bound procedure binding-name to be "
                    f"'code' if there is a procedure name, but found "
                    f"'{str(binding_name)}' in '{spec_part}'.")
            if not procedure_name:
                # Support the alternative metadata format that does
                # not include 'code =>'
                procedure_name = binding_name
            return procedure_name

        # The 'property_name' will be declared within Component_Part.
        component_part = get_child(spec_part, Fortran2003.Component_Part)
        if not component_part:
            raise ParseError(
                f"No declarations were found in the kernel metadata: "
                f"'{spec_part}'.")
        # Each name/value pair will be contained within a Component_Decl
        for component_decl in walk(component_part, Fortran2003.Component_Decl):
            # Component_Decl(Name('name') ...)
            name = component_decl.children[0].string
            if name.lower() == property_name.lower():
                # The value will be contained in a Component_Initialization
                comp_init = get_child(
                    component_decl, Fortran2003.Component_Initialization)
                if not comp_init:
                    raise ParseError(
                        f"No value for property {property_name} was found "
                        f"in '{spec_part}'.")
                # Component_Initialization('=', Name('name'))
                return comp_init.children[1]
        raise ParseError(
            f"'{property_name}' was not found in {str(spec_part)}.")

    def fortran_string(self):
        '''
        :returns: the metadata represented by this instance as Fortran.
        :rtype: str

        :raises ValueError: if the values for name, meta_arg, \
            operates_on and procedure_name have not been set.

        '''
        if not (self.operates_on and self._meta_args and
                self.procedure_name and self.name):
            raise ValueError(
                f"Values for operates_on, meta_args, procedure_name and name "
                f"must be provided before calling the fortran_string method, "
                f"but found '{self.operates_on}', '{self._meta_args}', "
                f"'{self.procedure_name}' and '{self.name}' "
                f"respectively.")

        operates_on = f"  {self._operates_on.fortran_string()}"
        meta_args = f"  {self._meta_args.fortran_string()}"

        shapes = ""
        if self._shapes:
            shapes = f"  {self._shapes.fortran_string()}"

        evaluator_targets = ""
        if self._evaluator_targets:
            evaluator_targets = f"  {self._evaluator_targets.fortran_string()}"

        meta_funcs = ""
        if self._meta_funcs:
            meta_funcs = f"  {self._meta_funcs.fortran_string()}"

        meta_ref_element = ""
        if self._meta_ref_element:
            meta_ref_element = f"  {self._meta_ref_element.fortran_string()}"

        meta_mesh = ""
        if self._meta_mesh:
            meta_mesh = f"  {self._meta_mesh.fortran_string()}"

        result = (
            f"TYPE, PUBLIC, EXTENDS(kernel_type) :: {self.name}\n"
            f"{meta_args}"
            f"{meta_funcs}"
            f"{meta_ref_element}"
            f"{meta_mesh}"
            f"{shapes}"
            f"{evaluator_targets}"
            f"{operates_on}"
            f"  CONTAINS\n"
            f"    PROCEDURE, NOPASS :: {self.procedure_name}\n"
            f"END TYPE {self.name}\n")
        return result

    @property
    def operates_on(self):
        '''
        :returns: the kernel operates_on property specified by the \
            metadata.
        :rtype: str
        '''
        if self._operates_on is None:
            return None
        else:
            return self._operates_on.operates_on

    @operates_on.setter
    def operates_on(self, value):
        '''
        :param str value: set the kernel operates_on property \
            in the metadata to the specified value.

        '''
        self._operates_on = OperatesOnMetadata(value)

    @property
    def shapes(self):
        '''
        :returns: a list of shape metadata values.
        :rtype: Optional[List[str]]

        '''
        if self._shapes is None:
            return None
        else:
            return self._shapes.shapes

    @shapes.setter
    def shapes(self, values):
        '''
        :param values: set the shape metadata to the \
            supplied list of values.
        :type values: List[str]

        '''
        self._shapes = ShapesMetadata(values)

    @property
    def evaluator_targets(self):
        '''
        :returns: a list of evaluator_targets metadata values.
        :rtype: Optional[List[str]]

        '''
        if self._evaluator_targets is None:
            return None
        else:
            return self._evaluator_targets.evaluator_targets

    @evaluator_targets.setter
    def evaluator_targets(self, values):
        '''
        :param values: set the evaluator_targets metadata to the \
            supplied list of values.
        :type values: List[str]

        '''
        self._evaluator_targets = EvaluatorTargetsMetadata(values)

    @property
    def meta_args(self):
        '''
        :returns: a list of 'meta_arg' objects which capture the \
            metadata values of the kernel arguments.
        :rtype: Optional[List[:py:class:`psyclone.domain.lfric.kernel.\
            CommonArg`]]

        '''
        if self._meta_args is None:
            return None
        else:
            return self._meta_args.meta_args_args

    @meta_args.setter
    def meta_args(self, values):
        '''
        :param values: set the meta_args metadata to the \
            supplied list of values.
        :type values: List[:py:class:`psyclone.domain.lfric.kernel.\
            CommonArg`]

        '''
        self._meta_args = MetaArgsMetadata(values)

    @property
    def meta_funcs(self):
        '''
        :returns: a list of meta_funcs metadata values.
        :rtype: Optional[List[:py:class:`psyclone.domain.lfric.kernel.\
            MetaFuncsArgMetadata`]]

        '''
        if self._meta_funcs is None:
            return None
        else:
            return self._meta_funcs.meta_funcs_args

    @meta_funcs.setter
    def meta_funcs(self, values):
        '''
        :param values: set the meta_funcs metadata to the \
            supplied list of values.
        :type values: List[:py:class:`psyclone.domain.lfric.kernel.\
            MetaFuncsArgMetadata`]

        '''
        self._meta_funcs = MetaFuncsMetadata(values)

    @property
    def meta_ref_element(self):
        '''
        :returns: a list of meta_reference_element metadata values.
        :rtype: Optional[List[:py:class:`psyclone.domain.lfric.kernel.\
            MetaRefElementArgMetadata`]]

        '''
        if self._meta_ref_element is None:
            return None
        else:
            return self._meta_ref_element.meta_ref_element_args

    @meta_ref_element.setter
    def meta_ref_element(self, values):
        '''
        :param values: set the meta_funcs metadata to the \
            supplied list of values.
        :type values: List[:py:class:`psyclone.domain.lfric.kernel.\
            MetaRefElementArgMetadata`]

        '''
        self._meta_ref_element = MetaRefElementMetadata(values)

    @property
    def meta_mesh(self):
        '''
        :returns: a list of meta_mesh metadata values.
        :rtype: Optional[List[:py:class:`psyclone.domain.lfric.kernel.\
            MetaMeshArgMetadata`]]

        '''
        if self._meta_mesh is None:
            return None
        else:
            return self._meta_mesh.meta_mesh_args

    @meta_mesh.setter
    def meta_mesh(self, values):
        '''
        :param values: set the meta_mesh metadata to the \
            supplied list of values.
        :type values: List[:py:class:`psyclone.domain.lfric.kernel.\
            MetaMeshArgMetadata`]

        '''
        self._meta_mesh = MetaMeshMetadata(values)

    @property
    def procedure_name(self):
        '''
        :returns: the kernel procedure name specified by the metadata.
        :rtype: str
        '''
        return self._procedure_name

    @procedure_name.setter
    def procedure_name(self, value):
        '''
        :param str value: set the kernel procedure name in the \
            metadata to the specified value.

        :raises ValueError: if the metadata has an invalid value.

        '''
        config = Config.get()
        if not value or not config.valid_name.match(value):
            raise ValueError(
                f"Expected procedure_name to be a valid Fortran name but "
                f"found '{value}'.")
        self._procedure_name = value

    @property
    def name(self):
        '''
        :returns: the name of the symbol that will contain the \
            metadata when lowering.
        :rtype: str

        '''
        return self._name

    @name.setter
    def name(self, value):
        '''
        :param str value: set the name of the symbol that will contain \
            the metadata when lowering.

        :raises ValueError: if the name is not valid.

        '''
        config = Config.get()
        if not value or not config.valid_name.match(value):
            raise ValueError(
                f"Expected name to be a valid Fortran name but found "
                f"'{value}'.")
        self._name = value
