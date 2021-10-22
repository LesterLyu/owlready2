## Notes
### `triplelite.py`
 An SQLite Store

Class `Graph`
> Note: context: `c`, subject `s`, predicate `p`, object `o`, datatype `d`.
>   
> See also [Triplelite SQLite schema](./triplelite.md).
- `__init__(self, filename, clone=None, exclusive=True, sqlite_tmp_dir="", world=None, profiling=False, read_only=False)` constructor
  - Manage the connection to the SQLite file, in memory or on disk.
  - Initialize the database with predefined schema. L169-201
  - Upgrade previous database schema to latest schema (to version 9). L218-411
- `analyze(self)` Data integrity check, make sure `sqlite_stat1` table is consistent with other tables, why?. L416
- invoked when database is opened and closed, and when the number of the newly added triples is greater than 1000.
- `acquire_write_lock(self), release_write_lock(self), has_write_lock(self)` Locking protocol. Lock the `Graph`. 
  Make the library supports parallelism. L455-L461
- `select_abbreviate_method(self)` Make `world`, `subgraph`, `subgraph.onto` uses the `_abbreviate(...)` and
`_unabbreviate(...)` method defined in triplelite. L463-483
- `_abbreviate(self, iri, create_if_missing=True)` Mapping between external IRI to an internal id `storid`.
  Map IRI to `storid`.  L513
- `_unabbreviate(self, storid)` Mapping between internal id `storid` to an external IRI. Map `storid` to IRI. L523
- `fix_base_iri(self, base_iri)` Check and make sure the IRI is consistent in some format. 
  Do nothing and return the given IRI if the given IRI ends with `#` or `/`. 
  Otherwise, figure out whether to use `#` or `/` base on the existed IRIs stored in the `resourses` table. L485
- `sub_graph(self, onto)`  Look for an existing context `c` based on the given base_iri `onto.base_iri` from the `ontologies` table.
  If the `base_iri` is not in the `ontologies` table, create one. Return a `SubGraph` instance with the given `onto`. L495
- `ontologies_iris(self)` Return all IRIs in the `ontologies` table as a Python generator. L509
- `get_storid_dict(self)` Return a storid to IRI mapping. L538, *unused*
- `_new_numbered_iri(self, prefix)` Generate a new numbered IRI for the given `prefix`, based on `last_numbered_iri` table. 
  i.e. `new_numbered_iri('http://example.com/drug')` returns IRI 'http://example.com/drug1' L558-L581
- `_refactor(self, storid, new_iri)` set the storid with a new IRI in the `resources` table. (Update the specific `storid`). L585
- `commit(self)` Commit all changes, this is called when save the SQLite database file or export as rdfxml/ntriples/... format. L594
- `context_2_user_context(self)` Not sure, map the context `c` to an IRI. L600
- `new_blank_node(self)` Generate a new blank node id and return it (always negative).
- `_get_obj_triple(s)_xxx_xxx(self, c, s, p, o)`  Return all triples ([context, ]subject, predicate, object) 
  the `objs` table, which only contains the triples that have an **object** property.
- `_get_data_triple(s)_xxx_xxx(self, c, s, p, o, d)` Return all triples ([context, ]subject, predicate, object[, datatype]) 
  from the `datas` table, which only contains the triples that have a **data** property.
- `_get_triple(s)_xxx_xxx(self, c, s, p, o, d)` Return all triples ([context, ]subject, predicate, object[, datatype]) 
  from the `quads` view.
- `_has_obj_triple_spo(self, s=None, p=None, o=None)` Return True if the given triple is found in the `objs` table. 
  `s`, `p`, `o` could be None.
- `_has_data_triple_spod(self, s=None, p=None, o=None, d=None)`  Return `True` if the given triple is found in the `datas` table.
  `s`, `p`, `o` could be None.
- `_del_obj_triple_raw_spo(self, s=None, p=None, o=None)` Delete the given triples (s, p, o), `s`, `p` and `o` could be `None`.
- `__del_data_triple_raw_spod(self, s=None, p=None, o=None, d=None)` Delete the given triples (s, p, o, d), `s`, `p`, `o` and `d` could be `None`.
- `_punned_entities(self)` Return all IRIs that is a named individual(`owl:NamedIndividual`) and also an ontology class(`owl:Class`) *unused*
- `__bool__(self)` Always return true. L860
- `__len__(self)` Return the number of **all** triples. L861
- `_get_obj_triples_transitive_sp(self, s, p)` Return all triples that connect to the given subject and predicate. L893
- `_get_obj_triples_transitive_po(self, p, o)` Return all triples that connect to the given predicate and subject. L902
- `_destroy_collect_storids(self, destroyed_storids, modified_relations, storid)` **?** Something related to blank node. L922
- `_rdf_list_analyze(self, blank)` **?** Something related to blank node, used in `_destroy_collect_storids()`. L957
- `restore_iri(self, storid, iri)` Insert `(storid, iri)` into the `resources` table.
- `destroy_entity(storid, destroyer, relation_updater, undoer_objs=None, undoer_datas=None)` 
Destroy an IRI (given as `storid`) and remove all related triples & invoke callbacks `destroyer(storid)` and 
`relation_updater(destroyed_storids, s, ps)`. L987
- `_iter_triples(self, quads=False, sort_by_s=False, c=None)` Return an iterator (SQLite cursor) to iterate all triples in `quads` view. L1044
- `get_fts_prop_storid(self)` Return `self.prop_fts`. Something related to *full text search*. L1057
- `enable_full_text_search(self, prop_storid)` **?**
- `disable_full_text_search(self, prop_storid)` **?**

