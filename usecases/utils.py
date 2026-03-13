import time

# configuration
DEFAULT_HOST_URL = 'https://speakeasy.ifi.uzh.ch'
GRAPH_PATH = "/space_mounts/atai-hs25/dataset/graph.nt"
EMB_BASE_PATH = "/space_mounts/atai-hs25/dataset/embeddings/"
IMAGE_BASE_PATH = "/space_mounts/atai-hs25/dataset/images/"

QUESTION_RELATION_MAP = {
    # Existing
    'director': 'http://www.wikidata.org/prop/direct/P57',
    'screenwriter': 'http://www.wikidata.org/prop/direct/P58',
    'genre': 'http://www.wikidata.org/prop/direct/P136',
    'rating': 'http://www.wikidata.org/prop/direct/P1657',
    'release_date': 'http://www.wikidata.org/prop/direct/P577',
    'country': 'http://www.wikidata.org/prop/direct/P495',
    
    'composer': 'http://www.wikidata.org/prop/direct/P86',       # composer
    'cast': 'http://www.wikidata.org/prop/direct/P161',          # cast member
    'producer': 'http://www.wikidata.org/prop/direct/P162',      # producer
    'cinematographer': 'http://www.wikidata.org/prop/direct/P344', # cinematographer
    'editor': 'http://www.wikidata.org/prop/direct/P1040',       # film editor
    'awards': 'http://www.wikidata.org/prop/direct/P166',        # award received
    'nominated': 'http://www.wikidata.org/prop/direct/P1411',    # nominated for
    'based_on': 'http://www.wikidata.org/prop/direct/P144',      # based on
    'duration': 'http://www.wikidata.org/prop/direct/P2047',     # duration/runtime
    'budget': 'http://www.wikidata.org/prop/direct/P2130',       # budget
    'box_office': 'http://www.wikidata.org/prop/direct/P2142',   # box office
}

# label dictionaries
def build_label_dicts(graph):
   # Load all entity labels from the graph
    entity_label_dict = {}
    label_entity_dict = {}

    query = """
    SELECT ?entity ?label
    WHERE { ?entity <http://www.w3.org/2000/01/rdf-schema#label> ?label }
    """
    for e, l in graph.query(query):
        e_str, l_str = str(e), str(l)
        entity_label_dict[e_str] = l_str
        label_entity_dict.setdefault(l_str, []).append(e_str)

    return label_entity_dict, entity_label_dict


def build_movie_label_dict(graph):
    """Build a dictionary containing ONLY movie labels"""
    movie_label_dict = {}
    
    query = """
    SELECT ?movie ?label
    WHERE {
        ?movie <http://www.wikidata.org/prop/direct/P31> ?type .
        FILTER(?type IN (
            <http://www.wikidata.org/entity/Q11424>,   # film
            <http://www.wikidata.org/entity/Q24869>,   # feature film
            <http://www.wikidata.org/entity/Q506240>,  # short film
            <http://www.wikidata.org/entity/Q220898>,   # television film
            <http://www.wikidata.org/entity/Q202866>,  # animated film 
            <http://www.wikidata.org/entity/Q202470>   # animated feature film 
        ))
        ?movie <http://www.w3.org/2000/01/rdf-schema#label> ?label .
    }
    """
    
    for movie, label in graph.query(query):
        label_str = str(label)
        movie_str = str(movie)
        movie_label_dict.setdefault(label_str, []).append(movie_str)
    
    print(f"  Found {len(movie_label_dict)} unique movie labels")
    return movie_label_dict
