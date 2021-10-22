from SPARQLWrapper import SPARQLWrapper, JSON, POST
from owlready2.base import *
from owlready2.driver import BaseMainGraph, BaseSubGraph
from owlready2.driver import _guess_format, _save
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
        raise NotImplementedError

    def context_2_user_context(self, c):
        return self.parent.context_2_user_context(c)

    def add_ontology_alias(self, iri, alias):
        raise NotImplementedError

    def get_last_update_time(self):
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
        self.execute(delete_query, insert_query)

    def _add_obj_triple_raw_spo(self, s, p, o):
        if (s is None) or (p is None) or (o is None):
            raise ValueError
        s_iri, p_iri, o_iri = self._unabbreviate_all(s, p, o)
        insert_query = QueryGenerator.generate_insert_query(s_iri, p_iri, o_iri, default_graph_iri=self.graph_iri)
        self.execute(insert_query)

    def _del_obj_triple_raw_spo(self, s=None, p=None, o=None):
        s_iri, p_iri, o_iri = self._unabbreviate_all(s, p, o)
        delete_query = QueryGenerator.generate_delete_query(s, p, o, default_graph_iri=self.graph_iri)
        self.execute(delete_query)

    def _set_data_triple_raw_spod(self, s, p, o, d):
        if (s is None) or (p is None) or (o is None) or (d is None):
            raise ValueError
        s_iri, p_iri, d_iri = self._unabbreviate_all(s, p, d)
        delete_query = QueryGenerator.generate_delete_query(s_iri, p_iri, default_graph_iri=self.graph_iri)
        insert_query = QueryGenerator.generate_insert_query(s_iri, p_iri, o, d_iri, default_graph_iri=self.graph_iri)
        self.execute(delete_query, insert_query)

    def _add_data_triple_raw_spod(self, s, p, o, d):
        if (s is None) or (p is None) or (o is None) or (d is None):
            raise ValueError
        s_iri, p_iri, d_iri = self._unabbreviate_all(s, p, d)
        insert_query = QueryGenerator.generate_insert_query(s_iri, p_iri, o, d_iri, default_graph_iri=self.graph_iri)
        self.execute(insert_query)

    def _del_data_triple_raw_spod(self, s, p, o, d):
        s_iri, p_iri = self._unabbreviate_all(s, p)
        o_data = None
        if o and d:
            o_data = QueryGenerator.serialize_to_sparql_type_with_datetype(o, self._unabbreviate(d))

        delete_query = QueryGenerator.generate_delete_query(s_iri, p_iri, o_data, default_graph_iri=self.graph_iri)
        self.execute(delete_query)

    def _has_obj_triple_spo(self, s=None, p=None, o=None):
        s_iri, p_iri, o_iri = self._unabbreviate_all(s, p, o)

        query = QueryGenerator.generate_select_query(s_iri, p_iri, o_iri, is_obj=True, limit=1,
                                                     default_graph_iri=self.graph_iri)
        result = self.execute(query)
        return len(result["results"]["bindings"]) > 0

    def _has_data_triple_spod(self, s=None, p=None, o=None, d=None):
        raise NotImplementedError

    def _get_obj_triples_spo_spo(self, s=None, p=None, o=None):
        raise NotImplementedError

    def _get_data_triples_spod_spod(self, s, p, o, d=""):
        raise NotImplementedError

    def _get_triples_spod_spod(self, s, p, o, d=""):
        raise NotImplementedError

    def _get_obj_triples_s_po(self, s):
        s_iri = self._unabbreviate(s)

        query = QueryGenerator.generate_select_query(s_iri, is_obj=True, default_graph_iri=self.graph_iri)
        result = self.execute(query)

        for item in result["results"]["bindings"]:
            yield item["p"]["storid"], item["o"]["storid"]

    def _get_obj_triples_sp_o(self, s, p):
        raise NotImplementedError

    def _get_obj_triples_sp_co(self, s, p):
        s_iri, p_iri = self._unabbreviate_all(s, p)

        query = QueryGenerator.generate_select_query(s_iri, p_iri, is_obj=True, default_graph_iri=self.graph_iri)
        result = self.execute(query)

        for item in result["results"]["bindings"]:
            yield self.c, item["o"]["storid"]

    def _get_triples_sp_od(self, s, p):
        raise NotImplementedError

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
        raise NotImplementedError

    def _get_triple_sp_od(self, s, p):
        raise NotImplementedError

    def _get_data_triple_sp_od(self, s, p):
        raise NotImplementedError

    def _get_obj_triple_po_s(self, p, o):
        raise NotImplementedError

    def _get_triples_s_p(self, s):
        raise NotImplementedError

    def _get_obj_triples_o_p(self, o):
        raise NotImplementedError

    def _get_obj_triples_cspo_cspo(self, c, s, p, o):
        raise NotImplementedError

    def __len__(self):
        raise NotImplementedError
