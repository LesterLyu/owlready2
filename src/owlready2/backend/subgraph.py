from SPARQLWrapper import SPARQLWrapper, JSON, POST
from owlready2.base import *
from owlready2.driver import BaseMainGraph, BaseSubGraph
from owlready2.util import FTS, _LazyListMixin
from owlready2.base import _universal_abbrev_2_iri, _universal_iri_2_abbrev, _next_abb

from .utils import QueryGenerator
from time import time
import multiprocessing
import re


class SparqlSubGraph(BaseSubGraph):
    def __init__(self, parent, onto, c):
        super().__init__(parent, onto)
        self.parent = parent
        self.onto = onto
        self.c = c
        self.graph_iri = onto.graph_iri

    def execute(self, *args, **kwargs):
        if self.parent.debug:
            import inspect
            print(f'Called from: {type(self).__name__}.{inspect.currentframe().f_back.f_code.co_name}(' + ', '.join(
                inspect.currentframe().f_back.f_code.co_varnames) + ')')
        return self.parent.execute(*args, **kwargs)

    def _abbreviate(self, iri, create_if_missing=True):
        return self.parent._abbreviate(iri, create_if_missing)

    def _unabbreviate(self, storid):
        return self.parent._unabbreviate(storid)

    def _abbreviate_all(self, *iris):
        return self.parent._unabbreviate_all(*iris)

    def _unabbreviate_all(self, *storids):
        return self.parent._unabbreviate_all(*storids)

    def _new_numbered_iri(self, prefix):
        return self.parent._new_numbered_iri(prefix)

    def _refactor(self, storid, new_iri):
        return self.parent._refactor(storid, new_iri)

    def _iter_triples(self, quads=False, sort_by_s=False):
        return self.parent._iter_triples(quads, sort_by_s, self.c)

    def create_parse_func(self, filename=None, delete_existing_triples=True,
                          datatype_attr="http://www.w3.org/1999/02/22-rdf-syntax-ns#datatype"):
        objs = []
        datas = []

        if delete_existing_triples:
            # Delete the whole named graph!
            self.execute(f"DROP GRAPH <{self.graph_iri}>")

        def _abbreviate(iri):
            return self._abbreviate(iri)

        def insert_objs():
            triples = []
            for spo in objs:
                s, p, o = self._unabbreviate_all(*spo)
                triples.append(f'<{s}> <{p}> <{o}>.')

            newline = '\n\t\t\t\t'
            self.execute(f"""
                insert data {{
                    graph <{self.graph_iri}> {{ {newline.join(triples)} }}
                }}
            """, method='update')
            objs.clear()

        def insert_datas():
            triples = []
            for spod in datas:
                o = spod[2]
                s, p, d = self._unabbreviate_all(spod[0], spod[1], spod[3])
                triples.append(f'<{s}> <{p}> {QueryGenerator.serialize_to_sparql_type_with_datetype(o, d)}.')

            newline = '\n\t\t\t\t'
            self.execute(f"""
                insert data {{
                    graph <{self.graph_iri}> {{ {newline.join(triples)} }}
                }}
            """, method='update')
            datas.clear()

        # TODO: Improve performance: Do we really need to abbreviate IRIs?
        def on_prepare_obj(s, p, o):
            if isinstance(s, str):
                s = _abbreviate(s)
            if isinstance(o, str):
                o = _abbreviate(o)
            objs.append((s, _abbreviate(p), o))
            if len(objs) > 1000:
                insert_objs()

        def on_prepare_data(s, p, o, d):
            if isinstance(s, str):
                s = _abbreviate(s)
            if d and (not d.startswith("@")):
                d = _abbreviate(d)
            datas.append((s, _abbreviate(p), o, d))
            if len(datas) > 1000:
                insert_datas()

        def on_finish():
            if filename:
                date = os.path.getmtime(filename)
            else:
                date = time()

            insert_objs()
            insert_datas()

            # TODO: Get base IRI
            # There might be several owl:Ontology in the named graph
            # Match a correct one

            # TODO: Set last update time
            return self.graph_iri

        return objs, datas, on_prepare_obj, on_prepare_data, insert_objs, insert_datas, self.parent.new_blank_node, \
               _abbreviate, on_finish

    def update_graph_iri(self, new_graph_iri):
        """Rename graph"""
        self.execute(f'MOVE <{self.graph_iri}> TO <{new_graph_iri}>', method='update')
        del self.parent.graph_iri2c[self.graph_iri]
        self.parent.graph_iri2c[new_graph_iri] = self.c
        self.parent.named_graph_iris.remove(self.graph_iri)

        self.graph_iri = new_graph_iri
        self.parent.named_graph_iris.append(new_graph_iri)

    def context_2_user_context(self, c):
        return self.parent.context_2_user_context(c)

    def add_ontology_alias(self, iri, alias):
        # TODO
        # This is invoked when the imported Ontology changes base_iri
        # Set an IRI alias that points to the same Ontology base_iri
        raise NotImplementedError

    def get_last_update_time(self):
        """
        Return 0 if never loaded. Otherwise return the last update time.
        """
        # TODO
        return 0

    def set_last_update_time(self, t):
        # TODO
        pass

    def destroy(self):
        raise NotImplementedError

    def _set_obj_triple_raw_spo(self, s, p, o):
        if (s is None) or (p is None) or (o is None):
            raise ValueError
        s_iri, p_iri, o_iri = self._unabbreviate_all(s, p, o)
        delete_query = QueryGenerator.generate_delete_query(s_iri, p_iri, default_graph_iri=self.graph_iri)
        insert_query = QueryGenerator.generate_insert_query(s_iri, p_iri, o_iri, default_graph_iri=self.graph_iri)
        self.execute(delete_query, insert_query, method='update')

    def _add_obj_triple_raw_spo(self, s, p, o):
        if (s is None) or (p is None) or (o is None):
            raise ValueError
        s_iri, p_iri, o_iri = self._unabbreviate_all(s, p, o)
        insert_query = QueryGenerator.generate_insert_query(s_iri, p_iri, o_iri, default_graph_iri=self.graph_iri)
        self.execute(insert_query, method='update')

    def _del_obj_triple_raw_spo(self, s=None, p=None, o=None):
        s_iri, p_iri, o_iri = self._unabbreviate_all(s, p, o)
        delete_query = QueryGenerator.generate_delete_query(s, p, o, default_graph_iri=self.graph_iri)
        self.execute(delete_query, method='update')

    def _set_data_triple_raw_spod(self, s, p, o, d):
        if (s is None) or (p is None) or (o is None) or (d is None):
            raise ValueError
        s_iri, p_iri, d_iri = self._unabbreviate_all(s, p, d)
        delete_query = QueryGenerator.generate_delete_query(s_iri, p_iri, default_graph_iri=self.graph_iri)
        insert_query = QueryGenerator.generate_insert_query(s_iri, p_iri, o, d_iri, default_graph_iri=self.graph_iri)
        self.execute(delete_query, insert_query, method='update')

    def _add_data_triple_raw_spod(self, s, p, o, d):
        if (s is None) or (p is None) or (o is None) or (d is None):
            raise ValueError
        s_iri, p_iri, d_iri = self._unabbreviate_all(s, p, d)
        insert_query = QueryGenerator.generate_insert_query(s_iri, p_iri, o, d_iri, default_graph_iri=self.graph_iri)
        self.execute(insert_query, method='update')

    def _del_data_triple_raw_spod(self, s, p, o, d):
        s_iri, p_iri = self._unabbreviate_all(s, p)
        o_data = None
        if o and d:
            o_data = QueryGenerator.serialize_to_sparql_type_with_datetype(o, self._unabbreviate(d))

        delete_query = QueryGenerator.generate_delete_query(s_iri, p_iri, o_data, default_graph_iri=self.graph_iri)
        self.execute(delete_query, method='update')

    def _has_obj_triple_spo(self, s=None, p=None, o=None):
        s_iri, p_iri, o_iri = self._unabbreviate_all(s, p, o)

        query = QueryGenerator.generate_select_query(s_iri, p_iri, o_iri, is_obj=True, limit=1,
                                                     default_graph_iri=self.graph_iri)
        result = self.execute(query)
        return len(result["results"]["bindings"]) > 0

    def _has_data_triple_spod(self, s=None, p=None, o=None, d=None):
        s_iri, p_iri, d_iri = self._unabbreviate_all(s, p, d)

        query = QueryGenerator.generate_select_query(s_iri, p_iri, o, d_iri, is_data=True, limit=1,
                                                     default_graph_iri=self.graph_iri)
        result = self.execute(query)
        return len(result["results"]["bindings"]) > 0

    def _get_obj_triples_spo_spo(self, s=None, p=None, o=None):
        s_iri, p_iri, o_iri = self._unabbreviate_all(s, p, o)

        query = QueryGenerator.generate_select_query(s_iri, p_iri, o_iri, is_obj=True, default_graph_iri=self.graph_iri)
        result = self.execute(query)
        for item in result["results"]["bindings"]:
            yield item["s"]["storid"], item["p"]["storid"], item["o"]["storid"]

    def _get_data_triples_spod_spod(self, s, p, o, d=None):
        s_iri, p_iri, d_iri = self._unabbreviate_all(s, p, d)

        query = QueryGenerator.generate_select_query(s_iri, p_iri, o, d_iri, is_data=True,
                                                     default_graph_iri=self.graph_iri)
        result = self.execute(query)
        for item in result["results"]["bindings"]:
            yield item["s"]["storid"], item["p"]["storid"], item["o"].get("storid") or item["o"]["value"], \
                  d or item["o"]["d"]

    def _get_triples_spod_spod(self, s, p, o, d=""):
        if o:
            raise TypeError("'o' should always be None")
        s_iri, p_iri, d_iri = self._unabbreviate_all(s, p, d)

        query = QueryGenerator.generate_select_query(s_iri, p_iri, None, d_iri,
                                                     is_data=True, is_obj=True, default_graph_iri=self.graph_iri)
        result = self.execute(query)

        for item in result["results"]["bindings"]:
            yield item["s"]["storid"], item["p"]["storid"], \
                  item["o"].get("storid") or item["o"]["value"], \
                  d or item["o"].get("d")

    def _get_obj_triples_s_po(self, s):
        s_iri = self._unabbreviate(s)

        query = QueryGenerator.generate_select_query(s_iri, is_obj=True, default_graph_iri=self.graph_iri)
        result = self.execute(query)

        for item in result["results"]["bindings"]:
            yield item["p"]["storid"], item["o"]["storid"]

    def _get_obj_triples_sp_o(self, s, p):
        s_iri, p_iri = self._unabbreviate_all(s, p)

        query = QueryGenerator.generate_select_query(s_iri, p_iri, is_obj=True, default_graph_iri=self.graph_iri)
        result = self.execute(query)

        for item in result["results"]["bindings"]:
            yield item["o"]["storid"]

    def _get_obj_triples_sp_co(self, s, p):
        s_iri, p_iri = self._unabbreviate_all(s, p)

        query = QueryGenerator.generate_select_query(s_iri, p_iri, is_obj=True, default_graph_iri=self.graph_iri)
        result = self.execute(query)

        for item in result["results"]["bindings"]:
            yield self.c, item["o"]["storid"]

    def _get_triples_sp_od(self, s, p):
        s_iri, p_iri = self._unabbreviate_all(s, p)

        query = QueryGenerator.generate_select_query(s_iri, p_iri, is_data=True, is_obj=True,
                                                     default_graph_iri=self.graph_iri)
        result = self.execute(query)

        for item in result["results"]["bindings"]:
            yield item["o"].get("storid") or item["o"]["value"], \
                  item["o"].get("d")

    def _get_data_triples_sp_od(self, s, p):
        s_iri, p_iri = self._unabbreviate_all(s, p)

        query = QueryGenerator.generate_select_query(s_iri, p_iri, is_data=True, default_graph_iri=self.graph_iri)
        result = self.execute(query)

        for item in result["results"]["bindings"]:
            yield item["o"]["storid"], item["o"]["d"]

    def _get_data_triples_s_pod(self, s):
        s_iri = self._unabbreviate(s)

        query = QueryGenerator.generate_select_query(s_iri, is_data=True, default_graph_iri=self.graph_iri)
        result = self.execute(query)

        for item in result["results"]["bindings"]:
            yield item["p"]["storid"], item["o"]["value"], item["o"]["d"]

    def _get_triples_s_pod(self, s):
        raise NotImplementedError

    def _get_obj_triples_po_s(self, p, o):
        p_iri, o_iri = self._unabbreviate_all(p, o)

        query = QueryGenerator.generate_select_query(None, p_iri, o_iri, is_obj=True, default_graph_iri=self.graph_iri)
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
                                                     default_graph_iri=self.graph_iri)
        result = self.execute(query)
        if len(result["results"]["bindings"]) > 0:
            return result["results"]["bindings"][0]["o"]["storid"]

    def _get_triple_sp_od(self, s, p):
        s_iri, p_iri = self._unabbreviate_all(s, p)

        query = QueryGenerator.generate_select_query(s_iri, p_iri, limit=1,
                                                     is_data=True, is_obj=True, default_graph_iri=self.graph_iri)
        result = self.execute(query)
        if len(result["results"]["bindings"]) > 0:
            item = result["results"]["bindings"][0]
            return item["o"]["storid"] if item["o"].get("storid") else item["o"]["value"], item["o"].get("d")

    def _get_data_triple_sp_od(self, s, p):
        s_iri, p_iri = self._unabbreviate_all(s, p)

        query = QueryGenerator.generate_select_query(s_iri, p_iri, limit=1, is_data=True,
                                                     default_graph_iri=self.graph_iri)
        result = self.execute(query)
        if len(result["results"]["bindings"]) > 0:
            item = result["results"]["bindings"][0]
            return item["o"]["value"], item["o"]["d"]

    def _get_obj_triple_po_s(self, p, o):
        p_iri, o_iri = self._unabbreviate_all(p, o)

        query = QueryGenerator.generate_select_query(None, p_iri, o_iri, limit=1, is_obj=True,
                                                     default_graph_iri=self.graph_iri)
        result = self.execute(query)
        if len(result["results"]["bindings"]) > 0:
            return result["results"]["bindings"][0]["s"]["storid"]

    def _get_triples_s_p(self, s):
        """DISTINCT"""
        s_iri = self._unabbreviate_all(s)

        query = QueryGenerator.generate_select_query(s_iri, distinct=True,
                                                     is_data=True, is_obj=True, default_graph_iri=self.graph_iri)
        result = self.execute(query)

        # Remove duplicates
        # TODO: Use DISTINCT on SPARQL level and only select '?p'
        p_list = []
        for item in result["results"]["bindings"]:
            p_list.append(item["p"]["storid"])
        return list(dict.fromkeys(p_list))

    def _get_obj_triples_o_p(self, o):
        """DISTINCT"""
        o_iri = self._unabbreviate_all(o)

        query = QueryGenerator.generate_select_query(o=o_iri, distinct=True, is_obj=True,
                                                     default_graph_iri=self.graph_iri)
        result = self.execute(query)

        # Remove duplicates
        # TODO: Use DISTINCT on SPARQL level and only select '?p'
        p_list = []
        for item in result["results"]["bindings"]:
            p_list.append(item["p"]["storid"])
        return list(dict.fromkeys(p_list))

    def _get_obj_triples_cspo_cspo(self, c, s, p, o):
        return [(self.c, s, p, o) for (s, p, o) in self._get_obj_triples_spo_spo(s, p, o)]

    def _iter_ontology_iri(self, c=None):
        return self.parent._iter_ontology_iri(c)

    def __len__(self):
        result = self.execute(f"""
            select (count(?s) as ?count)
            from <{self.graph_iri}>
            where {{
                graph ?g {{?s ?p ?o .}}
            }}
            """)
        return int(result['results']['bindings'][0]['count']['value'])
