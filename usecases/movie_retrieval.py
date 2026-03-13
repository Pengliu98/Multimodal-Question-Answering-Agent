class MovieRetriever:
    """
    Retrieves actual movie titles from the knowledge graph based on recommendation criteria.
    """
    
    def __init__(self, graph, entity_label_dict):
        self.graph = graph
        self.entity_label_dict = entity_label_dict
        
        # Build reverse lookup: lowercase label -> URI
        self.label_to_uri = {}
        for uri, label in entity_label_dict.items():
            self.label_to_uri[label.lower()] = uri
    
    def _get_entity_uri_by_label(self, label):
        """
        Find entity URI by its label (case-insensitive).
        Uses pre-built dictionary for fast lookup.
        """
        # Try lowercase lookup
        uri = self.label_to_uri.get(label.lower())
        if uri:
            return uri
        
        # Fallback: exact match
        for entity_uri, entity_label in self.entity_label_dict.items():
            if entity_label.lower() == label.lower():
                return entity_uri
        
        print(f"WARNING: No URI found for label '{label}'")
        return None

    def _format_movie_with_id(self, label, uri):
        """
        Format movie with Wikidata ID.
        Example: "Inception (Q25188)"
    
        Args:
            label: Movie title
            uri: Full Wikidata URI like "http://www.wikidata.org/entity/Q25188"
    
        Returns:
            Formatted string like "Inception (Q25188)"
        """
        # Extract Qid from URI
        qid = uri.split('/')[-1]  # Get "Q25188" from full URI
        return f"{label} ({qid})"


    def fetch_movies(self, criteria_type, criteria_value, limit=10):
        """
        Fetch movies matching the given criteria.
        
        Args:
            criteria_type: Type of criteria (director, actor, genre, etc.)
            criteria_value: The value to search for (person name, genre name, etc.)
            limit: Maximum number of movies to return
            
        Returns:
            List of movie titles (strings)
        """
        
        if criteria_type == "director":
            return self._fetch_by_director(criteria_value, limit)
        elif criteria_type == "actor":
            return self._fetch_by_actor(criteria_value, limit)
        elif criteria_type == "genre":
            return self._fetch_by_genre(criteria_value, limit)
        elif criteria_type == "composer":
            return self._fetch_by_composer(criteria_value, limit)
        elif criteria_type == "costume_designer":
            return self._fetch_by_costume_designer(criteria_value, limit)
        elif criteria_type == "award":
            return self._fetch_by_award(criteria_value, limit)
        elif criteria_type == "country":
            return self._fetch_by_country(criteria_value, limit)
        elif criteria_type == "genre_country":
            genre, country = criteria_value
            return self._fetch_by_genre_and_country(genre, country, limit)
        elif criteria_type == "genre_actor":
            genre, actor = criteria_value
            return self._fetch_by_genre_and_actor(genre, actor, limit)
        elif criteria_type == "genre_decade":
            genre, decade = criteria_value
            return self._fetch_by_genre_and_decade(genre, decade, limit)
        elif criteria_type == "decade":
            return self._fetch_by_decade(criteria_value, limit)
        else:
            return []
    
    def _fetch_by_director(self, director_name, limit):
        """Fetch movies by a specific director"""
        director_uri = self._get_entity_uri_by_label(director_name)
        if not director_uri:
            return []
        
        query = f"""
        SELECT DISTINCT ?movie ?movieLabel WHERE {{
            ?movie <http://www.wikidata.org/prop/direct/P31> ?type .
            ?movie <http://www.wikidata.org/prop/direct/P57> <{director_uri}> .
            ?movie <http://www.w3.org/2000/01/rdf-schema#label> ?movieLabel .
            
            FILTER(?type IN (
                <http://www.wikidata.org/entity/Q11424>,
                <http://www.wikidata.org/entity/Q202866>,
                <http://www.wikidata.org/entity/Q202470>
            ))
        }} LIMIT {limit}
        """
        
        results = list(self.graph.query(query))
        return [self._format_movie_with_id(str(row[1]), str(row[0])) for row in results]
    
    def _fetch_by_actor(self, actor_name, limit):
        """Fetch movies starring a specific actor"""
        actor_uri = self._get_entity_uri_by_label(actor_name)
        if not actor_uri:
            return []
        
        query = f"""
        SELECT DISTINCT ?movie ?movieLabel WHERE {{
            ?movie <http://www.wikidata.org/prop/direct/P31> ?type .
            ?movie <http://www.wikidata.org/prop/direct/P161> <{actor_uri}> .
            ?movie <http://www.w3.org/2000/01/rdf-schema#label> ?movieLabel .
            
            FILTER(?type IN (
                <http://www.wikidata.org/entity/Q11424>,
                <http://www.wikidata.org/entity/Q202866>,
                <http://www.wikidata.org/entity/Q202470>
            ))
        }} LIMIT {limit}
        """
        
        results = list(self.graph.query(query))
        return [self._format_movie_with_id(str(row[1]), str(row[0])) for row in results]
    
    def _fetch_by_genre(self, genre_name, limit):
        """Fetch movies of a specific genre"""
        genre_uri = self._get_entity_uri_by_label(genre_name)
        if not genre_uri:
            return []
        
        query = f"""
        SELECT DISTINCT ?movie ?movieLabel WHERE {{
            ?movie <http://www.wikidata.org/prop/direct/P31> ?type .
            ?movie <http://www.wikidata.org/prop/direct/P136> <{genre_uri}> .
            ?movie <http://www.w3.org/2000/01/rdf-schema#label> ?movieLabel .
            
            FILTER(?type IN (
                <http://www.wikidata.org/entity/Q11424>,
                <http://www.wikidata.org/entity/Q202866>,
                <http://www.wikidata.org/entity/Q202470>
            ))
        }} LIMIT {limit}
        """
        
        results = list(self.graph.query(query))
        return [self._format_movie_with_id(str(row[1]), str(row[0])) for row in results]
    
    def _fetch_by_composer(self, composer_name, limit):
        """Fetch movies with music by a specific composer"""
        composer_uri = self._get_entity_uri_by_label(composer_name)
        if not composer_uri:
            return []
        
        query = f"""
        SELECT DISTINCT ?movie ?movieLabel WHERE {{
            ?movie <http://www.wikidata.org/prop/direct/P31> ?type .
            ?movie <http://www.wikidata.org/prop/direct/P86> <{composer_uri}> .
            ?movie <http://www.w3.org/2000/01/rdf-schema#label> ?movieLabel .
            
            FILTER(?type IN (
                <http://www.wikidata.org/entity/Q11424>,
                <http://www.wikidata.org/entity/Q202866>,
                <http://www.wikidata.org/entity/Q202470>
            ))
        }} LIMIT {limit}
        """
        
        results = list(self.graph.query(query))
        return [self._format_movie_with_id(str(row[1]), str(row[0])) for row in results]
    
    def _fetch_by_costume_designer(self, designer_name, limit):
        """Fetch movies with costume design by a specific designer"""
        designer_uri = self._get_entity_uri_by_label(designer_name)
        if not designer_uri:
            return []
        
        query = f"""
        SELECT DISTINCT ?movie ?movieLabel WHERE {{
            ?movie <http://www.wikidata.org/prop/direct/P31> ?type .
            ?movie <http://www.wikidata.org/prop/direct/P2515> <{designer_uri}> .
            ?movie <http://www.w3.org/2000/01/rdf-schema#label> ?movieLabel .
            
            FILTER(?type IN (
                <http://www.wikidata.org/entity/Q11424>,
                <http://www.wikidata.org/entity/Q202866>,
                <http://www.wikidata.org/entity/Q202470>
            ))
        }} LIMIT {limit}
        """
        
        results = list(self.graph.query(query))
        return [self._format_movie_with_id(str(row[1]), str(row[0])) for row in results]
    
    def _fetch_by_country(self, country_name, limit):
        """Fetch movies from a specific country"""
        country_uri = self._get_entity_uri_by_label(country_name)
        if not country_uri:
            return []
        
        query = f"""
        SELECT DISTINCT ?movie ?movieLabel WHERE {{
            ?movie <http://www.wikidata.org/prop/direct/P31> ?type .
            ?movie <http://www.wikidata.org/prop/direct/P495> <{country_uri}> .
            ?movie <http://www.w3.org/2000/01/rdf-schema#label> ?movieLabel .
            
            FILTER(?type IN (
                <http://www.wikidata.org/entity/Q11424>,
                <http://www.wikidata.org/entity/Q202866>,
                <http://www.wikidata.org/entity/Q202470>
            ))
        }} LIMIT {limit}
        """
        
        results = list(self.graph.query(query))
        return [self._format_movie_with_id(str(row[1]), str(row[0])) for row in results]
    
    def _fetch_by_award(self, award_name, limit):
        """Fetch movies that won or were nominated for a specific award"""
        award_uri = self._get_entity_uri_by_label(award_name)
        if not award_uri:
            return []
        
        query = f"""
        SELECT DISTINCT ?movie ?movieLabel WHERE {{
            ?movie <http://www.wikidata.org/prop/direct/P31> ?type .
            ?movie <http://www.w3.org/2000/01/rdf-schema#label> ?movieLabel .
            
            {{
                ?movie <http://www.wikidata.org/prop/direct/P166> <{award_uri}> .
            }} UNION {{
                ?movie <http://www.wikidata.org/prop/direct/P1411> <{award_uri}> .
            }}
            
            FILTER(?type IN (
                <http://www.wikidata.org/entity/Q11424>,
                <http://www.wikidata.org/entity/Q202866>,
                <http://www.wikidata.org/entity/Q202470>
            ))
        }} LIMIT {limit}
        """
        
        results = list(self.graph.query(query))
        return [self._format_movie_with_id(str(row[1]), str(row[0])) for row in results]
    
    def _fetch_by_genre_and_country(self, genre_name, country_name, limit):
        """Fetch movies matching both genre and country"""
        genre_uri = self._get_entity_uri_by_label(genre_name)
        country_uri = self._get_entity_uri_by_label(country_name)
        
        if not genre_uri or not country_uri:
            return []
        
        query = f"""
        SELECT DISTINCT ?movie ?movieLabel WHERE {{
            ?movie <http://www.wikidata.org/prop/direct/P31> ?type .
            ?movie <http://www.wikidata.org/prop/direct/P136> <{genre_uri}> .
            ?movie <http://www.wikidata.org/prop/direct/P495> <{country_uri}> .
            ?movie <http://www.w3.org/2000/01/rdf-schema#label> ?movieLabel .
            
            FILTER(?type IN (
                <http://www.wikidata.org/entity/Q11424>,
                <http://www.wikidata.org/entity/Q202866>,
                <http://www.wikidata.org/entity/Q202470>
            ))
        }} LIMIT {limit}
        """
        
        results = list(self.graph.query(query))
        return [self._format_movie_with_id(str(row[1]), str(row[0])) for row in results]
    
    def _fetch_by_genre_and_actor(self, genre_name, actor_name, limit):
        """Fetch movies matching both genre and actor"""
        genre_uri = self._get_entity_uri_by_label(genre_name)
        actor_uri = self._get_entity_uri_by_label(actor_name)
        
        if not genre_uri or not actor_uri:
            return []
        
        query = f"""
        SELECT DISTINCT ?movie ?movieLabel WHERE {{
            ?movie <http://www.wikidata.org/prop/direct/P31> ?type .
            ?movie <http://www.wikidata.org/prop/direct/P136> <{genre_uri}> .
            ?movie <http://www.wikidata.org/prop/direct/P161> <{actor_uri}> .
            ?movie <http://www.w3.org/2000/01/rdf-schema#label> ?movieLabel .
            
            FILTER(?type IN (
                <http://www.wikidata.org/entity/Q11424>,
                <http://www.wikidata.org/entity/Q202866>,
                <http://www.wikidata.org/entity/Q202470>
            ))
        }} LIMIT {limit}
        """
        
        results = list(self.graph.query(query))
        return [self._format_movie_with_id(str(row[1]), str(row[0])) for row in results]
    
    def _fetch_by_genre_and_decade(self, genre_name, decade, limit):
        """Fetch movies matching genre from a specific decade"""
        genre_uri = self._get_entity_uri_by_label(genre_name)
        if not genre_uri:
            return []
        
        start_year = decade
        end_year = decade + 9
        
        query = f"""
        SELECT DISTINCT ?movie ?movieLabel WHERE {{
            ?movie <http://www.wikidata.org/prop/direct/P31> ?type .
            ?movie <http://www.wikidata.org/prop/direct/P136> <{genre_uri}> .
            ?movie <http://www.wikidata.org/prop/direct/P577> ?date .
            ?movie <http://www.w3.org/2000/01/rdf-schema#label> ?movieLabel .
            
            FILTER(YEAR(?date) >= {start_year} && YEAR(?date) <= {end_year})
            FILTER(?type IN (
                <http://www.wikidata.org/entity/Q11424>,
                <http://www.wikidata.org/entity/Q202866>,
                <http://www.wikidata.org/entity/Q202470>
            ))
        }} LIMIT {limit}
        """
        
        results = list(self.graph.query(query))
        return [self._format_movie_with_id(str(row[1]), str(row[0])) for row in results]
    
    def _fetch_by_decade(self, decade, limit):
        """Fetch movies from a specific decade"""
        start_year = decade
        end_year = decade + 9
        
        query = f"""
        SELECT DISTINCT ?movie ?movieLabel WHERE {{
            ?movie <http://www.wikidata.org/prop/direct/P31> ?type .
            ?movie <http://www.wikidata.org/prop/direct/P577> ?date .
            ?movie <http://www.w3.org/2000/01/rdf-schema#label> ?movieLabel .
            
            FILTER(YEAR(?date) >= {start_year} && YEAR(?date) <= {end_year})
            FILTER(?type IN (
                <http://www.wikidata.org/entity/Q11424>,
                <http://www.wikidata.org/entity/Q202866>,
                <http://www.wikidata.org/entity/Q202470>
            ))
        }} LIMIT {limit}
        """
        
        results = list(self.graph.query(query))
        return [self._format_movie_with_id(str(row[1]), str(row[0])) for row in results]