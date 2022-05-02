from time import time
import re
from owlready2.util import locstr
from .utils import QueryGenerator
import requests
import urllib

POST = 'POST'
GET = 'GET'


class SPARQLResponse:
    def __init__(self, response: requests.Response, is_update=False):
        self.response = response
        self.is_update = is_update
        if response.status_code >= 400:
            raise ValueError(f'{response.status_code}: {response.text}')

    def json(self):
        if self.is_update:
            return
        return self.response.json()


class SPARQLWrapper:
    # https://www.w3.org/TR/rdf-sparql-query/#rPN_CHARS_BASE
    PN_CHARS_BASE = r"[A-Z]|[a-z]|[\u00C0-\u00D6]|[\u00D8-\u00F6]|[\u00F8-\u02FF]|[\u0370-\u037D]|[\u037F-\u1FFF]" \
                    r"|[\u200C-\u200D]|[\u2070-\u218F]|[\u2C00-\u2FEF]|[\u3001-\uD7FF]|[\uF900-\uFDCF]" \
                    r"|[\uFDF0-\uFFFD]|[\U00010000-\U000EFFFF]"
    PN_CHARS_U = PN_CHARS_BASE + r"|_"
    PN_CHARS = PN_CHARS_U + r"|-|[0-9]|\u00B7|[\u0300-\u036F]|[\u203F-\u2040]"
    PN_PREFIX = f'({PN_CHARS_BASE})(({PN_CHARS}|\\.)*({PN_CHARS}))?'
    PNAME_NS = f'({PN_PREFIX})?:'
    IRI_REF = r'<([^<>\"{}|^`\]\[\x00-\x20])*>'
    PrefixDecl = re.compile(f'[Pp][Rr][Ee][Ff][Ii][Xx]\\s({PNAME_NS})\\s({IRI_REF})')

    @staticmethod
    def is_update_request(query_string):
        """
        Get the sparql query type: 'select' or 'update'.
        This is required for the sparql endpoint.
        """
        prev_time = time()
        # Remove prefixes
        query_string = re.sub(re.compile(SPARQLWrapper.PrefixDecl), '', query_string)

        # Trim the query
        query_string = query_string.strip()
        if re.match(r'^(select|construct|describe|ask)', query_string, re.IGNORECASE):
            SparqlClient.function_times['SparqlClient.parse_sparql_type'][0] += time() - prev_time
            SparqlClient.function_times['SparqlClient.parse_sparql_type'][1] += 1
            return False
        else:
            SparqlClient.function_times['SparqlClient.parse_sparql_type'][0] += time() - prev_time
            SparqlClient.function_times['SparqlClient.parse_sparql_type'][1] += 1
            return True

    def __init__(self, endpoint, is_update=False):
        self.endpoint = endpoint
        self.is_update = is_update
        self.username = None
        self.password = None
        self.method = 'POST'
        self.session = None
        self._query = None

    def set_method(self, method):
        self.method = method

    def set_query(self, query):
        self._query = query

    def set_credentials(self, username, password=None):
        self.username = username
        self.password = password

    def query(self):
        # Init session
        if self.session is None:
            self.session = requests.Session()
            if self.username:
                self.session.auth = (self.username, self.password)

        if self.method == POST:
            if self.is_update:
                response = self.session.request(self.method, self.endpoint,
                                                data=f'update={urllib.parse.quote(self._query)}',
                                                headers={
                                                    'Accept': 'text/plain',
                                                    'Content-Type': 'application/x-www-form-urlencoded'
                                                })
            else:
                response = self.session.request(self.method, self.endpoint,
                                                data=f'query={urllib.parse.quote(self._query)}',
                                                headers={
                                                    'Accept': 'application/sparql-results+json',
                                                    'Content-Type': 'application/x-www-form-urlencoded'
                                                })
        elif self.method == GET:
            if self.is_update:
                raise ValueError('update operations MUST be done by POST')

            response = self.session.request(self.method, self.endpoint,
                                            params={'query': urllib.parse.quote(self._query)},
                                            headers={
                                                'Accept': 'application/sparql-results+json'
                                            })
        else:
            raise ValueError('Illegal method:', self.method)

        return SPARQLResponse(response, is_update=self.is_update)


