from datetime import date, time, datetime
import sys
import json
import re

SPARQL_INT_TYPES = ["http://www.w3.org/2001/XMLSchema#integer", "http://www.w3.org/2001/XMLSchema#byte",
                    "http://www.w3.org/2001/XMLSchema#short", "http://www.w3.org/2001/XMLSchema#int",
                    "http://www.w3.org/2001/XMLSchema#long", "http://www.w3.org/2001/XMLSchema#unsignedByte",
                    "http://www.w3.org/2001/XMLSchema#unsignedShort", "http://www.w3.org/2001/XMLSchema#unsignedInt",
                    "http://www.w3.org/2001/XMLSchema#unsignedLong", "http://www.w3.org/2001/XMLSchema#negativeInteger",
                    "http://www.w3.org/2001/XMLSchema#nonNegativeInteger",
                    "http://www.w3.org/2001/XMLSchema#positiveInteger"]
SPARQL_BOOL_TYPES = ["http://www.w3.org/2001/XMLSchema#boolean"]
SPARQL_FLOAT_TYPES = ["http://www.w3.org/2001/XMLSchema#decimal", "http://www.w3.org/2001/XMLSchema#double",
                      "http://www.w3.org/2001/XMLSchema#float", "http://www.w3.org/2002/07/owl#real"]
SPARQL_STR_TYPES = ["http://www.w3.org/2001/XMLSchema#string"]
SPARQL_DATETIME_TYPES = ["http://www.w3.org/2001/XMLSchema#dateTime"]
SPARQL_TIME_TYPES = ["http://www.w3.org/2001/XMLSchema#time"]
SPARQL_DATE_TYPES = ["http://www.w3.org/2001/XMLSchema#date"]


