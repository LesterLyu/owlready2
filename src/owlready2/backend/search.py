from owlready2.util import FirstList, _LazyListMixin
from owlready2.base import _universal_abbrev_2_iri, to_literal
from owlready2.backend.utils import QueryGenerator

import fnmatch


class SparqlSubQuery:
    """
    The query inside WHERE clause:
    SELECT ... WHERE {
        **SparqlSubQuery**
    }
    """

    def __init__(self, triples=None, filters=None, binds=None, prefixes=None):
        self.triples = triples or []
        self.filters = filters or []
        self.binds = binds or []
        self.prefixes = prefixes or {}

    def triple_clauses(self):
        return '    \n'.join(self.triples)

    def bind_clauses(self):
        return '    \n'.join(self.binds)

    def filter_clauses(self):
        return '    \n'.join(self.filters)

    def __str__(self):
        result = '{\n'
        if len(self.binds):
            result += ' ' * 8 + self.bind_clauses()
        result += '    ?s ent:id ?sid.\n'
        if len(self.triples):
            result += ' ' * 8 + self.triple_clauses() + '\n'
        if len(self.filters):
            result += ' ' * 8 + self.filter_clauses() + '\n'
        result += '\n}'
        return result


class SparqlStatement:
    """
    SPARQL Statement contains multiple `SparqlSubQuery`.
    """

    def __init__(self, sub_queries=None, prefixes=None, selects=None, distinct=False, limit=None):
        self.sub_queries = sub_queries or []

        self.prefixes = {'rdf:': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                         'rdfs:': 'http://www.w3.org/2000/01/rdf-schema#',
                         'ent:': 'http://www.ontotext.com/owlim/entity#', **(prefixes or {})}
        for sub_query in self.sub_queries:
            self.prefixes.update(sub_query.prefixes)

        self.selects = selects or ['?s', '?sid']
        self.distinct = distinct
        self.limit = limit

    def generate_sparql(self):
        """Return the SPARQL query of this instance"""

        prefix_clauses = '\n'.join([f'PREFIX {key} <{value}>' for key, value in self.prefixes.items()])
        where_clauses = []
        for sub_query in self.sub_queries:
            where_clauses.append(str(sub_query))

        return f"""
        {prefix_clauses}
        SELECT {'DISTINCT ' if self.distinct else ''}{' '.join(self.selects)} WHERE {{
            {' UNION '.join(where_clauses)}
        }}{f' limit {self.limit}' if self.limit else ''}
        """

    def __str__(self):
        return self.generate_sparql()


