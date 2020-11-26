# -----------------------------------------------------------------------------
# BSD 3-Clause License
#
# Copyright (c) 2017-2020, Science and Technology Facilities Council.
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
# Authors R. W. Ford, A. R. Porter and S. Siso, STFC Daresbury Lab
#         I. Kavcic, Met Office
#         J. Henrichs, Bureau of Meteorology
# -----------------------------------------------------------------------------

''' This module contains the SymbolTable implementation. '''

from __future__ import print_function, absolute_import
from collections import OrderedDict
import six
from psyclone.configuration import Config
from psyclone.psyir.symbols import Symbol, DataSymbol, GlobalInterface, \
    ContainerSymbol, TypeSymbol
from psyclone.psyir.symbols.symbol import SymbolError
from psyclone.errors import InternalError


class SymbolTable(object):
    # pylint: disable=too-many-public-methods
    '''Encapsulates the symbol table and provides methods to add new
    symbols and look up existing symbols. Nested scopes are supported
    and, by default, the add and lookup methods take any ancestor
    symbol tables into consideration (ones attached to nodes that are
    ancestors of the node that this symbol table is attached to).

    :param node: reference to the Schedule or Container to which this \
        symbol table belongs.
    :type node: :py:class:`psyclone.psyir.nodes.Schedule`, \
        :py:class:`psyclone.psyir.nodes.Container` or NoneType

    :raises TypeError: if node argument is not a Schedule or a Container.

    '''
    def __init__(self, node=None):
        # Dict of Symbol objects with the symbol names as keys. Make
        # this ordered so that different versions of Python always
        # produce code with declarations in the same order.
        self._symbols = OrderedDict()
        # Ordered list of the arguments.
        self._argument_list = []
        # Dict of tags. Some symbols can be identified with a tag.
        self._tags = {}
        # Reference to the node to which this symbol table belongs.
        from psyclone.psyir.nodes import Schedule, Container
        if node and not isinstance(node, (Schedule, Container)):
            raise TypeError(
                "Optional node argument to SymbolTable should be a "
                "Schedule or a Container but found '{0}'."
                "".format(type(node).__name__))
        self._node = node

    @property
    def node(self):
        '''
        :returns: reference to the Schedule or Container to which this \
            symbol table belongs.
        :rtype: :py:class:`psyclone.psyir.nodes.Schedule`, \
            :py:class:`psyclone.psyir.nodes.Container` or NoneType

        '''
        return self._node

    @property
    def parent(self):
        '''
        :returns: the 'parent' SymbolTable of the current SymbolTable (i.e.
                  the one that encloses this one in the PSyIR hierarchy).
        :rtype: :py:class:`psyclone.psyir.symbols.SymbolTable` or NoneType
        '''
        # We use the Node with which this table is associated in order to
        # move up the Node hierarchy
        if self.node and self.node.parent:
            return self.node.parent.scope.symbol_table
        return None

    @property
    def _all_symbols(self):
        '''Return symbols from this symbol table and all symbol tables
        associated with ancestors of the node that this symbol table
        is attached to. If there are duplicates we only return one of
        them (the one from the closest ancestor including self).

        :returns: ordered dictionary of symbols indexed by symbol name.
        :rtype: OrderedDict[str] = :py:class:`psyclone.psyir.symbols.Symbol`

        '''
        all_symbols = OrderedDict(self._symbols)
        current = self
        while current.parent:
            current = current.parent
            for symbol_name in current.symbols_dict:
                if symbol_name not in all_symbols:
                    all_symbols[symbol_name] = current.symbols_dict[
                        symbol_name]
        return all_symbols

    @property
    def _all_tags(self):
        '''Return tags from this symbol table and all symbol tables associated
        with ancestors of the node that this symbol table is attached
        to. If there are duplicates we only return one of them (the
        one from the closest ancestor including self).

        :returns: ordered dictionary of symbols indexed by tag.
        :rtype: OrderedDict[str] = :py:class:`psyclone.psyir.symbols.Symbol`

        '''
        all_tags = OrderedDict(self._tags)
        current = self
        while current.parent:
            current = current.parent
            for tag in current.tags_dict:
                if tag not in all_tags:
                    all_tags[tag] = current.tags_dict[tag]
        return all_tags

    def shallow_copy(self):
        '''Create a copy of the symbol table where the top-level containers
        are new (symbols added to the new symbol table will not be added in
        the original but the existing objects are still the same).

        :returns: a copy of this symbol table.
        :rtype: :py:class:`psyclone.psyir.symbols.SymbolTable`

        '''
        # pylint: disable=protected-access
        from copy import copy
        new_st = SymbolTable()
        new_st._symbols = copy(self._symbols)
        new_st._argument_list = copy(self._argument_list)
        new_st._tags = copy(self._tags)
        new_st._node = self.node
        return new_st

    @staticmethod
    def _normalize(key):
        '''Normalises the symboltable key strings.

        :param str key: an input key.

        :returns: the normalized key.
        :rtype: str

        '''
        # The symbol table is currently case insensitive
        new_key = key.lower()
        return new_key

    def new_symbol_name(self, root_name=None, check_ancestors=True):
        '''Create a symbol name that is not in this symbol table (if the
        `check_ancestors` argument is False) or in this or any
        ancestor symbol table (if the `check_ancestors` argument is
        True). If the `root_name` argument is not supplied or if it is
        an empty string then the name is generated internally,
        otherwise the `root_name` is used. If required, an additional
        integer is appended to avoid clashes.

        :param root_name: optional name to use when creating a new \
            symbol name. This will be appended with an integer if the name \
            clashes with an existing symbol name.
        :type root_name: str or NoneType
        :param bool check_ancestors: optional logical flag indicating \
            whether the name should be unique in this symbol table \
            (False) or in this and all ancestor symbol tables \
            (True). Defaults to True.

        :returns: the new unique symbol name.
        :rtype: str

        :raises TypeError: if the root_name argument is not a string \
            or None.

        '''
        if check_ancestors:
            symbols = self._all_symbols
        else:
            symbols = self._symbols

        if root_name is not None and not isinstance(root_name, str):
            raise TypeError(
                "Argument root_name should be of type str or NoneType but "
                "found '{0}'.".format(type(root_name).__name__))
        if not root_name:
            root_name = Config.get().psyir_root_name
        candidate_name = root_name
        idx = 1
        while candidate_name in symbols:
            candidate_name = "{0}_{1}".format(root_name, idx)
            idx += 1
        return candidate_name

    def add(self, new_symbol, tag=None, check_ancestors=True):
        '''Add a new symbol to the symbol table if the symbol name is not
        already in use.

        :param new_symbol: the symbol to add to the symbol table.
        :type new_symbol: :py:class:`psyclone.psyir.symbols.Symbol`
        :param str tag: a tag identifier for the new symbol, by default no \
            tag is given.
        :param bool check_ancestors: optional logical flag indicating \
            whether the symbol name and tag (if provided) should be \
            unique in this symbol table (False) or in this and all \
            ancestor symbol tables (True). Defaults to True.

        :raises InternalError: if the new_symbol argument is not a \
            symbol.
        :raises KeyError: if the symbol name is already in use.
        :raises KeyError: if a tag is supplied and it is already in \
            use.

        '''
        if check_ancestors:
            symbols = self._all_symbols
        else:
            symbols = self._symbols

        if not isinstance(new_symbol, Symbol):
            raise InternalError("Symbol '{0}' is not a symbol, but '{1}'.'"
                                .format(new_symbol, type(new_symbol).__name__))

        key = self._normalize(new_symbol.name)
        if key in symbols:
            raise KeyError("Symbol table already contains a symbol with"
                           " name '{0}'.".format(new_symbol.name))

        if tag:
            if check_ancestors:
                tags = self._all_tags
            else:
                tags = self._tags
            if tag in tags:
                raise KeyError(
                    "Symbol table already contains the tag '{0}' for symbol"
                    " '{1}', so it can not be associated to symbol '{2}'.".
                    format(tag, tags[tag], new_symbol.name))
            self._tags[tag] = new_symbol

        self._symbols[key] = new_symbol

    def swap_symbol_properties(self, symbol1, symbol2):
        '''Swaps the properties of symbol1 and symbol2 apart from the symbol
        name. Argument list positions are also updated appropriately.

        :param symbol1: the first symbol.
        :type symbol1: :py:class:`psyclone.psyir.symbols.Symbol`
        :param symbol2: the second symbol.
        :type symbol2: :py:class:`psyclone.psyir.symbols.Symbol`

        :raises KeyError: if either of the supplied symbols are not in \
                          the symbol table.
        :raises TypeError: if the supplied arguments are not symbols, \
                 or the names of the symbols are the same in the SymbolTable \
                 instance.

        '''
        for symbol in [symbol1, symbol2]:
            if not isinstance(symbol, Symbol):
                raise TypeError("Arguments should be of type 'Symbol' but "
                                "found '{0}'.".format(type(symbol).__name__))
            if symbol.name not in self._symbols:
                raise KeyError("Symbol '{0}' is not in the symbol table."
                               "".format(symbol.name))
        if symbol1.name == symbol2.name:
            raise ValueError("The symbols should have different names, but "
                             "found '{0}' for both.".format(symbol1.name))

        tmp_symbol = symbol1.copy()
        symbol1.copy_properties(symbol2)
        symbol2.copy_properties(tmp_symbol)

        # Update argument list if necessary
        index1 = None
        if symbol1 in self._argument_list:
            index1 = self._argument_list.index(symbol1)
        index2 = None
        if symbol2 in self._argument_list:
            index2 = self._argument_list.index(symbol2)
        if index1 is not None:
            self._argument_list[index1] = symbol2
        if index2 is not None:
            self._argument_list[index2] = symbol1

    def specify_argument_list(self, argument_symbols):
        '''
        Sets-up the internal list storing the order of the arguments to this
        kernel.

        :param list argument_symbols: ordered list of the DataSymbols \
            representing the kernel arguments.

        :raises ValueError: if the new argument_list is not consistent with \
            the existing entries in the SymbolTable.

        '''
        self._validate_arg_list(argument_symbols)
        self._argument_list = argument_symbols[:]

    def lookup(self, name, visibility=None, check_ancestors=True):
        '''Look up a symbol in the symbol table (if the `check_ancestors`
        argument is False) or in this or any ancestor symbol table (if
        the `check_ancestors` argument is True).

        :param str name: name of the symbol.
        :param visibilty: the visibility or list of visibilities that the \
                          symbol must have.
        :type visibility: [list of] :py:class:`psyclone.symbols.Visibility`
        :param bool check_ancestors: optional logical flag indicating \
            whether the symbol name should be unique in this symbol \
            table (False) or in this and all ancestor symbol tables \
            (True). Defaults to True.

        :returns: the symbol with the given name and, if specified, visibility.
        :rtype: :py:class:`psyclone.psyir.symbols.Symbol`

        :raises TypeError: if the name argument is not a string.
        :raises SymbolError: if the name exists in the Symbol Table but does \
                             not have the specified visibility.
        :raises TypeError: if the visibility argument has the wrong type.
        :raises KeyError: if the given name is not in the Symbol Table.

        '''
        if not isinstance(name, six.string_types):
            raise TypeError(
                "Expected the name argument to the lookup() method to be "
                "a str but found '{0}'."
                "".format(type(name).__name__))

        if check_ancestors:
            symbols = self._all_symbols
        else:
            symbols = self._symbols

        try:
            symbol = symbols[self._normalize(name)]
            if visibility:
                if not isinstance(visibility, list):
                    vis_list = [visibility]
                else:
                    vis_list = visibility
                if symbol.visibility not in vis_list:
                    vis_names = []
                    # Take care here in case the 'visibility' argument
                    # is of the wrong type
                    for vis in vis_list:
                        if not isinstance(vis, Symbol.Visibility):
                            raise TypeError(
                                "the 'visibility' argument to lookup() must be"
                                " an instance (or list of instances) of "
                                "Symbol.Visibility but got '{0}' when "
                                "searching for symbol '{1}'".format(
                                    type(vis).__name__, name))
                        vis_names.append(vis.name)
                    raise SymbolError(
                        "Symbol '{0}' exists in the Symbol Table but has "
                        "visibility '{1}' which does not match with the "
                        "requested visibility: {2}".format(
                            name, symbol.visibility.name, vis_names))
            return symbol
        except KeyError:
            raise KeyError("Could not find '{0}' in the Symbol Table."
                           "".format(name))

    def lookup_with_tag(self, tag, check_ancestors=True):
        '''Look up a symbol using the supplied tag. If check_ancestors is True
        then this and any ancestor symbol tables are searched,
        otherwise only this symbol table is examined.

        :param str tag: tag identifier.
        :param bool check_ancestors: optional logical flag indicating \
            whether the tag should be from just this symbol table \
            (False) or this and all ancestor symbol tables \
            (True). Defaults to True.

        :returns: symbol with the given tag.
        :rtype: :py:class:`psyclone.psyir.symbols.Symbol`

        :raises TypeError: if the tag argument is not a string.
        :raises KeyError: if the given tag is not in the Symbol Table.

        '''
        if not isinstance(tag, six.string_types):
            raise TypeError(
                "Expected the tag argument to the lookup_with_tag() method "
                "to be a str but found '{0}'.".format(type(tag).__name__))

        if check_ancestors:
            tags = self._all_tags
        else:
            tags = self._tags

        try:
            return tags[tag]
        except KeyError:
            raise KeyError("Could not find the tag '{0}' in the Symbol Table."
                           "".format(tag))

    def name_from_tag(self, tag, root=None, check_ancestors=True):
        '''If the supplied tag exists in this symbol table (if the
        `check_ancestors` argument is False) or in this or any
        ancestor symbol table (if the `check_ancestors` argument is
        True), then return the symbol name associated with it,
        otherwise create a new symbol associated with this tag (using
        the tag as name or optionally the provided root) and return
        the name of the new symbol.

        Note that this method creates generic Symbols without properties like
        datatypes and just returns the name string (not the Symbol object).
        This is commonly needed on the current psy-layer implementation but not
        recommended on new style PSyIR. This method may be deprecated in the
        future. (TODO #720)

        There is no need to check the argument types as this method
        calls methods which check the argument types.

        :param str tag: tag identifier.
        :param str root: optional name of the new symbols if this needs to \
            be created.
        :param bool check_ancestors: optional logical flag indicating \
            whether the tag should be from just this symbol table \
            (False) or this and all ancestor symbol tables \
            (True). Defaults to True.

        :returns: name associated with the given tag.
        :rtype: str

        '''
        try:
            return self.lookup_with_tag(
                tag, check_ancestors=check_ancestors).name
        except KeyError:
            if root:
                name = self.new_symbol_name(
                    root, check_ancestors=check_ancestors)
            else:
                name = self.new_symbol_name(
                    tag, check_ancestors=check_ancestors)
            # No need to check ancestors as this has already been done
            # when creating the name.
            self.add(Symbol(name), tag=tag, check_ancestors=False)
            return name

    def __contains__(self, key):
        '''Check if the given key is part of the Symbol Table.

        :param str key: key to check for existance.

        :returns: whether the Symbol Table contains the given key.
        :rtype: bool
        '''
        return self._normalize(key.lower()) in self._symbols

    def imported_symbols(self, csymbol):
        '''
        Examines the contents of this symbol table to see which DataSymbols
        (if any) are imported from the supplied ContainerSymbol (which must
        be present in the SymbolTable).

        :param csymbol: the ContainerSymbol to search for imports from.
        :type csymbol: :py:class:`psyclone.psyir.symbols.ContainerSymbol`

        :returns: list of DataSymbols that are imported from the supplied \
                  ContainerSymbol. If none are found then the list is empty.
        :rtype: list of :py:class:`psyclone.psyir.symbols.DataSymbol`

        :raises TypeError: if the supplied object is not a ContainerSymbol.
        :raises KeyError: if the supplied object is not in this SymbolTable.

        '''
        if not isinstance(csymbol, ContainerSymbol):
            raise TypeError(
                "imported_symbols() expects a ContainerSymbol but got an "
                "object of type '{0}'".format(type(csymbol).__name__))
        # self.lookup(name) will raise a KeyError if there is no symbol with
        # that name in the table.
        if self.lookup(csymbol.name) is not csymbol:
            raise KeyError("The '{0}' entry in this SymbolTable is not the "
                           "supplied ContainerSymbol.".format(csymbol.name))

        return [symbol for symbol in self.global_symbols if
                symbol.interface.container_symbol is csymbol]

    def swap(self, old_symbol, new_symbol):
        '''
        Remove the `old_symbol` from the table and replace it with the
        `new_symbol`.

        :param old_symbol: the symbol to remove from the table.
        :type old_symbol: :py:class:`psyclone.psyir.symbols.Symbol`
        :param new_symbol: the symbol to add to the table.
        :type new_symbol: :py:class:`psyclone.psyir.symbols.Symbol`

        :raises TypeError: if either old/new_symbol are not Symbols.
        :raises SymbolError: if `old_symbol` and `new_symbol` don't have \
                             the same name.
        '''
        if not isinstance(old_symbol, Symbol):
            raise TypeError("Symbol to remove must be of type Symbol but "
                            "got '{0}'".format(type(old_symbol).__name__))
        if not isinstance(new_symbol, Symbol):
            raise TypeError("Symbol to add must be of type Symbol but "
                            "got '{0}'".format(type(new_symbol).__name__))
        if old_symbol.name != new_symbol.name:
            raise SymbolError(
                "Cannot swap symbols that have different names, got: '{0}' "
                "and '{1}'".format(old_symbol.name, new_symbol.name))
        # TODO #898 remove() does not currently check for any uses of
        # old_symbol.
        self.remove(old_symbol)
        self.add(new_symbol)

    def remove(self, symbol):
        '''
        Remove the supplied Symbol or ContainerSymbol from the Symbol Table.
        Support for removing other types of Symbol will be added as required.

        TODO #898. This method should check for any references/uses of
        the target symbol, even if it's not a ContainerSymbol.

        :param symbol: the container symbol to remove.
        :type symbol: :py:class:`psyclone.psyir.symbols.ContainerSymbol`

        :raises TypeError: if the supplied symbol is not a ContainerSymbol.
        :raises KeyError: if the supplied symbol is not in the symbol table.
        :raises ValueError: if the supplied container symbol is referenced \
                            by one or more DataSymbols.
        :raises InternalError: if the supplied symbol is not the same as the \
                               entry with that name in this SymbolTable.
        '''
        # pylint: disable=unidiomatic-typecheck
        if not (isinstance(symbol, ContainerSymbol) or type(symbol) == Symbol):
            raise TypeError("remove() expects a ContainerSymbol or Symbol "
                            "object but got: '{0}'".format(
                                type(symbol).__name__))
        # pylint: enable=unidiomatic-typecheck
        if symbol.name not in self._symbols:
            raise KeyError("Cannot remove Symbol '{0}' from symbol table "
                           "because it does not exist.".format(symbol.name))
        # Sanity-check that the entry in the table is the symbol we've
        # been passed.
        if self._symbols[symbol.name] is not symbol:
            raise InternalError(
                "The Symbol with name '{0}' in this symbol table is not the "
                "same Symbol object as the one that has been supplied to the "
                "remove() method.".format(symbol.name))
        # We can only remove a ContainerSymbol if no DataSymbols are
        # being imported from it
        if (isinstance(symbol, ContainerSymbol) and
                self.imported_symbols(symbol)):
            raise ValueError(
                "Cannot remove ContainerSymbol '{0}' because symbols "
                "{1} are imported from it - remove them first.".format(
                    symbol.name,
                    [sym.name for sym in self.imported_symbols(symbol)]))
        self._symbols.pop(symbol.name)

    @property
    def argument_list(self):
        '''
        Checks that the contents of the SymbolTable are self-consistent
        and then returns the list of kernel arguments.

        :returns: ordered list of arguments.
        :rtype: list of :py:class:`psyclone.psyir.symbols.DataSymbol`

        :raises InternalError: if the entries of the SymbolTable are not \
            self-consistent.

        '''
        try:
            self._validate_arg_list(self._argument_list)
            self._validate_non_args()
        except ValueError as err:
            # If the SymbolTable is inconsistent at this point then
            # we have an InternalError.
            raise InternalError(str(err.args))
        return self._argument_list

    @staticmethod
    def _validate_arg_list(arg_list):
        '''
        Checks that the supplied list of Symbols are valid kernel arguments.

        :param arg_list: the proposed kernel arguments.
        :type param_list: list of :py:class:`psyclone.psyir.symbols.DataSymbol`

        :raises TypeError: if any item in the supplied list is not a \
            DataSymbol.
        :raises ValueError: if any of the symbols does not have an argument \
            interface.

        '''
        for symbol in arg_list:
            if not isinstance(symbol, DataSymbol):
                raise TypeError("Expected a list of DataSymbols but found an "
                                "object of type '{0}'.".format(type(symbol)))
            if not symbol.is_argument:
                raise ValueError(
                    "DataSymbol '{0}' is listed as a kernel argument but has "
                    "an interface of type '{1}' rather than "
                    "ArgumentInterface"
                    "".format(str(symbol), type(symbol.interface)))

    def _validate_non_args(self):
        '''
        Performs internal consistency checks on the current entries in the
        SymbolTable that do not represent kernel arguments.

        :raises ValueError: if a symbol that is not in the argument list \
            has an argument interface.

        '''
        for symbol in self.datasymbols:
            if symbol not in self._argument_list:
                # DataSymbols not in the argument list must not have a
                # Symbol.Argument interface
                if symbol.is_argument:
                    raise ValueError(
                        "Symbol '{0}' is not listed as a kernel argument and "
                        "yet has an ArgumentInterface interface."
                        "".format(str(symbol)))

    def get_unresolved_datasymbols(self, ignore_precision=False):
        '''
        Create a list of the names of all of the DataSymbols in the table that
        do not have a resolved interface. If ignore_precision is True then
        those DataSymbols that are used to define the precision of other
        DataSymbols are ignored. If no unresolved DataSymbols are found then an
        empty list is returned.

        :param bool ignore_precision: whether or not to ignore DataSymbols \
                    that are used to define the precision of other DataSymbols.

        :returns: the names of those DataSymbols with unresolved interfaces.
        :rtype: list of str

        '''
        unresolved_symbols = [sym for sym in self.datasymbols
                              if sym.is_unresolved]
        if ignore_precision:
            unresolved_datasymbols = list(set(unresolved_symbols) -
                                          set(self.precision_datasymbols))
        else:
            unresolved_datasymbols = unresolved_symbols
        return [sym.name for sym in unresolved_datasymbols]

    @property
    def symbols_dict(self):
        '''
        :returns: ordered dictionary of symbols indexed by symbol name.
        :rtype: OrderedDict[str] = :py:class:`psyclone.psyir.symbols.Symbol`

        '''
        return self._symbols

    @property
    def tags_dict(self):
        '''
        :returns: ordered dictionary of symbols indexed by tag.
        :rtype: OrderedDict[str] = :py:class:`psyclone.psyir.symbols.Symbol`

        '''
        return self._tags

    @property
    def symbols(self):
        '''
        :returns: list of symbols.
        :rtype: list of :py:class:`psyclone.psyir.symbols.Symbol`
        '''
        return list(self._symbols.values())

    @property
    def datasymbols(self):
        '''
        :returns: list of symbols representing data variables.
        :rtype: list of :py:class:`psyclone.psyir.symbols.DataSymbol`
        '''
        return [sym for sym in self._symbols.values() if
                isinstance(sym, DataSymbol)]

    @property
    def local_datasymbols(self):
        '''
        :returns: list of symbols representing local variables.
        :rtype: list of :py:class:`psyclone.psyir.symbols.DataSymbol`
        '''
        return [sym for sym in self.datasymbols if sym.is_local]

    @property
    def argument_datasymbols(self):
        '''
        :returns: list of symbols representing arguments.
        :rtype: list of :py:class:`psyclone.psyir.symbols.DataSymbol`
        '''
        return [sym for sym in self.datasymbols if sym.is_argument]

    @property
    def global_symbols(self):
        '''
        :returns: list of symbols that have 'global' interface (are \
            associated with data that exists outside the current scope).
        :rtype: list of :py:class:`psyclone.psyir.symbols.Symbol`

        '''
        return [sym for sym in self.symbols if sym.is_global]

    @property
    def precision_datasymbols(self):
        '''
        :returns: list of all symbols used to define the precision of \
                  other symbols within the table.
        :rtype: list of :py:class:`psyclone.psyir.symbols.DataSymbol`

        '''
        # Accumulate into a set so as to remove any duplicates
        precision_symbols = set()
        from psyclone.psyir.symbols import DeferredType
        for sym in self.datasymbols:
            if (not isinstance(sym.datatype, (TypeSymbol, DeferredType)) and
                    isinstance(sym.datatype.precision, DataSymbol)):
                precision_symbols.add(sym.datatype.precision)
        return list(precision_symbols)

    @property
    def containersymbols(self):
        '''
        :returns: a list of the ContainerSymbols present in the Symbol Table.
        :rtype: list of :py:class:`psyclone.psyir.symbols.ContainerSymbol`
        '''
        return [sym for sym in self.symbols if isinstance(sym,
                                                          ContainerSymbol)]

    @property
    def iteration_indices(self):
        '''
        :returns: list of symbols representing kernel iteration indices.
        :rtype: list of :py:class:`psyclone.psyir.symbols.DataSymbol`

        :raises NotImplementedError: this method is abstract.
        '''
        raise NotImplementedError(
            "Abstract property. Which symbols are iteration indices is"
            " API-specific.")

    @property
    def data_arguments(self):
        '''
        :returns: list of symbols representing kernel data arguments.
        :rtype: list of :py:class:`psyclone.psyir.symbols.DataSymbol`

        :raises NotImplementedError: this method is abstract.
        '''
        raise NotImplementedError(
            "Abstract property. Which symbols are data arguments is"
            " API-specific.")

    def copy_external_global(self, globalvar, tag=None):
        '''
        Copy the given global variable (and its referenced ContainerSymbol if
        needed) into the SymbolTable.

        :param globalvar: the variable to be copied in.
        :type globalvar: :py:class:`psyclone.psyir.symbols.DataSymbol`
        :param str tag: a tag identifier for the new copy, by default no tag \
            is given.

        :raises TypeError: if the given variable is not a global variable.
        :raises KeyError: if the given variable name already exists in the \
            symbol table.

        '''
        if not isinstance(globalvar, DataSymbol):
            raise TypeError(
                "The globalvar argument of SymbolTable.copy_external_global"
                " method should be a DataSymbol, but found '{0}'."
                "".format(type(globalvar).__name__))

        if not globalvar.is_global:
            raise TypeError(
                "The globalvar argument of SymbolTable.copy_external_"
                "global method should have a GlobalInterface interface, "
                "but found '{0}'.".format(type(globalvar.interface).__name__))

        external_container_name = globalvar.interface.container_symbol.name

        # If the Container is not yet in the SymbolTable we need to
        # create one and add it.
        if external_container_name not in self:
            self.add(ContainerSymbol(external_container_name))
        container_ref = self.lookup(external_container_name)

        # Copy the variable into the SymbolTable with the appropriate interface
        if globalvar.name not in self:
            new_symbol = globalvar.copy()
            # Update the interface of this new symbol
            new_symbol.interface = GlobalInterface(container_ref)
            self.add(new_symbol, tag)
        else:
            # If it already exists it must refer to the same Container and have
            # the same tag.
            local_instance = self.lookup(globalvar.name)
            if not (local_instance.is_global and
                    local_instance.interface.container_symbol.name ==
                    external_container_name):
                raise KeyError(
                    "Couldn't copy '{0}' into the SymbolTable. The"
                    " name '{1}' is already used by another symbol."
                    "".format(globalvar, globalvar.name))
            if tag:
                # If the symbol already exists and a tag is provided
                try:
                    self.lookup_with_tag(tag)
                except KeyError:
                    # If the tag was not used, it will now be attached
                    # to the symbol.
                    self._tags[tag] = self.lookup(globalvar.name)

                # The tag should not refer to a different symbol
                if self.lookup(globalvar.name) != self.lookup_with_tag(tag):
                    raise KeyError(
                        "Couldn't copy '{0}' into the SymbolTable. The"
                        " tag '{1}' is already used by another symbol."
                        "".format(globalvar, tag))

    def view(self):
        '''
        Print a representation of this Symbol Table to stdout.
        '''
        print(str(self))

    def __str__(self):
        return ("Symbol Table:\n" +
                "\n".join(map(str, self._symbols.values())) +
                "\n")
