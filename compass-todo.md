### TODOs
1. Owlready2 has a mapping that maps their internal ID (storid) to IRIs. 
We need to get rid of it across all owlready2 and directly use IRIs.
2. In Owlready2, different namespaces/ontologies go into the different user contexts/SubGraph.(ontologies table)
The MainGraph is for the global access, SPARQL engine, ...; SubGraph is for ontologies/namespaces.

3. Map the user context/sub graph into graph databases.


4. Map owlready2 blank nodes (that uses storid) to graph databases' blank nodes and vice versa.
i.e. Blank nodes is used for owl:Restriction.

5. There is no official GraphDB driver/package for Python, we will use their HTTP APIs.

6. We won't have the ability to load ontology file from local environment directly into Owlready2.
The ontologies are existed already on the graph database.

7. Once ontologies are imported into a graph database, there is no way to know what is imported.

8. Owlready2 uses contexts to differentiate different ontologies imported. When user save the modified ontology as a file,
they choose which ontology(context) to save. When they modify the ontology or create individuals, they 
choose a context/ontology to make modification.
in a real graph database, we don't have the option to choose the context, when we save the triples as a file, everything 
in the graph database (default graph) is saved. If we don't save the triples as a file then it's fine 

9. We need to store some metadata in the graph database, the functionality of generating IRI for named individual
requires some store some number(counter) for each ontology classes.