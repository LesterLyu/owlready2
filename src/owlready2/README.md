## Notes
### `triplelite.py`
 An SQLite Store

 Class `Graph`
  - `__init__` constructor
      - Manage the connection to the SQLite file, in memory or on disk.
      - Initialize the database with predefined schema. L169-201
      - Upgrade previous database schema to latest schema (to version 9). L218-411
  - `analyze()` Analyze the database, make sure `sqlite_stat1` table is consistent with other tables, why?. L416
  - Handle write lock. L455-L461
  - `select_abbreviate_method(self)` Make `world`, `subgraph`, `subgraph.onto` uses the `_abbreviate(...)` and
    `_unabbreviate(...)` method defined in triplelite. L463-483
  - `_abbreviate(self, iri)` Map IRI to `storid`.  L513
  - `_unabbreviate(self, storid)` Map `storid` to IRI. L523
  - `fix_base_iri(self, base_iri)` Do nothing and return the given IRI if the given IRI ends with `#` or `/`. 
    Otherwise, figure out whether to use `#` or `/` base on the existed IRIs stored in the `resourses` table. L485
  - `sub_graph(self, onto)`  Look for an existing context `c` based on the given base_iri `onto.base_iri` from the `ontologies` table.
   If the `base_iri` is not in the `ontologies` table, create one. Return a `SubGraph` instance with the given `onto`. L495
  - `ontologies_iris(self)` Return an IRI generator. L509
  - `get_storid_dict(self)` Return a storid to IRI dictionary. L538, *unused*
  - `_new_numbered_iri(self, prefix)` Generate a new numbered IRI for the given `prefix`, based on `last_numbered_iri` table. 
    i.e. `new_numbered_iri('http://example.com/drug')` returns IRI 'http://example.com/drug1' L558-L581
  - `_refactor(self, storid, new_iri)` set the storid with a new IRI in the `resources` table. L585
  - `commit(self)` Commit all changes, this is called when save the SQLite database file or export as rdfxml/ntriples/... format. L594
  - `context_2_user_context(self)` Not sure, map the context `c` to IRI. L600
  - `new_blank_node(self)` Add a new blank node and return the blank node id (always negative).
  - `_get_obj_triple(s)_xxx_xxx(self, c, s, p, o)`  Return all triples ([context, ]subject, predicate, object) from the `objs` table, which only contains the triples that have an **object** property.
  - `_get_data_triple(s)_xxx_xxx(self, c, s, p, o, d)` Return all triples ([context, ]subject, predicate, object[, datatype]) from the `datas` table, which only contains the triples that have a **data** property.
  - `_get_triple(s)_xxx_xxx(self, c, s, p, o, d)` Return all triples ([context, ]subject, predicate, object[, datatype]) from the `quads` view.
  - `_punned_entities(self)` ?
  - `_get_obj_triples_transitive_sp(self, s, p)` ?
  - `_get_obj_triples_transitive_po(self, p, o)` ?
  - `...`

  Class `SubGraph`: Subgraph from `Graph`
    
  Class `_SearchMixin`: Inherits `list`

  Class `_PopulatedSearchList`: 

  Class `_SearchList`: Construct SQL statement for `search(...)`.

  Class `_PopulatedUnionSearchList`
  
  Class `_UnionSearchList`
  
  Class `_PopulatedIntersectionSearchList`
  
  Class `_IntersectionSearchList`

### `rdflib_store.py`

  - class `TripleLiteRDFlibStore` implements the [Abstracted Store API `rdflib.store.Store`](https://rdflib.readthedocs.io/en/stable/apidocs/rdflib.html#rdflib.store.Store)

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
Class `Thing`: The class for user to define ontology class, instance of `Thing` is also the *Named Individual* of the ontology class.

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