class QueryGenerator:

    @staticmethod
    def serialize_to_sparql_type(value):
        """Serialize the data type in Python to SPARQL"""
        if isinstance(value, str):
            return f'"{value}"'
        elif isinstance(value, int):
            return f'{value}'
        elif isinstance(value, float):
            return f'{value}'
        elif isinstance(value, bool):
            return 'true' if value is True or value == 'true' else 'false'
        # ISO 8601
        elif isinstance(value, datetime):
            return f'"{value.isoformat()}"^^xsd:dateTime'
        elif isinstance(value, date):
            return f'"{value.isoformat()}"^^xsd:date'
        elif isinstance(value, time):
            return f'"{value.isoformat()}"^^xsd:time'
        else:
            raise NotImplemented(f"Unknown Python type: {type(value)}")

    @staticmethod
    def serialize_to_sparql_type_with_datetype(value, datatype):
        if datatype in SPARQL_DATE_TYPES:
            if isinstance(value, date):
                return f'"{value.isoformat()}"^^xsd:date'
            else:
                return f'"{value}"^^xsd:date'
        elif datatype in SPARQL_DATETIME_TYPES:
            if isinstance(value, datetime):
                return f'"{value.isoformat()}"^^xsd:dateTime'
            else:
                return f'"{value}"^^xsd:dateTime'
        elif datatype in SPARQL_TIME_TYPES:
            if isinstance(value, time):
                return f'"{value.isoformat()}"^^xsd:time'
            else:
                return f'"{value}"^^xsd:time'
        elif datatype in SPARQL_INT_TYPES:
            return int(value)
        elif datatype in SPARQL_FLOAT_TYPES:
            return float(value)
        elif datatype in SPARQL_BOOL_TYPES:
            return 'true' if value is True or value == 'true' else 'false'
        elif datatype in SPARQL_STR_TYPES or datatype is None:  # Default to string
            return json.dumps(value)
        elif datatype.startswith("@"):
            match = re.match(r'[a-zA-Z]+(-[a-zA-Z0-9]+)*', datatype[1:])
            if match is None or match.group(0) != datatype[1:]:
                print(f"Illegal language tag: {datatype}, ignored (language tag removed)", file=sys.stderr)
                return json.dumps(value)
            return f'{json.dumps(value)}{datatype}'
        else:
            # Arbitrary Datatypes: https://www.w3.org/TR/rdf-sparql-query/#matchArbDT
            return f'"{value}^^<{datatype}>"'
            # raise TypeError(f"Unknown SPARQL type {datatype}")

    @staticmethod
    def deserialize_to_owlready_type(value, type, datatype):
        """
        deserialize the datatype in SPARQL to Python
        https://www.w3.org/TR/sparql11-results-json/ 3.2.2 Encoding RDF terms
        Literal S with datatype IRI D	{ "type": "literal", "value": "S", "datatype": "D"}
        TODO: Literal S with language tag L	{ "type": "literal", "value": "S", "xml:lang": "L"}
        """
        if type == 'uri' or type == 'bnode':
            raise TypeError("Should not call deserialize_to_py_type with datatype 'uri' or 'bnode'")
        elif type == 'literal':
            if datatype in SPARQL_DATE_TYPES:
                return date.fromisoformat(value)
            elif datatype in SPARQL_DATETIME_TYPES:
                return datetime.fromisoformat(value)
            elif datatype in SPARQL_TIME_TYPES:
                return time.fromisoformat(value)
            elif datatype in SPARQL_INT_TYPES:
                return int(value)
            elif datatype in SPARQL_FLOAT_TYPES:
                return float(value)
            elif datatype in SPARQL_BOOL_TYPES:
                return True if value == 'true' else False
            else:
                # Default to string
                return value
        else:
            raise NotImplemented(f"Unknown SPARQL datatype: {datatype}")

    @staticmethod
    def generate_select_query(s=None, p=None, o=None, d=None, sid=None, oid=None, is_obj=False, is_data=False,
                              distinct=False, graph_iris=None, default_graph_iri=None, limit=None, order_by=None):
        """
        Designed for GraphDB only.
        Uses http://www.ontotext.com/owlim/entity#id to get internal ID for entities in subject/object.
        """
        if not is_obj and not is_data:
            raise TypeError("'is_obj' and 'is_data' cannot be both False")
        if graph_iris and default_graph_iri:
            # This can happen in the future.
            raise TypeError("Should not give both 'graph_iris' and 'default_graph_iri'.")

        binds = []
        filters = []
        from_clauses = []
        default_graph_clause = ''

        if s and isinstance(s, str):
            binds.append(f'bind(<{s}> as ?s)')
        elif s and isinstance(s, list):
            inner_filter = []
            for item in s:
                # blank node
                if isinstance(item, int) and item < 0:
                    inner_filter.append(f'?sid = {-item}')
                else:
                    inner_filter.append(f'?s = <{item}>')
            filters.append(f'filter({" || ".join(inner_filter)})')

        if p and isinstance(p, str):
            binds.append(f'bind(<{p}> as ?p)')
        elif p and isinstance(p, list):
            inner_filter = []
            for item in p:
                # blank node
                if isinstance(item, int) and item < 0:
                    raise TypeError("Predicate cannot be blank node.")
                else:
                    inner_filter.append(f'?p = <{item}>')
            filters.append(f'filter({" || ".join(inner_filter)})')

        if sid or (isinstance(s, int) and s < 0):
            binds.append(f'bind({-(sid or s)} as ?sid)')
        if oid or (isinstance(o, int) and o < 0):
            binds.append(f'bind({-(oid or o)} as ?oid)')

        if is_obj and not is_data:
            if o:
                binds.append(f'bind(<{o}> as ?o)')
            else:
                filters.append('filter(isIRI(?o) || isBlank(?o))')
        elif is_data and not is_obj:
            if o and d:
                binds.append(f'bind({QueryGenerator.serialize_to_sparql_type_with_datetype(o, d)} as ?o)')
            elif o and d is None:
                binds.append(f'bind({QueryGenerator.serialize_to_sparql_type(o)}) as ?o')
            elif o is None and d:
                filters.append('filter(!isIRI(?o) && !isBlank(?o))')
                filters.append(f'filter(datatype(?o) = <{d}>)')
            elif o is None and d is None:
                filters.append('filter(!isIRI(?o) && !isBlank(?o))')
        elif is_data and is_obj:
            # o is always None in owlready2's usage, but I implemented the case that o is not None.
            if o and d:
                # o is data since datatype is given
                binds.append(f'bind({QueryGenerator.serialize_to_sparql_type_with_datetype(o, d)}) as ?o')
            elif o and d is None:
                binds.append(f'bind(<{o}> as ?o) as ?o')
            elif o is None and d:
                # assume o is data since datatype is given
                filters.append('filter(!isIRI(?o) && !isBlank(?o))')
                filters.append(f'filter(datatype(?o) = <{d}>)')
            # No need to specify filters

        # from, define default graph
        if default_graph_iri is not None:
            default_graph_clause = f"from <{default_graph_iri}>"

        # from named, choose named graph to query
        if graph_iris is None:
            graph_iris = []
        for graph_iri in graph_iris:
            from_clauses.append(f"from named <{graph_iri}>")

        newline = '\n\t\t\t\t'
        include_g = len(graph_iris) > 0
        query = f"""
            PREFIX ent: <http://www.ontotext.com/owlim/entity#>
            select {'distinct' if distinct else ''} {'?g' if include_g else ''} ?s ?p ?o ?sid ?oid
            {newline.join([default_graph_clause, *from_clauses])}
            where {{
                {newline.join(binds)}
                {'graph ?g {?s ?p ?o}.' if include_g else '?s ?p ?o.'}
                ?s ent:id ?sid.
                ?o ent:id ?oid.
                {newline.join(filters)}
            }}{f'order by {order_by} ' if order_by else ''}{f' limit {limit}' if limit else ''}
        """
        return query

    @staticmethod
    def generate_insert_query(s, p, o, d=None, is_data=False, default_graph_iri=None, sid=None, oid=None):
        """
        Generate SPARQL insert query.
        'o' could be literal or URI.
        """
        if not default_graph_iri:
            raise TypeError('default_graph_iri is required.')

        # 'o' is a literal if 'd' is provided
        if d or d == '':
            is_data = True
        if is_data and d is None:
            d = SPARQL_STR_TYPES[0]

        subject = f'<{s}>'
        object = f'<{o}>' if not is_data else QueryGenerator.serialize_to_sparql_type_with_datetype(o, d)
        where_clause = []

        # s is a blank node
        if isinstance(s, int) and s < 0:
            subject = '?s'
            where_clause.append(f'?s ent:id {-s}.')

        # o is a blank node
        if isinstance(o, int) and o < 0:
            object = '?o'
            where_clause.append(f'?o ent:id {-o}.')

        query = f"""
            PREFIX ent: <http://www.ontotext.com/owlim/entity#>
            insert {'data' if len(where_clause) == 0 else ''} {{
                graph <{default_graph_iri}> {{
                    {subject} <{p}> {object}
                }}
            }}{('where {' + ''.join(where_clause) + '}') if len(where_clause) > 0 else ''};
        """
        return query

    @staticmethod
    def generate_delete_query(s=None, p=None, o=None, d=None, is_data=False, default_graph_iri=None):
        """
        Generate SPARQL delete query.
        'o' could be literal or URI, and should be serialized before invoke this method.
        """
        if not default_graph_iri:
            raise TypeError('default_graph_iri is required.')

        where_clause = []

        subject = '?s' if s is None else f'<{s}>'
        predicate = '?p' if p is None else f'<{p}>'
        object = '?o'

        # s is a blank node
        if isinstance(s, int) and s < 0:
            subject = '?s'
            where_clause.append(f'?s ent:id {-s}.')

        # 'o' is a literal if 'd' is provided
        if d or is_data:
            object = QueryGenerator.serialize_to_sparql_type_with_datetype(o, d)
        elif o:
            object = f'<{o}>'

        query = f"""
            PREFIX ent: <http://www.ontotext.com/owlim/entity#>
            delete where {{
                graph <{default_graph_iri}> {{
                    {subject} {predicate} {object}.
                }}
                {''.join(where_clause)}
            }}
        """
        return query
