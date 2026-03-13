from movie_retrieval import MovieRetriever

class Recommender:
    """
    General recommender based on the knowledge graph.
    Finds attributes shared by input movies and recommends similar movies.
    Respects explicit user requests for country/language/genre.
    """

    def __init__(self, graph, label_entity_dict, entity_label_dict):
        self.graph = graph
        self.label_entity_dict = label_entity_dict
        self.entity_label_dict = entity_label_dict
        self.retriever = MovieRetriever(graph, entity_label_dict)

    # ---------------------------------------------------------
    # Utilities
    # ---------------------------------------------------------

    def _uri(self, title):
        """Get entity URI from label."""
        return self.label_entity_dict.get(title, [None])[0]

    def _get(self, uri, property_uri):
        """Generic helper to fetch objects for a property."""
        q = f"""
        SELECT ?vLabel WHERE {{
            <{uri}> <{property_uri}> ?v .
            OPTIONAL {{ ?v rdfs:label ?vLabel }} .
        }}
        """
        return [str(r[0]) for r in self.graph.query(q)]

    def _get_year(self, uri):
        q = f"""
        SELECT ?date WHERE {{
            <{uri}> <http://www.wikidata.org/prop/direct/P577> ?date .
        }} LIMIT 1
        """
        res = list(self.graph.query(q))
        if not res:
            return None
        try:
            return int(str(res[0][0])[:4])
        except:
            return None

    def _format_movie_list(self, movies, max_display=10):
        """Format a list of movies for display (up to max_display movies)"""
        if not movies:
            return None
        
        if len(movies) <= max_display:
            return ", ".join(movies)
        else:
            displayed = ", ".join(movies[:max_display])
            remaining = len(movies) - max_display
            return f"{displayed} (and {remaining} more)"

    def _format_or_response(self, description1, movies1, description2, movies2):
        """
        Format a response with OR options using bullet points.
        
        Args:
            description1: Description of first option (e.g., "movies directed by fellini")
            movies1: List of movies for first option
            description2: Description of second option (e.g., "comedy films from italy")
            movies2: List of movies for second option
        """
        response = f"Adequate recommendations will be {description1} or {description2}.\n"
        
        if movies1:
            response += f"• Examples of {description1}: {self._format_movie_list(movies1)}\n"
        
        if movies2:
            response += f"• Examples of {description2}: {self._format_movie_list(movies2)}"
        
        return response

    def _filter_input_movies(self, movies, input_movie_labels):
        """
        Filter out input movies from recommendations.
        
        Args:
            movies: List of movie strings like "Inception (Q25188)"
            input_movie_labels: List of input movie labels
            
        Returns:
            Filtered list of movies
        """
        if not input_movie_labels:
            return movies
        
        # Normalize input labels for comparison
        input_labels_lower = {label.lower() for label in input_movie_labels}
        
        filtered = []
        for movie in movies:
            # Extract movie title from "Title (Q12345)" format
            if '(' in movie:
                title = movie.split('(')[0].strip()
            else:
                title = movie
            
            # Check if this movie is in the input list
            if title.lower() not in input_labels_lower:
                filtered.append(movie)
        
        return filtered

    def _fetch_and_filter(self, criteria_type, criteria_value, movie_labels, limit=10):
        """
        Fetch movies and filter out input movies.
        Fetches extra to compensate for filtering, returns up to 'limit' results.
        """
        # Fetch extra movies to account for potential filtering
        # (in case some input movies appear in results)
        extra_fetch = limit + len(movie_labels) + 5
        movies = self.retriever.fetch_movies(criteria_type, criteria_value, limit=extra_fetch)
        
        # Filter out input movies
        filtered = self._filter_input_movies(movies, movie_labels)
        
        # Return up to the requested limit
        return filtered[:limit]

    # ---------------------------------------------------------
    # User request detection
    # ---------------------------------------------------------

    def detect_requested_country_or_language(self, message):
        """Detect if user explicitly requests movies from a specific country or language"""
        if not message:
            return None
    
        msg = message.lower()
    
        # Language/country mappings with patterns
        # Use word boundaries to avoid false matches
        import re
    
        patterns = {
            r'\bin japanese\b': 'Japan',
            r'\bjapanese\b': 'Japan',
            r'\bfrom japan\b': 'Japan',
            r'\bin italian\b': 'Italy',
            r'\bitalian\b': 'Italy',
            r'\bfrom italy\b': 'Italy',
            r'\bin french\b': 'France',
            r'\bfrench\b': 'France',
            r'\bfrom france\b': 'France',
            r'\bin spanish\b': 'Spain',
            r'\bspanish\b': 'Spain',
            r'\bfrom spain\b': 'Spain',
            r'\bin german\b': 'Germany',
            r'\bgerman\b': 'Germany',
            r'\bfrom germany\b': 'Germany',
            r'\bin korean\b': 'South Korea',
            r'\bkorean\b': 'South Korea',
            r'\bfrom korea\b': 'South Korea',
            r'\bin chinese\b': 'China',
            r'\bchinese\b': 'China',
            r'\bfrom china\b': 'China',
            r'\bin hindi\b': 'India',
            r'\bhindi\b': 'India',
            r'\bindian movies\b': 'India',  # "indian movies" but not "indiana"
            r'\bfrom india\b': 'India',
        }
    
        # Check patterns with word boundaries (sorted by length, longest first)
        for pattern in sorted(patterns.keys(), key=len, reverse=True):
            if re.search(pattern, msg):
                return patterns[pattern]
    
        return None

    def detect_requested_genre(self, message):
        """Detect if user explicitly requests a specific genre"""
        if not message:
            return None
        
        msg = message.lower()
        
        genres = {
            'biographical': 'biographical film',
            'biography': 'biographical film',
            'biopic': 'biographical film',
            'horror': 'horror film',
            'comedy': 'comedy film',
            'drama': 'drama film',
            'action': 'action film',
            'thriller': 'thriller',
            'romance': 'romance film',
            'romantic': 'romance film',
            'musical': 'musical film',
            'sci-fi': 'science fiction film',
            'science fiction': 'science fiction film',
            'documentary': 'documentary',
            'animated': 'animated film',
            'animation': 'animated film',
        }
        
        for keyword, genre in genres.items():
            if keyword in msg:
                return genre
        
        return None

    def _pick_best_genre(self, shared_genres):
        """
        When multiple genres are shared, pick the most specific/distinctive one.
        
        Args:
            shared_genres: dict of {genre: count}
            
        Returns:
            Best genre (string)
        """
        
        # Genre specificity scores (higher = more specific/useful)
        genre_scores = {
            # Very specific genres (10 points)
            'science fiction film': 10,
            'dystopian film': 10,
            'cyberpunk': 10,
            'horror film': 10,
            'western film': 10,
            'musical film': 10,
            'film noir': 10,
            'neo-noir': 10,
            'biographical film': 10,
            'arthouse science fiction film': 10,
            'tech noir': 10,
            'time-travel film': 10,
            'animated film': 10,
            'documentary': 10,
            'treasure hunt film': 10,
            
            # Moderately specific (7 points)
            'thriller film': 7,
            'thriller': 7,
            'comedy film': 7,
            'romance film': 7,
            'mystery film': 7,
            'crime film': 7,
            'fantasy film': 7,
            'animation': 7,
            
            # Generic (lower priority)
            'action film': 5,
            'adventure film': 5,
            'drama film': 3,
            'melodrama': 2,
        }
        
        best_genre = None
        best_score = 0
        
        for genre in shared_genres.keys():
            score = genre_scores.get(genre, 5)  # Default score 5 if not in list
            if score > best_score:
                best_score = score
                best_genre = genre
        
        return best_genre if best_genre else list(shared_genres.keys())[0]

    # ---------------------------------------------------------
    # Main recommendation logic
    # ---------------------------------------------------------

    def recommend(self, movie_labels, user_message=""):
        """
        Build recommendations based on shared attributes.
        
        Priority:
        0. Respect explicit user requests (country, genre)
        1. Find attributes shared by ALL movies (100%)
        2. Find attributes shared by MOST movies (80%)
        3. Fallback to generic recommendations
        
        Args:
            movie_labels: List of movie title strings
            user_message: Original user message (to detect explicit requests)
        """
        
        # Convert labels to URIs
        uris = [self._uri(title) for title in movie_labels]
        uris = [u for u in uris if u is not None]
        if not uris:
            return "I couldn't interpret any movie titles."
        
        num_movies = len(uris)
        
        # ---------------------------------------------------------
        # Helper: Find attributes shared by movies
        # ---------------------------------------------------------
        
        def find_shared_attributes(property_uri, min_count):
            """
            Find attributes that appear in at least min_count movies.
            Returns: dict of {attribute: count}
            """
            from collections import Counter
            
            # Count how many movies each attribute appears in
            attribute_movie_count = Counter()
            
            for uri in uris:
                attrs = self._get(uri, property_uri)
                # Deduplicate per movie (count each movie only once)
                unique_attrs = set(a.lower() for a in attrs if a)
                for attr in unique_attrs:
                    attribute_movie_count[attr] += 1
            
            # Filter for attributes that appear in enough movies
            shared = {attr: count for attr, count in attribute_movie_count.items() 
                     if count >= min_count}
            
            return shared

        def find_shared_awards_and_nominations(min_count):
            """
            Find awards/nominations that appear in at least min_count movies.
            Checks BOTH P166 (awards won) AND P1411 (nominated for).
            Returns: dict of {award: count}
            """
            from collections import Counter
            
            # Count how many movies each award appears in (either won or nominated)
            award_movie_count = Counter()
            
            for uri in uris:
                # Get both awards won AND nominations
                awards_won = self._get(uri, "http://www.wikidata.org/prop/direct/P166")
                nominations = self._get(uri, "http://www.wikidata.org/prop/direct/P1411")
                
                # Combine them
                all_awards = awards_won + nominations
                
                # Deduplicate per movie
                unique_awards = set(a.lower() for a in all_awards if a)
                for award in unique_awards:
                    award_movie_count[award] += 1
            
            # Filter for awards that appear in enough movies
            shared = {award: count for award, count in award_movie_count.items() 
                     if count >= min_count}
            
            return shared
        
        # ---------------------------------------------------------
        # PRIORITY 0: Check for explicit user requests
        # ---------------------------------------------------------
        
        requested_country = self.detect_requested_country_or_language(user_message)
        requested_genre = self.detect_requested_genre(user_message)
        
        print(f"\n{'='*60}")
        print(f"DEBUG: Analyzing {num_movies} movies")
        print(f"  Requested country: {requested_country}")
        print(f"  Requested genre: {requested_genre}")
        print(f"{'='*60}")
        
        # If user explicitly requests country/language
        if requested_country:
            print(f"✅ Honoring explicit country request: {requested_country}")
            
            # If we have input movies, check for shared attributes to add with OR
            additional = None
            additional_movies = []
            
            if num_movies > 0:
                min_count_100 = num_movies

                # Or shared director
                if not additional:
                    shared_directors = find_shared_attributes("http://www.wikidata.org/prop/direct/P57", min_count_100)
                    if shared_directors:
                        director = list(shared_directors.keys())[0]
                        additional = f"movies directed by {director}"
                        additional_movies = self._fetch_and_filter("director", director, movie_labels, limit=10)
                
                # Priority 2: Check for shared genre (very relevant)
                if not additional:
                    shared_genres = find_shared_attributes("http://www.wikidata.org/prop/direct/P136", min_count_100)
                    if shared_genres:
                        genre = self._pick_best_genre(shared_genres)
                        additional = f"{genre} movies"
                        additional_movies = self._fetch_and_filter("genre", genre, movie_labels, limit=10)
        
                # Or shared actor
                if not additional:
                    shared_actors = find_shared_attributes("http://www.wikidata.org/prop/direct/P161", min_count_100)
                    if shared_actors:
                        actor = list(shared_actors.keys())[0]
                        additional = f"movies starring {actor}"
                        additional_movies = self._fetch_and_filter("actor", actor, movie_labels, limit=10)

                if not additional:       
                    # Check for shared composer (highest priority for OR with country)
                    shared_composers = find_shared_attributes("http://www.wikidata.org/prop/direct/P86", min_count_100)
                    if shared_composers:
                        composer = list(shared_composers.keys())[0]
                        additional = f"movies with music composed by {composer}"
                        additional_movies = self._fetch_and_filter("composer", composer, movie_labels, limit=10)
            
            # Build country recommendation
            if requested_genre:
                country_part = f"{requested_genre} movies from {requested_country}"
                country_movies = self._fetch_and_filter("genre_country", (requested_genre, requested_country), movie_labels, limit=10)
            else:
                country_part = f"movies from {requested_country}"
                country_movies = self._fetch_and_filter("country", requested_country, movie_labels, limit=10)
            
            # Build response
            if additional:
                return self._format_or_response(additional, additional_movies, country_part, country_movies)
            else:
                response = f"Adequate recommendations will be {country_part}."
                if country_movies:
                    response += f"\n• Examples: {self._format_movie_list(country_movies)}"
                return response
        
        # If user explicitly requests genre (e.g., "biographical movies with Meryl Streep")
        if requested_genre:
            # Check if there's a dominant actor
            actors = []
            for uri in uris:
                actors.extend(self._get(uri, "http://www.wikidata.org/prop/direct/P161"))
            
            if actors:
                from collections import Counter
                actor_counts = Counter([a.lower() for a in actors])
                if actor_counts:
                    dom_actor = actor_counts.most_common(1)[0][0]
                    movies = self._fetch_and_filter("genre_actor", (requested_genre, dom_actor), movie_labels, limit=10)
                    
                    print(f"✅ Combining requested genre with actor")
                    response = f"Adequate recommendations will be {requested_genre} movies starring {dom_actor}."
                    if movies:
                        response += f"\n• Examples: {self._format_movie_list(movies)}"
                    return response
            
            # Just genre
            movies = self._fetch_and_filter("genre", requested_genre, movie_labels, limit=10)
            print(f"✅ Honoring explicit genre request")
            response = f"Adequate recommendations will be {requested_genre} movies."
            if movies:
                response += f"\n• Examples: {self._format_movie_list(movies)}"
            return response
        
        # ---------------------------------------------------------
        # PASS 1: Look for 100% match (ALL movies share)
        # ---------------------------------------------------------
        
        min_count_100 = num_movies  # All movies must have it
        
        shared_directors_100 = find_shared_attributes("http://www.wikidata.org/prop/direct/P57", min_count_100)
        shared_actors_100 = find_shared_attributes("http://www.wikidata.org/prop/direct/P161", min_count_100)
        shared_costume_100 = find_shared_attributes("http://www.wikidata.org/prop/direct/P2515", min_count_100)
        shared_composers_100 = find_shared_attributes("http://www.wikidata.org/prop/direct/P86", min_count_100)
        shared_awards_100 = find_shared_awards_and_nominations(min_count_100)
        shared_genres_100 = find_shared_attributes("http://www.wikidata.org/prop/direct/P136", min_count_100)
        shared_countries_100 = find_shared_attributes("http://www.wikidata.org/prop/direct/P495", min_count_100)
        
        print(f"\n100% Match (all {num_movies} movies):")
        print(f"  Directors: {list(shared_directors_100.keys())}")
        print(f"  Actors: {list(shared_actors_100.keys())[:3]}...")
        print(f"  Costume designers: {list(shared_costume_100.keys())}")
        print(f"  Composers: {list(shared_composers_100.keys())}")
        print(f"  Awards: {list(shared_awards_100.keys())[:3]}...")
        print(f"  Genres: {list(shared_genres_100.keys())}")
        print(f"  Countries: {list(shared_countries_100.keys())}")
        
        # ---------------------------------------------------------
        # Return based on 100% match (with smart OR logic)
        # ---------------------------------------------------------
        
        # CASE 1: Director + (Genre or Country) → Use OR
        if shared_directors_100 and (shared_genres_100 or shared_countries_100):
            director = list(shared_directors_100.keys())[0]
            director_movies = self._fetch_and_filter("director", director, movie_labels, limit=10)
            description1 = f"movies directed by {director}"
            
            # Build second category
            if shared_genres_100 and shared_countries_100:
                genre = self._pick_best_genre(shared_genres_100)
                country = list(shared_countries_100.keys())[0]
                second_movies = self._fetch_and_filter("genre_country", (genre, country), movie_labels, limit=10)
                description2 = f"{genre} movies from {country}"
            elif shared_countries_100:
                country = list(shared_countries_100.keys())[0]
                second_movies = self._fetch_and_filter("country", country, movie_labels, limit=10)
                description2 = f"movies from {country}"
            elif shared_genres_100:
                genre = self._pick_best_genre(shared_genres_100)
                second_movies = self._fetch_and_filter("genre", genre, movie_labels, limit=10)
                description2 = f"{genre} movies"
            else:
                second_movies = []
                description2 = None
            
            if description2:
                print(f"\n✅ Recommending by director OR genre/country (100% match)")
                return self._format_or_response(description1, director_movies, description2, second_movies)
            else:
                print(f"\n✅ Recommending by director (100% match)")
                response = f"Adequate recommendations will be {description1}."
                if director_movies:
                    response += f"\n• Examples: {self._format_movie_list(director_movies)}"
                return response
        
        # CASE 2: Costume designer + Costume award → Use OR
        if shared_costume_100 and shared_awards_100:
            costume = list(shared_costume_100.keys())[0]
            costume_awards = {k: v for k, v in shared_awards_100.items() if 'costume' in k}
            
            if costume_awards:
                award = list(costume_awards.keys())[0]
                costume_movies = self._fetch_and_filter("costume_designer", costume, movie_labels, limit=10)
                award_movies = self._fetch_and_filter("award", award, movie_labels, limit=10)
                
                print(f"\n✅ Recommending by costume designer OR costume award (100% match)")
                description1 = f"movies with costume design by {costume}"
                description2 = f"movies won or were nominated for {award}"
                return self._format_or_response(description1, costume_movies, description2, award_movies)

        # CASE 3: composer
        if shared_composers_100:
            composer = list(shared_composers_100.keys())[0]
            movies = self._fetch_and_filter("composer", composer, movie_labels, limit=10)
            print(f"\n✅ Recommending by composer (100% match)")
            response = f"Adequate recommendations will be movies with music composed by {composer}."
            if movies:
                response += f"\n• Examples: {self._format_movie_list(movies)}"
            return response

        # CASE 4: Genre + Decade (if narrow range AND country is generic)
        if shared_genres_100:
            genre = self._pick_best_genre(shared_genres_100)
    
            years = []
            for uri in uris:
                year = self._get_year(uri)
                if year:
                    years.append(year)
    
            if years:
                min_year = min(years)
                max_year = max(years)
        
                # Check if we have a narrow decade range
                if max_year - min_year <= 15:
                    decade = (min_year // 10) * 10
            
                    # Check if country is generic (USA, UK)
                    if shared_countries_100:
                        country = list(shared_countries_100.keys())[0]
                        generic_countries = {'united states', 'united kingdom', 'uk', 'usa'}
                
                        # If country is generic, prioritize decade
                        if country.lower() in generic_countries:
                            movies = self._fetch_and_filter("genre_decade", (genre, decade), movie_labels, limit=10)
                            print(f"\n✅ Recommending by genre + decade (100% match)")
                            response = f"Adequate recommendations will be {genre} movies from the {decade}s."
                            if movies:
                                response += f"\n• Examples: {self._format_movie_list(movies)}"
                            return response
                    else:
                        # No country, use decade
                        movies = self._fetch_and_filter("genre_decade", (genre, decade), movie_labels, limit=10)
                        print(f"\n✅ Recommending by genre + decade (100% match)")
                        response = f"Adequate recommendations will be {genre} movies from the {decade}s."
                        if movies:
                            response += f"\n• Examples: {self._format_movie_list(movies)}"
                        return response

        # CASE 5: Genre + Country (if country is distinctive)
        if shared_genres_100 and shared_countries_100:
            genre = self._pick_best_genre(shared_genres_100)
            country = list(shared_countries_100.keys())[0]
    
            # Only use if country is distinctive
            generic_countries = {'united states', 'united kingdom', 'uk', 'usa'}
            if country.lower() not in generic_countries:
                movies = self._fetch_and_filter("genre_country", (genre, country), movie_labels, limit=10)
                print(f"\n✅ Recommending by genre + country (100% match)")
                response = f"Adequate recommendations will be {genre} movies from {country}."
                if movies:
                    response += f"\n• Examples: {self._format_movie_list(movies)}"
                return response
        
        
        # CASE 6: Actor + Genre → Combined (NO OR)
        if shared_actors_100 and shared_genres_100:
            actor = list(shared_actors_100.keys())[0]
            genre = self._pick_best_genre(shared_genres_100)
            movies = self._fetch_and_filter("genre_actor", (genre, actor), movie_labels, limit=10)
            
            print(f"\n✅ Recommending by genre + actor (100% match)")
            response = f"Adequate recommendations will be {genre} movies starring {actor}."
            if movies:
                response += f"\n• Examples: {self._format_movie_list(movies)}"
            return response
        
        
        # CASE 7: Single attributes (no combinations)
        if shared_directors_100:
            director = list(shared_directors_100.keys())[0]
            movies = self._fetch_and_filter("director", director, movie_labels, limit=10)
            print(f"\n✅ Recommending by director (100% match)")
            response = f"Adequate recommendations will be movies directed by {director}."
            if movies:
                response += f"\n• Examples: {self._format_movie_list(movies)}"
            return response
        
        if shared_actors_100:
            actor = list(shared_actors_100.keys())[0]
            movies = self._fetch_and_filter("actor", actor, movie_labels, limit=10)
            print(f"\n✅ Recommending by actor (100% match)")
            response = f"Adequate recommendations will be movies starring {actor}."
            if movies:
                response += f"\n• Examples: {self._format_movie_list(movies)}"
            return response
        
        
        
        if shared_costume_100:
            costume = list(shared_costume_100.keys())[0]
            movies = self._fetch_and_filter("costume_designer", costume, movie_labels, limit=10)
            print(f"\n✅ Recommending by costume designer (100% match)")
            response = f"Adequate recommendations will be movies with costume design by {costume}."
            if movies:
                response += f"\n• Examples: {self._format_movie_list(movies)}"
            return response
        
        # CASE 8: Awards
        if shared_awards_100:
            academy_awards = {k: v for k, v in shared_awards_100.items() 
                             if 'academy award' in k and 'best' in k}
            if academy_awards:
                award = list(academy_awards.keys())[0]
                movies = self._fetch_and_filter("award", award, movie_labels, limit=10)
                print(f"\n✅ Recommending by award (100% match)")
                response = f"Adequate recommendations will be movies that won or were nominated for {award}."
                if movies:
                    response += f"\n• Examples: {self._format_movie_list(movies)}"
                return response
        
        # ---------------------------------------------------------
        # PASS 2: Try 80% match if no 100% match found
        # ---------------------------------------------------------
        
        print(f"\n❌ No 100% match found. Trying 80% match...")
        
        min_count_80 = max(2, int(num_movies * 0.8))
        
        shared_directors_80 = find_shared_attributes("http://www.wikidata.org/prop/direct/P57", min_count_80)
        shared_actors_80 = find_shared_attributes("http://www.wikidata.org/prop/direct/P161", min_count_80)
        shared_costume_80 = find_shared_attributes("http://www.wikidata.org/prop/direct/P2515", min_count_80)
        shared_composers_80 = find_shared_attributes("http://www.wikidata.org/prop/direct/P86", min_count_80)
        shared_awards_80 = find_shared_awards_and_nominations(min_count_80)
        shared_genres_80 = find_shared_attributes("http://www.wikidata.org/prop/direct/P136", min_count_80)
        shared_countries_80 = find_shared_attributes("http://www.wikidata.org/prop/direct/P495", min_count_80)
        
        print(f"\n80% Match (at least {min_count_80} movies):")
        print(f"  Directors: {list(shared_directors_80.keys())}")
        print(f"  Actors: {list(shared_actors_80.keys())[:3]}...")
        print(f"  Costume designers: {list(shared_costume_80.keys())}")
        print(f"  Composers: {list(shared_composers_80.keys())}")
        print(f"  Awards: {list(shared_awards_80.keys())[:3]}...")
        print(f"  Genres: {list(shared_genres_80.keys())}")
        print(f"  Countries: {list(shared_countries_80.keys())}")
        
        # ---------------------------------------------------------
        # 80% Match Priority Order (with smart OR logic)
        # ---------------------------------------------------------
        
        # CASE 1: Costume designer + Costume award → Use OR
        if shared_costume_80 and shared_awards_80:
            costume = max(shared_costume_80.items(), key=lambda x: x[1])[0]
            costume_awards = {k: v for k, v in shared_awards_80.items() if 'costume' in k}
            
            if costume_awards:
                award = max(costume_awards.items(), key=lambda x: x[1])[0]
                costume_movies = self._fetch_and_filter("costume_designer", costume, movie_labels, limit=10)
                award_movies = self._fetch_and_filter("award", award, movie_labels, limit=10)
                
                print(f"\n✅ Recommending by costume designer OR costume award (80% match)")
                description1 = f"movies with costume design by {costume}"
                description2 = f"movies nominated for {award}"
                return self._format_or_response(description1, costume_movies, description2, award_movies)
        
        # CASE 2: Costume designer alone
        if shared_costume_80:
            costume = max(shared_costume_80.items(), key=lambda x: x[1])[0]
            movies = self._fetch_and_filter("costume_designer", costume, movie_labels, limit=10)
            print(f"\n✅ Recommending by costume designer (80% match)")
            response = f"Adequate recommendations will be movies with costume design by {costume}."
            if movies:
                response += f"\n• Examples: {self._format_movie_list(movies)}"
            return response
        
        # CASE 3: Director + (Genre or Country) → Use OR
        if shared_directors_80 and (shared_genres_80 or shared_countries_80):
            director = max(shared_directors_80.items(), key=lambda x: x[1])[0]
            director_movies = self._fetch_and_filter("director", director, movie_labels, limit=10)
            description1 = f"movies directed by {director}"
            
            # Build second category
            if shared_genres_80 and shared_countries_80:
                genre = self._pick_best_genre(shared_genres_80)
                country = max(shared_countries_80.items(), key=lambda x: x[1])[0]
                second_movies = self._fetch_and_filter("genre_country", (genre, country), movie_labels, limit=10)
                description2 = f"{genre} movies from {country}"
            elif shared_countries_80:
                country = max(shared_countries_80.items(), key=lambda x: x[1])[0]
                second_movies = self._fetch_and_filter("country", country, movie_labels, limit=10)
                description2 = f"movies from {country}"
            elif shared_genres_80:
                genre = self._pick_best_genre(shared_genres_80)
                second_movies = self._fetch_and_filter("genre", genre, movie_labels, limit=10)
                description2 = f"{genre} movies"
            else:
                second_movies = []
                description2 = None
            
            if description2:
                print(f"\n✅ Recommending by director OR genre/country (80% match)")
                return self._format_or_response(description1, director_movies, description2, second_movies)
            else:
                print(f"\n✅ Recommending by director (80% match)")
                response = f"Adequate recommendations will be {description1}."
                if director_movies:
                    response += f"\n• Examples: {self._format_movie_list(director_movies)}"
                return response
        
        # CASE 4: Director alone
        if shared_directors_80:
            director = max(shared_directors_80.items(), key=lambda x: x[1])[0]
            movies = self._fetch_and_filter("director", director, movie_labels, limit=10)
            print(f"\n✅ Recommending by director (80% match)")
            response = f"Adequate recommendations will be movies directed by {director}."
            if movies:
                response += f"\n• Examples: {self._format_movie_list(movies)}"
            return response
        
        # CASE 5: Composer + (Genre or Country) → Use OR
        if shared_composers_80 and (shared_genres_80 or shared_countries_80):
            composer = max(shared_composers_80.items(), key=lambda x: x[1])[0]
            composer_movies = self._fetch_and_filter("composer", composer, movie_labels, limit=10)
            description1 = f"movies with music composed by {composer}"
            
            # Build second category
            if shared_genres_80 and shared_countries_80:
                genre = self._pick_best_genre(shared_genres_80)
                country = max(shared_countries_80.items(), key=lambda x: x[1])[0]
                second_movies = self._fetch_and_filter("genre_country", (genre, country), movie_labels, limit=10)
                description2 = f"{genre} movies from {country}"
            elif shared_countries_80:
                country = max(shared_countries_80.items(), key=lambda x: x[1])[0]
                second_movies = self._fetch_and_filter("country", country, movie_labels, limit=10)
                description2 = f"movies from {country}"
            elif shared_genres_80:
                genre = self._pick_best_genre(shared_genres_80)
                second_movies = self._fetch_and_filter("genre", genre, movie_labels, limit=10)
                description2 = f"{genre} movies"
            else:
                second_movies = []
                description2 = None
            
            if description2:
                print(f"\n✅ Recommending by composer OR genre/country (80% match)")
                return self._format_or_response(description1, composer_movies, description2, second_movies)
            else:
                print(f"\n✅ Recommending by composer (80% match)")
                response = f"Adequate recommendations will be {description1}."
                if composer_movies:
                    response += f"\n• Examples: {self._format_movie_list(composer_movies)}"
                return response
        
        # CASE 6: Actor + Genre → Combined (NO OR)
        if shared_actors_80 and shared_genres_80:
            actor = max(shared_actors_80.items(), key=lambda x: x[1])[0]
            genre = self._pick_best_genre(shared_genres_80)
            movies = self._fetch_and_filter("genre_actor", (genre, actor), movie_labels, limit=10)
            print(f"\n✅ Recommending by genre + actor (80% match)")
            response = f"Adequate recommendations will be {genre} movies starring {actor}."
            if movies:
                response += f"\n• Examples: {self._format_movie_list(movies)}"
            return response
        
        # CASE 7: Actor alone
        if shared_actors_80:
            actor = max(shared_actors_80.items(), key=lambda x: x[1])[0]
            movies = self._fetch_and_filter("actor", actor, movie_labels, limit=10)
            print(f"\n✅ Recommending by actor (80% match)")
            response = f"Adequate recommendations will be movies starring {actor}."
            if movies:
                response += f"\n• Examples: {self._format_movie_list(movies)}"
            return response
        
        # CASE 8: Composer alone
        if shared_composers_80:
            composer = max(shared_composers_80.items(), key=lambda x: x[1])[0]
            movies = self._fetch_and_filter("composer", composer, movie_labels, limit=10)
            print(f"\n✅ Recommending by composer (80% match)")
            response = f"Adequate recommendations will be movies with music composed by {composer}."
            if movies:
                response += f"\n• Examples: {self._format_movie_list(movies)}"
            return response
        
        # CASE 9: Genre + Country → Combined (NO OR)
        if shared_genres_80 and shared_countries_80:
            genre = self._pick_best_genre(shared_genres_80)
            country = max(shared_countries_80.items(), key=lambda x: x[1])[0]
            movies = self._fetch_and_filter("genre_country", (genre, country), movie_labels, limit=10)
            print(f"\n✅ Recommending by genre + country (80% match)")
            response = f"Adequate recommendations will be {genre} movies from {country}."
            if movies:
                response += f"\n• Examples: {self._format_movie_list(movies)}"
            return response
        
        # CASE 10: Genre alone
        if shared_genres_80:
            genre = self._pick_best_genre(shared_genres_80)
            movies = self._fetch_and_filter("genre", genre, movie_labels, limit=10)
            print(f"\n✅ Recommending by genre (80% match)")
            response = f"Adequate recommendations will be {genre} movies."
            if movies:
                response += f"\n• Examples: {self._format_movie_list(movies)}"
            return response
        
        # CASE 11: Awards
        if shared_awards_80:
            academy_awards = {k: v for k, v in shared_awards_80.items() 
                             if 'academy award' in k and 'best' in k}
            if academy_awards:
                award = max(academy_awards.items(), key=lambda x: x[1])[0]
                movies = self._fetch_and_filter("award", award, movie_labels, limit=10)
                print(f"\n✅ Recommending by award (80% match)")
                response = f"Adequate recommendations will be movies that won or were nominated for {award}."
                if movies:
                    response += f"\n• Examples: {self._format_movie_list(movies)}"
                return response
        
        # ---------------------------------------------------------
        # FALLBACK: No strong pattern found
        # ---------------------------------------------------------
        
        print(f"\n❌ No 80% match found. Using fallback...")
        
        # Last resort: time period
        years = []
        for uri in uris:
            year = self._get_year(uri)
            if year:
                years.append(year)
        
        if years:
            decade = (min(years) // 10) * 10
            movies = self._fetch_and_filter("decade", decade, movie_labels, limit=10)
            response = f"Adequate recommendations will be movies from the {decade}s."
            if movies:
                response += f"\n• Examples: {self._format_movie_list(movies)}"
            return response
        
        return "These movies are quite different from each other. For better recommendations, try movies that share a director, actor, genre, or time period!"