class SparqlClient:
    total_sparql_time = 0
    total_sparql_queries = 0
    function_times = {'SparqlClient.parse_sparql_type': [0, 0]}

    def __init__(self, endpoint, world, _abbreviate, debug=False, username=None, password=None):
        self.debug = debug
        self.world = world
        self._abbreviate = _abbreviate
        self.query_client = SPARQLWrapper(endpoint, is_update=False)
        self.update_client = SPARQLWrapper(endpoint + '/statements', is_update=True)
        if username:
            self.query_client.set_credentials(username, password)
            self.update_client.set_credentials(username, password)

    def execute_sparql(self, *query, method=None):
        """
        Execute sparql query only without post processing
        method could be 'select', 'update', or None.
        If method is None, SparqlClient.parse_sparql_type is invoked to check SPARQL format.
        """
        prev_time = time()
        if self.debug:
            import inspect
            print(
                f'Called from: {type(inspect.currentframe().f_back.f_back.f_locals["self"]).__name__}.{inspect.currentframe().f_back.f_back.f_code.co_name}(' + ', '.join(
                    inspect.currentframe().f_back.f_back.f_code.co_varnames) + ')')
            print(f"execute\n{';'.join(query).strip()}")

        # Check which client to use
        if method == 'select' or not SPARQLWrapper.is_update_request(query[0]):
            client = self.query_client
        else:
            client = self.update_client

        client.set_method(POST)
        client.set_query(';'.join(query))
        try:
            result = client.query().json()

            SparqlClient.total_sparql_time += time() - prev_time
            SparqlClient.total_sparql_queries += 1

            import inspect
            fun_name = f'{type(inspect.currentframe().f_back.f_back.f_locals["self"]).__name__}.{inspect.currentframe().f_back.f_back.f_code.co_name}'
            if not SparqlClient.function_times.get(fun_name):
                SparqlClient.function_times[fun_name] = [0, 0]
            SparqlClient.function_times[fun_name][0] += time() - prev_time
            SparqlClient.function_times[fun_name][1] += 1
            if self.debug:
                print(
                    f"took {round((time() - prev_time) * 1000)}ms. Total {fun_name}: {self.function_times[fun_name][0] * 1000}ms")
            return result

        except:
            print('error with the below sparql query using ' + (
                'update client' if client == self.update_client else 'normal client'))
            print(';'.join(query).strip())
            raise

    def execute_internal(self, *query, method=None):
        """
        execute + post processing for internal query
        """
        result = self.execute_sparql(*query, method=method)

        # Post processing
        if isinstance(result, dict):
            for item in result["results"]["bindings"]:
                for entity_name in ['s', 'p', 'o']:
                    entity = item.get(entity_name)
                    if not entity:
                        continue
                    # Pre-Abbreviate uri
                    if entity["type"] == 'uri':
                        entity["storid"] = self._abbreviate(entity["value"])
                    # process blank node id
                    elif entity["type"] == 'bnode':
                        entity["storid"] = -int(item[entity_name + 'id']["value"])
                        # print(f'Got blank node {entity["storid"]}')
                    # assign datatype for literal and storid 'd' for datatype
                    elif entity["type"] == 'literal':
                        if not entity.get('datatype') and not entity.get('xml:lang'):
                            entity['datatype'] = "http://www.w3.org/2001/XMLSchema#string"  # default is string
                        if entity.get('xml:lang'):
                            entity['d'] = f"@{entity.get('xml:lang')}"
                        else:
                            entity['d'] = self._abbreviate(entity.get('datatype'))

        return result

    def execute_owlready(self, *query, error_on_undefined_entities=True):
        """Execute and transform into owlready type for user defined query"""
        result = self.execute_sparql(*query)
        result_list = []
        # print(result)

        if isinstance(result, dict):
            bnode_cnt = 0
            vars = result['head']['vars']
            for item in result['results']['bindings']:
                inner_result_list = []
                for var in vars:
                    entity = item.get(var)
                    if not entity:
                        inner_result_list.append(None)
                        continue
                    if entity["type"] == 'uri':
                        storid = self._abbreviate(entity["value"])
                        inner_result_list.append(self.world._get_by_storid(storid) or storid)
                    elif entity["type"] == 'bnode':
                        bnode_cnt += 1
                        inner_result_list.append(f'_:temp-bnode-{bnode_cnt}')
                    elif entity['type'] == 'literal':
                        if entity.get('xml:lang'):
                            inner_result_list.append(locstr(entity['value'], entity['xml:lang']))
                        else:
                            inner_result_list.append(
                                QueryGenerator.deserialize_to_owlready_type(entity['value'], entity["type"],
                                                                            entity.get('datatype')))
                result_list.append(inner_result_list)
        return result_list
