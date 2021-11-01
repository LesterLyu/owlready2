## Sparql-endpoint Backend
### TODO
- [x] Implement blank node creation.
- [ ] Implement Loading.
  - [x] Store triples
  - [ ] Store last update time.
  - [ ] Implement `ontology_alias` for different `base_iri` point to the same Ontology. (i.e. Ontology changes `base_iri`)
  - [ ] Figure out 
- [ ] Implement search.
  - [ ] Nested search
    - [ ] union of the search result.
    - [ ] Intersection of the search result.
  - [ ] `iri`, for searching entities by its full IRI
  - [ ] `type`, for searching Individuals of a given Class
  - [ ] `subclass_of`, for searching subclasses of a given Class
  - [ ] `is_a`, for searching both Individuals and subclasses of a given Class
  - [ ] `subproperty_of`, for searching subproperty of a given Property
  - [ ] any object, data or annotation property name
- [ ] Use remote SPARQL engine to perform customized SPARQL query.
- [ ] Implement `SparqlGraph._new_numbered_iri(self, ...)` to generate IRI for newly created individual.
- [ ] Store modified/update time for Ontology in the graph.


### Limitations
- There should be only one Ontology in each named graph. (*more investigation required*)
- Only GraphDB Support due to blank node limitation.
  - GraphDB provides a way to [get internal ID for entities](https://graphdb.ontotext.com/documentation/free/query-behaviour.html#what-s-in-this-document)
    (URIs, blank nodes, literals). 
    Blank node ID is needed for owlready2 which make query about specific blank nodes.
  - If we want to support all SPARQL endpoints, we need to keep track of the blank node IDs in our way (Store it in the graph).
  We won't be able to use native import functionality provided by the graph database, i.e. web interface to import rdf/owl file.
- Search (`onto.search(...)`)
  - `FTS(...)` No [FTS (Full-Text Search)](https://owlready2.readthedocs.io/en/v0.35/annotations.html?highlight=fts#full-text-search-fts) Support
  - `_bm25` No BM25 support. (Similarity search)
- SPARQL Engine
  - Internal SPARQL engine dropped, we now have a full SPARQL support.
  - SPARQL query must specify **the named graph(s)** you want to query in.
- Performance
  - Performance is maximized when the owlready2 and GraphDB are located in the same network.
(localhost or connected through ethernet with low latency and high throughput.)
  - It could be extremely slow on WIFI. (GraphDB is a server and Owlready2 runs on some laptop.)