Class `SubGraph`: Subgraph from `Graph`.
> The sql statement in the subgraph always contains the context `c`. This is used when import an ontology file.
- `__init__(self, parent, onto, c, db)` Create a subgraph from a main graph, given the main graph `parent`, base ontology `onto`, context `c` L1115
- `create_parse_func(self, filename=None, delete_existing_triples=True,...)` Create a set of parse helper functions and variables for a local ontology file `filename`. L1126
- `context_2_user_context(self, c)` Call the main graph `context_2_user_context(...)`. Map the context `c` to an IRI.
- `add_ontology_alias(self, iri, alias)`
- `get_last_update_time(self)` Get last update time of this ontology.
- `set_last_update_time(self)` Set last update time of this ontology.
- `destroy(self)` Remove everything that is in this ontology context.
- `_set_obj_triple_raw_spo(self, s, p, o)`
- `_add_obj_triple_raw_spo(self, s, p, o)`
- `_del_obj_triple_raw_spo(self, s=None, p=None, o=None)`
- `_set_data_triple_raw_spod(self, s, p, o, d)`
- `_add_data_triple_raw_spod(self,  s, p, o, d)`
- `_del_data_triple_raw_spod(self,  s, p, o, d)`
- `_has_obj_triple_spo(self, s=None, p=None, o=None)`
- `_has_data_triple_spod(self, s=None, p=None, o=None, d=None)`
- `_get_obj_triple(s)_xxx_xxx(self, s, p, o)`  Return all triples ([context, ]subject, predicate, object) 
  the `objs` table, which only contains the triples that have an **object** property.
- `_get_data_triple(s)_xxx_xxx(self, s, p, o, d)` Return all triples ([context, ]subject, predicate, object[, datatype]) 
  from the `datas` table, which only contains the triples that have a **data** property.
- `_get_triple(s)_xxx_xxx(self, s, p, o, d)` Return all triples ([context, ]subject, predicate, object[, datatype]) 
  from the `quads` view.
- `search(self, prop_vals)` **unused**
- `__len__(self)` Return the number of **all** triples in current context.
- `_iter_ontology_iri(self, c=None)` Return an iterator for all ontology IRIs `(c, iri)`.
  If the context `c` is given, only one IRI is returned.
- `_refactor(self, storid, new_iri)` Call the main graph `_refactor(...)`. 
  Set the storid with a new IRI in the `resources` table. (Update the specific `storid`).
- `_get_obj_triples_transitive_sp(self, s, p)` Return all triples that connect to the given subject and predicate in the current context.
- `_get_obj_triples_transitive_po(self, p, o)` Return all triples that connect to the given predicate and subject in the current context.
    
Class `_SearchMixin`: Inherits `list`

Class `_PopulatedSearchList`: **?**

Class `_SearchList`: Construct SQL statement for `graph.search(...)`.

Class `_PopulatedUnionSearchList` **?**
  
Class `_UnionSearchList` Construct UNION SQL statement.
  
Class `_PopulatedIntersectionSearchList` **?**
  
Class `_IntersectionSearchList` Construct Intersection SQL statement.

### `rdflib_store.py`

- class `TripleLiteRDFlibStore` implements the [Abstracted Store API `rdflib.store.Store`](https://rdflib.readthedocs.io/en/stable/apidocs/rdflib.html#rdflib.store.Store)
- class `TripleLiteRDFlibGraph` inherits [`rdflib.Graph`](https://rdflib.readthedocs.io/en/stable/apidocs/rdflib.html#rdflib.Graph).
  Adds `query_owlready(...)` method that automatically converts the results from `query()` to Python and Owlready2.
  
### `namespace.py`
  
  The main owlready2 entrance 
  - Include the predefined ontologies. L30
  
  Class `Namespace`
  
  Class `_GraphManager`: Abstract class related to `Graph`.
  - `_abbreviate`
  - `_unabbreviate`
  - `_get_obj_triple(s)_xxx_xxx`
  - `_get_data_triple(s)_xxx_xxx`
  - `_has_data_triple_spod`
  - `get_triples` Implemented
  - `_refactor`
  - `_get_annotation_axioms` ?
  - `...`

  Class `World`: Inherits `GraphManager`
  
  Class `Ontology`: Inherits `Namespace` and `GraphManager`, main entrance of owlready2

  Class `Metadata`

### `individual.py`
Class `Thing`: The class for user to define ontology class, instance of class `Thing` is also the *Named Individual* of the ontology class.
- `__setattr__(self, attr, value)` Does not check ontology consistent.

Class `NoThing` ?

Class `FusionClass` ?

### `class_construct.py`
The Python definition of the owl spec are defined here. (Restrictions, Inverse, ...)

### `prop.py`
Defines OWL properties in Python.

### `driver.py`
Parse & Serialize RDF.

### `owlxml_2_ntriples.py`
owlxml parser. 

### `annotation.py` 
?

### `base.py`
Some global variables and helpers.

### `util.py`
Some helper classes.

### `disjoint.py`
Class `AllDisjoint`

### `observe.py` 
?

### `reasoning.py`
Calls an external reasoner and parse the result.

### `rply.py` `owlready2/*`
SPARQL parser & lexer.

--- 
### `dl_render.py`
Render ontology class in console (print).

###  `editor.py`, `instance_editor.py`, `instance_editor_qt.py`
Some GUI for editing ontology.

---
### `ontos/*.owl`: 
Predifined ontologies used in owlready2
 - dc.owl
 - dcam.owl
 - dcmitype.owl
 - dcterms.owl
 - owlready_ontology.owl

### `hermit/*`:
Hermit reasoner binaries in Java