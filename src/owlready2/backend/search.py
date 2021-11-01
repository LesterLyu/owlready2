from owlready2.util import FirstList, _LazyListMixin


class SparqlSearch:

    @staticmethod
    def search(world, _use_str_as_loc_str=True, _case_sensitive=True, _bm25=False, **kwargs):
        pass


class _SearchMixin(list):

    def _get_content(self):
        raise NotImplementedError

    def first(self):
        raise NotImplementedError

    def has_bm25(self):
        return False


class _PopulatedSearchList(FirstList):

    def has_bm25(self): return self.bm25


class _SearchList(FirstList, _SearchMixin, _LazyListMixin):

    def __init__(self):
        raise NotImplementedError

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
