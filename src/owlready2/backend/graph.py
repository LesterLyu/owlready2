from owlready2.base import *
from owlready2.driver import BaseMainGraph, BaseSubGraph
from owlready2.base import _universal_abbrev_2_iri, _universal_iri_2_abbrev, _next_abb

from .utils import QueryGenerator
from .subgraph import SparqlSubGraph
from .sparql_client import SparqlClient
import multiprocessing
from uuid import uuid4


class SparqlGraph(BaseMainGraph):
    _SUPPORT_CLONING = True

    def __init__(self, endpoint: str, world=None, debug=False, username=None, password=None):
        self.endpoint = endpoint
        self.world = world
        self.debug = debug

        self.client = SparqlClient(endpoint, world, self._abbreviate, debug, username=username, password=password)
        self.execute = self.client.execute_internal

        self.storid2iri = {}
        self.iri2storid = {}
        self.c2ontology = {
            # 0 is reserved for blank nodes in owlready2
        }
        self.graph_iri2c = {}
        self.named_graph_iris = []

        self.lock = multiprocessing.RLock()
        self.lock_level = 0

        if self.world:
            self.world._abbreviate = self._abbreviate
            self.world._unabbreviate = self._unabbreviate

        # Some magic variable to mark the db is initialized.
        self.indexed = True

    def __bool__(self):
        # Reimplemented to avoid calling __len__ in this case
        return True

    def __len__(self):
        from_clause = '\n\t\t\t\t'.join([f'from named <{graph_iri}>' for graph_iri in self.named_graph_iris])

        result = self.execute(f"""
            select (count(?s) as ?count)
            {from_clause}
            where {{
                graph ?g {{?s ?p ?o .}}
            }}
            """)
        return int(result['results']['bindings'][0]['count']['value'])

    def acquire_write_lock(self):
        self.lock.acquire()
        self.lock_level += 1

    def release_write_lock(self):
        self.lock_level -= 1
        self.lock.release()

    def has_write_lock(self):
        return self.lock_level

    def set_indexed(self, indexed):
        pass

    def close(self):
        # Don't do anything
        pass

    def sub_graph(self, onto):
        if self.debug:
            print("create new sub_graph with graph IRI " + onto.graph_iri)
        c = max([0, *[int(i) for i in self.c2ontology.keys()]]) + 1
        self.c2ontology[c] = onto

        # Check if the graph already exists.
        result = self.execute(f"""
            select ?s from <{onto.graph_iri}> where {{
                ?s ?p ?o .
            }} limit 1
        """)
        is_new = True if len(result['results']['bindings']) == 0 else False

        if is_new:
            # onto.base_iri could be an alias, check if such alias exists.
            result = self.execute(f"""
                PREFIX or2: <http://owlready2/internal#>
                select ?iri ?graph from <http://owlready2/internal> where {{
                    [or2:alias "{onto.base_iri}";
                        or2:iri ?iri;
                        or2:graph ?graph]
                }}
            """)
            if len(result['results']['bindings']) > 0:
                is_new = False
                item = result['results']['bindings'][0]
                onto.graph_iri = item['graph']['value']
                # onto.base_iri = item['iri']['value']

        if onto.graph_iri not in self.named_graph_iris:
            self.named_graph_iris.append(onto.graph_iri)

        self.graph_iri2c[onto.graph_iri] = c

        onto._abbreviate = self._abbreviate
        onto._unabbreviate = self._unabbreviate
        return SparqlSubGraph(self, onto, c), is_new

    def ontologies_iris(self):
        """
        Return all ontology/Named Graph IRIs.
        """
        result = self.execute("""
            PREFIX or2: <http://owlready2/internal#>
            select ?iri ?graph from <http://owlready2/internal> where { 
                [or2:alias ?alias;
                    or2:iri ?iri;
                    or2:graph ?graph]
            }
        """)
        iris = []
        for item in result["results"]["bindings"]:
            iris.append(item["iri"]["value"])
        return iris

    def _new_numbered_iri(self, prefix):
        """
        Generate numbered IRI.
        Metadata is stored in graph http://owlready2/internal as [or2:prefix ?prefix; or2:idx ?idx].
        idx start with 1.
        """
        result = self.execute(f"""
                   PREFIX or2: <http://owlready2/internal#>
                   select ?idx from <http://owlready2/internal> where {{
                       [or2:prefix "{prefix}";
                           or2:idx ?idx]
                   }}
        """)
        if len(result["results"]["bindings"]) > 0:
            idx = int(result["results"]["bindings"][0]["idx"]["value"]) + 1
            self.execute(f"""
                PREFIX or2: <http://owlready2/internal#>
                delete where {{
                     graph <http://owlready2/internal> {{
                        ?s or2:prefix "{prefix}"; 
                           or2:idx ?o
                    }}
                }};
                insert data {{
                    graph <http://owlready2/internal> {{
                        [or2:prefix "{prefix}";
                           or2:idx {idx}]
                    }}
                }}
            """)
            return f'{prefix}{idx}'

        # Create a new blank node
        self.execute(f"""
            PREFIX or2: <http://owlready2/internal#>
            insert data {{
                graph <http://owlready2/internal> {{
                    [or2:prefix "{prefix}";
                       or2:idx 1]
                }}
            }}
        """)
        return f'{prefix}1'


    def _refactor(self, storid, new_iri):
        self.storid2iri[storid] = new_iri
        self.iri2storid[new_iri] = storid

    def commit(self):
        pass

    def context_2_user_context(self, c):
        """Fake the user context(ontology)"""
        return self.c2ontology[c]

    def _abbreviate(self, iri, create_if_missing=True):
        # Try get it from a global dict
        storid = _universal_iri_2_abbrev.get(iri) or self.iri2storid.get(iri)

        # Check graph, if exists in graph, create one storid regardless of 'create_if_missing'
        from_clause = '\n\t\t\t\t'.join([f'from named <{graph_iri}>' for graph_iri in self.named_graph_iris])
        if storid is None and not create_if_missing:
            result = self.execute(f"""
                select distinct ?uri {from_clause}
                where {{
                    bind(<{iri}> as ?uri)
                    graph ?g {{
                        {{?uri ?p ?o.}}
                        union
                        {{?s ?uri ?o}}
                        union
                        {{?s ?p ?uri}}
                    }}
                }}
            """)
            if len(result["results"]["bindings"]) > 0:
                create_if_missing = True

        if create_if_missing and storid is None:
            storid = max([0, _next_abb, *[int(i) for i in self.storid2iri.keys()]]) + 1
            self.iri2storid[iri] = storid
            self.storid2iri[storid] = iri

        # print(storid, ' -> ', iri)
        return storid

    def _unabbreviate(self, storid):
        # Skip language tag
        if isinstance(storid, str) and storid.startswith('@'):
            return storid

        if storid is not None and storid < 0:
            if self.debug:
                print(f'!!blank node {storid}')
            return storid
        if isinstance(storid, str) and storid.startswith("@"):
            return storid

        iri = _universal_abbrev_2_iri.get(storid) or self.storid2iri.get(storid)
        return iri

    def _abbreviate_all(self, *iris):
        if len(iris) == 1:
            return self._abbreviate(iris[0])
        else:
            return [self._abbreviate(iri) for iri in iris]

    def _unabbreviate_all(self, *storids):
        if len(storids) == 1:
            return self._unabbreviate(storids[0])
        else:
            return [self._unabbreviate(storid) for storid in storids]

    def new_blank_node(self):
        # Insert a blank node with a newly generated uuid
        uuid = uuid4()
        self.execute(f"""
        PREFIX or2: <http://owlready2/internal#>
        insert data {{
            [or2:uuid "{uuid}"].
        }}
        """, method='update')

        # Get the blank node ent:id
        result = self.execute(f"""
        PREFIX or2: <http://owlready2/internal#>
        PREFIX ent: <http://www.ontotext.com/owlim/entity#>
        select ?id where {{
            ?s or2:uuid "{uuid}".
            ?s ent:id ?id.
        }}
        """)
        bnode_id = -(int(result["results"]["bindings"][0]["id"]["value"]))

        # Delete the UUID triple
        result = self.execute(f"""
        PREFIX or2: <http://owlready2/internal#>
        PREFIX ent: <http://www.ontotext.com/owlim/entity#>
        delete where {{
            ?s or2:uuid "{uuid}".
        }}
        """, method='update')

        print(f'create a new blank node with id {bnode_id}')
        return bnode_id

    def _get_obj_triples_spo_spo(self, s, p, o):
        s_iri, p_iri, o_iri = self._unabbreviate_all(s, p, o)
        query = QueryGenerator.generate_select_query(s_iri, p_iri, o_iri, is_obj=True, graph_iris=self.named_graph_iris)
        result = self.execute(query)

        for item in result["results"]["bindings"]:
            yield item["s"]["storid"], item["p"]["storid"], item["o"]["storid"]

    def _get_data_triples_spod_spod(self, s, p, o, d):
        s_iri, p_iri, d_iri = self._unabbreviate_all(s, p, d)

        query = QueryGenerator.generate_select_query(s_iri, p_iri, o, d_iri,
                                                     is_data=True, graph_iris=self.named_graph_iris)
        result = self.execute(query)

        for item in result["results"]["bindings"]:
            yield item["s"]["storid"], item["p"]["storid"], item["o"]["value"], d or item["o"].get("d")

    def _get_triples_spod_spod(self, s, p, o, d=None):
        if o:
            raise TypeError("'o' should always be None")
        s_iri, p_iri, d_iri = self._unabbreviate_all(s, p, d)

        query = QueryGenerator.generate_select_query(s_iri, p_iri, None, d_iri,
                                                     is_data=True, is_obj=True, graph_iris=self.named_graph_iris)
        result = self.execute(query)

        for item in result["results"]["bindings"]:
            yield item["s"]["storid"], item["p"]["storid"], \
                  item["o"].get("storid") or item["o"]["value"], \
                  d or item["o"].get("d")

    def _get_obj_triples_cspo_cspo(self, c, s, p, o):
        s_iri, p_iri, o_iri = self._unabbreviate_all(s, p, o)
        graph_iri = self.c2ontology[c].graph_iri
        query = QueryGenerator.generate_select_query(s_iri, p_iri, o_iri, is_obj=True, default_graph_iri=graph_iri)
        result = self.execute(query)

        for item in result["results"]["bindings"]:
            yield c, item["s"]["storid"], item["p"]["storid"], item["o"]["storid"]

    def _get_obj_triples_sp_co(self, s, p):
        s_iri, p_iri = self._unabbreviate_all(s, p)

        query = QueryGenerator.generate_select_query(s_iri, p_iri, is_obj=True, graph_iris=self.named_graph_iris)
        result = self.execute(query)

        for item in result["results"]["bindings"]:
            yield self.graph_iri2c[item["g"]["value"]], item["o"]["storid"]

    def _get_triples_s_p(self, s):
        """DISTINCT"""
        s_iri = self._unabbreviate(s)

        query = QueryGenerator.generate_select_query(s_iri, distinct=True, is_data=True, is_obj=True,
                                                     graph_iris=self.named_graph_iris)
        result = self.execute(query)

        # Remove duplicates
        # TODO: Use DISTINCT on SPARQL level and only select '?p'
        p_list = []
        for item in result["results"]["bindings"]:
            p_list.append(item["p"]["storid"])
        return list(dict.fromkeys(p_list))

    def _get_obj_triples_o_p(self, o):
        """DISTINCT"""
        o_iri = self._unabbreviate(o)

        query = QueryGenerator.generate_select_query(o=o_iri, distinct=True, is_obj=True,
                                                     graph_iris=self.named_graph_iris)
        result = self.execute(query)

        # Remove duplicates
        # TODO: Use DISTINCT on SPARQL level and only select '?p'
        p_list = []
        for item in result["results"]["bindings"]:
            p_list.append(item["p"]["storid"])
        return list(dict.fromkeys(p_list))

    def _get_obj_triples_s_po(self, s):
        s_iri = self._unabbreviate(s)

        query = QueryGenerator.generate_select_query(s_iri, is_obj=True, graph_iris=self.named_graph_iris)
        result = self.execute(query)

        for item in result["results"]["bindings"]:
            yield item["p"]["storid"], item["o"]["storid"]

    def _get_obj_triples_sp_o(self, s, p):
        s_iri, p_iri = self._unabbreviate_all(s, p)

        query = QueryGenerator.generate_select_query(s_iri, p_iri, is_obj=True, graph_iris=self.named_graph_iris)
        result = self.execute(query)

        for item in result["results"]["bindings"]:
            yield item["o"]["storid"]

    def _get_data_triples_sp_od(self, s, p):
        s_iri, p_iri = self._unabbreviate_all(s, p)

        query = QueryGenerator.generate_select_query(s_iri, p_iri, is_data=True, graph_iris=self.named_graph_iris)
        result = self.execute(query)

        for item in result["results"]["bindings"]:
            yield item["o"]["value"], item["o"].get("d")

    def _get_triples_sp_od(self, s, p):
        s_iri, p_iri = self._unabbreviate_all(s, p)

        query = QueryGenerator.generate_select_query(s_iri, p_iri,
                                                     is_data=True, is_obj=True, graph_iris=self.named_graph_iris)
        result = self.execute(query)

        for item in result["results"]["bindings"]:
            yield item["o"].get("storid") or item["o"]["value"], \
                  item["o"].get("d")

    def _get_data_triples_s_pod(self, s):
        s_iri = self._unabbreviate(s)

        query = QueryGenerator.generate_select_query(s_iri, is_data=True, graph_iris=self.named_graph_iris)
        result = self.execute(query)

        for item in result["results"]["bindings"]:
            yield item["p"]["storid"], item["o"]["value"], item["o"].get("d")

    def _get_triples_s_pod(self, s):
        s_iri = self._unabbreviate(s)

        query = QueryGenerator.generate_select_query(s_iri, is_data=True, is_obj=True, graph_iris=self.named_graph_iris)
        result = self.execute(query)

        for item in result["results"]["bindings"]:
            yield item["p"]["storid"], \
                  item["o"].get("storid") or item["o"]["value"], \
                  item["o"].get("d")

    def _get_obj_triples_po_s(self, p, o):
        p_iri, o_iri = self._unabbreviate_all(p, o)

        query = QueryGenerator.generate_select_query(None, p_iri, o_iri, is_obj=True, graph_iris=self.named_graph_iris)
        result = self.execute(query)

        for item in result["results"]["bindings"]:
            yield item["s"]["storid"]

    def _get_obj_triples_spi_o(self, s, p, i):
        raise NotImplementedError

    def _get_obj_triples_pio_s(self, p, i, o):
        raise NotImplementedError

    def _get_obj_triple_sp_o(self, s, p):
        s_iri, p_iri = self._unabbreviate_all(s, p)

        query = QueryGenerator.generate_select_query(s_iri, p_iri, limit=1, is_obj=True,
                                                     graph_iris=self.named_graph_iris)
        result = self.execute(query)
        if len(result["results"]["bindings"]) > 0:
            item = result["results"]["bindings"][0]
            return item["o"]["storid"]

    def _get_triple_sp_od(self, s, p):
        s_iri, p_iri = self._unabbreviate_all(s, p)

        query = QueryGenerator.generate_select_query(s_iri, p_iri, limit=1, is_data=True, is_obj=True,
                                                     graph_iris=self.named_graph_iris)
        result = self.execute(query)
        if len(result["results"]["bindings"]) > 0:
            item = result["results"]["bindings"][0]
            return item["o"].get("storid") or item["o"]["value"], item["o"].get("d")

    def _get_data_triple_sp_od(self, s, p):
        s_iri, p_iri = self._unabbreviate_all(s, p)

        query = QueryGenerator.generate_select_query(s_iri, p_iri, limit=1, is_data=True,
                                                     graph_iris=self.named_graph_iris)
        result = self.execute(query)
        if len(result["results"]["bindings"]) > 0:
            item = result["results"]["bindings"][0]
            return item["o"]["value"], item["o"].get("d")

    def _get_obj_triple_po_s(self, p, o):
        p_iri, o_iri = self._unabbreviate_all(p, o)

        query = QueryGenerator.generate_select_query(None, p_iri, o_iri, limit=1, is_obj=True,
                                                     graph_iris=self.named_graph_iris)
        result = self.execute(query)
        if len(result["results"]["bindings"]) > 0:
            item = result["results"]["bindings"][0]
            return item["s"]["storid"]

    def _has_obj_triple_spo(self, s=None, p=None, o=None):
        s_iri, p_iri, o_iri = self._unabbreviate_all(s, p, o)

        query = QueryGenerator.generate_select_query(s_iri, p_iri, o_iri, is_obj=True, limit=1,
                                                     graph_iris=self.named_graph_iris)
        result = self.execute(query)

        return len(result["results"]["bindings"]) > 0

    def _has_data_triple_spod(self, s=None, p=None, o=None, d=None):
        s_iri, p_iri, d_iri = self._unabbreviate_all(s, p, d)

        query = QueryGenerator.generate_select_query(s_iri, p_iri, o, d_iri, is_data=True, limit=1,
                                                     graph_iris=self.named_graph_iris)
        result = self.execute(query)

        return len(result["results"]["bindings"]) > 0

    def _del_obj_triple_raw_spo(self, s, p, o):
        raise NotImplementedError

    def _del_data_triple_raw_spod(self, s, p, o, d):
        raise NotImplementedError

    def _get_obj_triples_transitive_sp(self, s, p):
        s_iri, p_iri = self._unabbreviate_all(s, p)
        from_clauses = []
        for graph_iri in self.named_graph_iris:
            from_clauses.append(f"from named <{graph_iri}>")
        newline = '\n\t\t\t\t'
        query = f"""
                    select ?o
                    {newline.join(from_clauses)}
                    where {{
                        graph ?g {{<{s_iri}> <{p_iri}>+ ?o.}}
                    }}
                """
        result = self.execute(query)
        for item in result["results"]["bindings"]:
            yield item["o"]["storid"]

    def _get_obj_triples_transitive_po(self, p, o):
        p_iri, o_iri = self._unabbreviate_all(p, o)
        from_clauses = []
        for graph_iri in self.named_graph_iris:
            from_clauses.append(f"from named <{graph_iri}>")
        newline = '\n\t\t\t\t'
        query = f"""
            select ?s
            {newline.join(from_clauses)}
            where {{
                graph ?g {{?s <{p_iri}>+ <{o_iri}>}}
            }}
        """
        result = self.execute(query)
        for item in result["results"]["bindings"]:
            yield item["s"]["storid"]

    def restore_iri(self, storid, iri):
        assert (storid > 0)
        self.storid2iri[storid] = iri
        self.iri2storid[iri] = storid

    def destroy_entity(self, storid, destroyer, relation_updater, undoer_objs=None, undoer_datas=None):
        raise NotImplementedError

    def _iter_ontology_iri(self, c=None):
        from_clauses = []
        if c:
            return self.c2ontology[c].base_iri
        else:
            for c in self.c2ontology:
                yield c, self.c2ontology[c].base_iri

    def _iter_triples(self, quads=False, sort_by_s=False, c=None):
        # TODO: Check is the order really matters?
        if c:
            query = QueryGenerator.generate_select_query(is_data=True, is_obj=True,
                                                         default_graph_iri=self.c2ontology[c].graph_iri,
                                                         order_by='asc(?s)' if sort_by_s else None)
        else:
            query = QueryGenerator.generate_select_query(is_data=True, is_obj=True, graph_iris=self.named_graph_iris,
                                                         order_by='asc(?s)' if sort_by_s else None)
        result = self.execute(query)

        for item in result["results"]["bindings"]:
            spod = [item["s"]["storid"], item["p"]["storid"],
                    item["o"].get("storid") or item["o"]["value"],
                    item["o"].get("d")]
            if quads:
                yield c if c else self._abbreviate(item["g"]["value"]), *spod
            else:
                yield spod

    def get_fts_prop_storid(self):
        raise NotImplementedError

    def enable_full_text_search(self, prop_storid):
        raise NotImplementedError

    def disable_full_text_search(self, prop_storid):
        raise NotImplementedError

    # Optimized queries for multiple subjects/predicates
    def _get_data_triples_sp_sod(self, s: list, p: list):
        """Take a list of subjects and a predicate."""
        if not isinstance(s, list):
            s = [s]
        if not isinstance(p, list):
            p = [p]
        s_iris = self._unabbreviate_all(*s)
        p_iris = self._unabbreviate_all(*p)

        query = QueryGenerator.generate_select_query(s_iris, p_iris, is_data=True, graph_iris=self.named_graph_iris)

        result = self.execute(query)
        for item in result["results"]["bindings"]:
            yield item["s"]["storid"], item["o"]["value"], item["o"].get("d")

    def _get_obj_triples_sp_cspo(self, s: list, p: list):
        """Take a list of subjects and a predicate."""
        if not isinstance(s, list):
            s = [s]
        if not isinstance(p, list):
            p = [p]
        s_iris = self._unabbreviate_all(*s)
        p_iris = self._unabbreviate_all(*p)

        query = QueryGenerator.generate_select_query(s_iris, p_iris, is_obj=True, graph_iris=self.named_graph_iris)
        result = self.execute(query)

        for item in result["results"]["bindings"]:
            yield self.graph_iri2c[item["g"]["value"]], item["s"]["storid"], item["p"]["storid"], item["o"]["storid"]

    def _parse_bnode(self, bnode):
        result = self.execute(f"""
            PREFIX ent: <http://www.ontotext.com/owlim/entity#>
            select ?g
            where {{
                graph ?g {{
                    {{?s ?p ?o. ?s ent:id {bnode}.}}
                    union 
                    {{?s ?p ?o. ?o ent:id {bnode}.}}
                }}
            }} limit 1
        """)
        items = result["results"]["bindings"]
        if len(items) == 1:
            return self.c2ontology[self.graph_iri2c[items[0]["g"]["value"]]]._parse_bnode(bnode)