class SparqlSearch:

    @staticmethod
    def search(world, _use_str_as_loc_str=True, _case_sensitive=True, _bm25=False, infer=False, **kwargs):
        """
        @param: _use_str_as_loc_str: whether to treats plain Python strings as strings in any language (default is True).
                loc_str is locale string, a string with a language tag.
        @param: _case_sensitive: whether to take lower/upper case into consideration (default is True).
        @param: _bm25: Not supported in the SPARQL backend.
        @param: infer: Include inferred data in results.

        kwargs are the followings:
        `iri`, for searching entities by its full IRI.
        `type`, for searching Individuals of a given Class.
        `subclass_of`, for searching subclasses of a given Class.
        `is_a`, for searching both Individuals and subclasses of a given Class.
        `subproperty_of`, for searching subproperty of a given Property.
        any object, data or annotation property name.

        The value associated to each keyword can be a single value or a list of several values.
        A list of serveral values are treated as AND.
        A star * can be used as a jocker in string values.

        Wildcard Search:
        `onto.search(iri = "*Topping")`

        Nested search:
        `onto.search(is_a = onto.Pizza, has_topping = onto.search(is_a = onto.TomatoTopping))`
        """
        if not _use_str_as_loc_str or not _case_sensitive:
            raise NotImplementedError
        if _bm25:
            raise ValueError("'_bm25' is not supported in SPARQL backend!")

        sparql_statement = SparqlStatement(distinct=True)
        curr_sub_query = SparqlSubQuery()
        sparql_statement.sub_queries.append(curr_sub_query)
        prefixes = {'rdf:': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#'}
        for key, val in kwargs.items():
            if key == 'iri':
                # Basic IRI match, supports wildcards *, i.e. *Topping
                curr_sub_query.triples.append('?s ?p ?o.')
                if isinstance(val, str) and '*' in val:
                    # Translate wildcards to regex
                    regex = fnmatch.translate(val)
                    curr_sub_query.filters.append(f'FILTER regex(str(?s), "{repr(regex)[1:-1]}", "")')
                else:
                    curr_sub_query.binds.append(f'BIND(<{val}> as ?s)')

            elif key == 'type':
                # Match with rdf:type
                curr_sub_query.triples.append(f'?s rdf:type <{val.iri}>.')

            elif key == 'subclass_of':
                # Match with rdfs:subClassOf
                curr_sub_query.triples.append(f'?s rdfs:subClassOf <{val.iri}>.')

            elif key == 'is_a':
                # Match with {?s rdf:type* <some_iri>} UNION {?s rdfs:subClassOf <some_iri>}
                curr_sub_query.triples.append(f'?s rdfs:subClassOf* <{val.iri}>.')

                new_sub_query = SparqlSubQuery(triples=[
                    f'?s rdf:type* <{val.iri}>.'
                ])
                sparql_statement.sub_queries.append(new_sub_query)

            elif key == 'subproperty_of':
                # Match with rdfs:subPropertyOf
                curr_sub_query.triples.append(f'?s rdfs:subPropertyOf <{val.iri}>.')

            else:
                # Arbitrary object, data or annotation property name
                # key could be IRI string, or a shorthanded property string
                # TODO: Investigate Inverse property

                # Get prop IRI from the loaded properties, key is the shorthanded IRI (without namespace)
                prop = world._props.get(key)
                if prop:
                    prop = prop.iri
                else:
                    prop = key
                    # On-demand loading
                    if '/' not in prop:
                        prop = world.graph.get_property_iri(key)

                if hasattr(val, 'iri'):
                    curr_sub_query.triples.append(f'?s <{prop}> <{val.iri}>.')
                else:
                    # Wildcard
                    if isinstance(val, str) and '*' in val:
                        curr_sub_query.triples.append(f'?s <{prop}> ?o.')

                        # Translate wildcards to regex
                        regex = fnmatch.translate(val)
                        curr_sub_query.filters.append(f'FILTER regex(?o, "{repr(regex)[1:-1]}", "")')
                    else:
                        curr_sub_query.triples.append(f'?s <{prop}> {QueryGenerator.serialize_to_sparql_type(val)}')

        return _SearchList(sparql_statement, world)


class _SearchMixin(list):
    __slots__ = []

    def _get_content(self):
        print(str(self.sparql_statement))
        result = self.world.graph.client.execute_internal(str(self.sparql_statement))

        for item in result["results"]["bindings"]:
            yield self.world._get_by_storid(item["s"]["storid"])

    def first(self):
        return self._get_content()[0]

    def has_bm25(self):
        return False


class _PopulatedSearchList(FirstList):
    """
    The populated search list will be `isinstance(search_result, _PopulatedSearchList)`
    """
    __slots__ = ['world', 'sparql_statement', 'bm25']

    def has_bm25(self): return self.bm25


class _SearchList(FirstList, _SearchMixin, _LazyListMixin):
    __slots__ = ['world', 'sparql_statement', 'bm25']
    _PopulatedClass = _PopulatedSearchList

    def __init__(self, sparql_statement, world):
        super().__init__()
        self.world = world
        self.sparql_statement = sparql_statement
        self.bm25 = False

    def has_bm25(self):
        return self.bm25

    def __or__(self, other):
        raise NotImplementedError

    def __and__(self, other):
        raise NotImplementedError


class _PopulatedUnionSearchList(FirstList):
    __slots__ = ["world", "searches"]


class _UnionSearchList(FirstList, _SearchMixin, _LazyListMixin):
    __slots__ = ["world", "searches"]


class _PopulatedIntersectionSearchList(FirstList):
    __slots__ = ["world", "searches"]


class _IntersectionSearchList(FirstList, _SearchMixin, _LazyListMixin):
    __slots__ = ["world", "searches"]
