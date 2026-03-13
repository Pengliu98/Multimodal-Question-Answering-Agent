import editdistance
import random
from utils import QUESTION_RELATION_MAP

class QuestionHandler:
    def __init__(self, graph, embeddings, label_entity_dict, entity_label_dict, movie_label_dict):
        self.graph = graph
        self.embeddings = embeddings
        self.label_entity_dict = label_entity_dict
        self.entity_label_dict = entity_label_dict
        self.movie_label_dict = movie_label_dict
        
        # Natural language response templates
        self.response_templates = {
            'director': [
                "{movie} was directed by {answer}.",
                "The director of {movie} is {answer}.",
                "{movie} is directed by {answer}.",
            ],
            'screenwriter': [
                "{movie} was written by {answer}.",
                "The screenwriter of {movie} is {answer}.",
                "{answer} wrote {movie}.",
            ],
            'composer': [
                "The music for {movie} was composed by {answer}.",
                "{answer} composed the score for {movie}.",
                "The composer of {movie} is {answer}.",
            ],
            'cast': [
                "{movie} stars {answer}.",
                "The cast of {movie} includes {answer}.",
                "{answer} starred in {movie}.",
            ],
            'producer': [
                "{movie} was produced by {answer}.",
                "The producer of {movie} is {answer}.",
            ],
            'cinematographer': [
                "The cinematographer of {movie} is {answer}.",
                "{answer} handled the cinematography for {movie}.",
            ],
            'editor': [
                "{movie} was edited by {answer}.",
                "The editor of {movie} is {answer}.",
            ],
            'awards': [
                "{movie} won {answer}.",
                "{movie} received {answer}.",
                "Awards for {movie}: {answer}.",
            ],
            'nominated': [
                "{movie} was nominated for {answer}.",
                "{movie} received nominations for {answer}.",
            ],
            'based_on': [
                "{movie} is based on {answer}.",
                "{movie} was adapted from {answer}.",
            ],
            'genre': [
                "{movie} is a {answer}.",
                "The genre of {movie} is {answer}.",
                "{movie} is classified as {answer}.",
            ],
            'rating': [
                "{movie} is rated {answer}.",
                "The rating for {movie} is {answer}.",
            ],
            'release_date': [
                "{movie} was released on {answer}.",
                "{movie} came out on {answer}.",
                "The release date of {movie} is {answer}.",
            ],
            'country': [
                "{movie} is from {answer}.",
                "{movie} is a {answer} film.",
                "The country of origin for {movie} is {answer}.",
            ],
            'duration': [
                "{movie} is {answer} long.",
                "The runtime of {movie} is {answer}.",
                "{movie} has a duration of {answer}.",
            ],
            'budget': [
                "{movie} had a budget of {answer}.",
                "The budget for {movie} was {answer}.",
            ],
            'box_office': [
                "{movie} grossed {answer}.",
                "The box office earnings for {movie} were {answer}.",
                "{movie} made {answer} at the box office.",
            ],
        }

    def detect_question_type(self, message):
        """Detect what kind of property is requested in the question"""
        msg = message.lower()
        
        # Director
        if "director" in msg or "directed" in msg:
            return "director"
        
        # Screenwriter
        if "screenwriter" in msg or "writer" in msg or "wrote" in msg or "written" in msg:
            return "screenwriter"
        
        # Composer
        if "composer" in msg or "music" in msg or "score" in msg:
            return "composer"
        
        # Cast
        if "cast" in msg or "actor" in msg or "actress" in msg or "starring" in msg or "starred" in msg:
            return "cast"
        
        # Producer
        if "producer" in msg or "produced" in msg:
            return "producer"
        
        # Cinematographer
        if "cinematographer" in msg or "cinematography" in msg or "director of photography" in msg:
            return "cinematographer"
        
        # Editor
        if "editor" in msg or "edited" in msg or "editing" in msg:
            return "editor"
        
        # Awards
        if "award" in msg or "won" in msg or "nominated" in msg or "nomination" in msg or 'win' in msg:
            if "nominated" in msg:
                return "nominated"
            return "awards"
        
        # Based on
        if "based on" in msg or "adapted from" in msg or "adaptation" in msg:
            return "based_on"
        
        # Duration/Runtime
        if "runtime" in msg or "duration" in msg or "long" in msg or "length" in msg:
            return "duration"
        
        # Budget
        if "budget" in msg or "cost" in msg:
            return "budget"
        
        # Box office
        if "box office" in msg or "gross" in msg or "earnings" in msg or "revenue" in msg:
            return "box_office"
        
        # Genre
        if "genre" in msg:
            return "genre"
        
        # Rating
        if "rating" in msg or "rated" in msg:
            return "rating"
        
        # Release date
        if "released" in msg or "release" in msg or "come out" in msg or "when" in msg or "date" in msg:
            return "release_date"
        
        # Country
        if "country" in msg or "from what country" in msg or "where" in msg:
            return "country"
        
        return None

    def detect_requested_approach(self, message):
        """Detect if the user explicitly asks for factual or embedding approach"""
        msg = message.lower()
        if "factual approach" in msg or "use sparql" in msg:
            return "factual"
        if "embedding approach" in msg or "use embeddings" in msg:
            return "embedding"
        if "recommendation" in msg or "recommended" in msg or "recommend" in msg or "movies like" in msg or "similar movies" in msg:
            return "recommendation"
        return None
    
    def get_entity_uri_by_label(self, label):
        """
        Try to find the entity URI for a label.
        Prioritizes movies over other entity types to avoid selecting books, franchises, etc.
        
        Args:
            label: Entity label (string)
            
        Returns:
            URI string or None
        """
        
        # PRIORITY 1: Check movie_label_dict first (films only)
        if label in self.movie_label_dict:
            uris = self.movie_label_dict[label]
            if uris:
                if len(uris) > 1:
                    return self._pick_best_movie(uris)
                return uris[0]
        
        # PRIORITY 2: Check label_entity_dict (all entities)
        if label in self.label_entity_dict:
            uris = self.label_entity_dict[label]
            if uris:
                return uris[0]
        
        # PRIORITY 3: Try fuzzy matching with edit distance
        best_match = None
        best_distance = float('inf')
        
        # Try movie labels first
        for movie_label in self.movie_label_dict.keys():
            distance = editdistance.eval(label.lower(), movie_label.lower())
            if distance < best_distance and distance <= 5:  # Threshold of 5
                best_distance = distance
                best_match = movie_label
        
        if best_match:
            return self.movie_label_dict[best_match][0]
        
        # Fallback: Try all entity labels
        for entity_label in self.label_entity_dict.keys():
            distance = editdistance.eval(label.lower(), entity_label.lower())
            if distance < best_distance and distance <= 5:
                best_distance = distance
                best_match = entity_label
        
        if best_match:
            return self.label_entity_dict[best_match][0]
        
        return None

    def _pick_best_movie(self, uris):
        """
        When multiple movies have the same title, pick the most relevant one.
        Heuristic: Pick the most recent one (likely most popular/relevant).
    
        Args:
            uris: List of movie URIs with same title
        
        Returns:
            Best URI (string)
        """
        movie_years = []
    
        for uri in uris:
            year = self._get_year(uri)
            if year:
                movie_years.append((uri, year))
    
        if movie_years:
            # Sort by year descending (most recent first)
            movie_years.sort(key=lambda x: x[1], reverse=True)
            print(f"DEBUG: Multiple movies found, picking most recent: {movie_years[0][1]}")
            return movie_years[0][0]
    
        # Fallback: return first if no year info
        return uris[0]

    def _get_year(self, uri):
        """Get release year for a movie"""
        query = f"""
        SELECT ?date WHERE {{
            <{uri}> <http://www.wikidata.org/prop/direct/P577> ?date .
        }} LIMIT 1
        """
        try:
            res = list(self.graph.query(query))
            if res:
                return int(str(res[0][0])[:4])
        except:
            pass
        return None

    def get_entity_type_id(self, entity_uri):
        """Return the QID type (P31) for an entity to include in embedding answers"""
        query = f"""
        SELECT DISTINCT ?type
        WHERE {{
            <{entity_uri}> <http://www.wikidata.org/prop/direct/P31> ?type .
        }}
        LIMIT 1
        """
        try:
            results = list(self.graph.query(query))
        except Exception:
            return "Unknown"
        if not results:
            return "Unknown"
        uri = str(results[0][0])
        return uri.split("/")[-1] if "/" in uri else uri
    
    def _format_answer_list(self, values, q_type):
        """
        Format multiple values naturally.
        
        Args:
            values: List of answer values
            q_type: Question type
            
        Returns:
            Naturally formatted string
        """
        if len(values) == 0:
            return "unknown"
        elif len(values) == 1:
            return values[0]
        elif len(values) == 2:
            return f"{values[0]} and {values[1]}"
        elif len(values) <= 5:
            # "A, B, C, and D"
            return ", ".join(values[:-1]) + f", and {values[-1]}"
        else:
            # Too many - show first 5
            return ", ".join(values[:4]) + f", and {len(values) - 4} others"
    
    def _format_natural_response(self, q_type, movie_name, answer):
        """
        Format the answer in natural language using templates.
        
        Args:
            q_type: Question type ('director', 'genre', etc.)
            movie_name: Name of the movie
            answer: The factual answer
            
        Returns:
            Naturally formatted response string
        """
        # Optional conversational starters (70% no starter, 30% with starter)
        starters = [
            "", "", "", "", "", "", "",  # 70% of time - no starter
            "Let me check... ",          # 10% of time
            "Sure! ",                    # 10% of time
            "Great question! ",          # 10% of time
        ]
        
        starter = random.choice(starters)
        
        # Get templates for this question type
        templates = self.response_templates.get(q_type)
        
        if not templates:
            # Fallback if no template exists
            return answer
        
        # Pick a random template for variety
        template = random.choice(templates)
        
        # Format the template
        try:
            formatted = template.format(movie=movie_name, answer=answer)
            return starter + formatted
        except Exception as e:
            print(f"Error formatting response: {e}")
            # Fallback if formatting fails
            return answer
    
    def handle_question(self, message, q_type, movies):
        """Answer the question using factual, embedding, or both approaches"""
        requested_approach = self.detect_requested_approach(message)
        
        if not movies:
            return "I can only answer questions when I recognize the movie title. Could you mention a specific movie?"
        
        movie = movies[0]
        movie_name = movie  # Store for formatting
        print(f"DEBUG: type={q_type}, approach={requested_approach}, movie={movies}")
        
        # Get the relation URI for this question type
        relation = QUESTION_RELATION_MAP.get(q_type)
        
        # Check if we know how to handle this question type
        if not relation:
            return f"I'm not sure how to answer questions about '{q_type}'. I can help with directors, cast, genres, release dates, and more!"
        
        # Get the movie URI
        movie_uri = self.get_entity_uri_by_label(movies[0])
        if not movie_uri:
            return f"I'm sorry, I couldn't find '{movies[0]}' in my database. Could you check the spelling?"

        factual_response = None
        embedding_response = None

        # FACTUAL APPROACH
        if requested_approach != "embedding":
            try:
                # Properties that return literal/numeric values (not entities)
                literal_properties = {'release_date', 'duration', 'budget', 'box_office'}
                
                if q_type in literal_properties:
                    # Query for literal values directly
                    query = f"SELECT DISTINCT ?v WHERE {{ <{movie_uri}> <{relation}> ?v }}"
                else:
                    # Query for entities and their labels
                    query = f"""
                    SELECT DISTINCT ?label WHERE {{
                        <{movie_uri}> <{relation}> ?obj .
                        OPTIONAL {{
                            ?obj <http://www.w3.org/2000/01/rdf-schema#label> ?label .
                        }}
                    }}
                    """
                
                results = list(self.graph.query(query))
                
                if results:
                    values = []
                    for row in results:
                        val = str(row[0])
                        if val not in values:
                            values.append(val)
                    
                    # Format the list naturally
                    answer_text = self._format_answer_list(values, q_type)
                    
                    # Format with natural language template
                    factual_response = self._format_natural_response(q_type, movie_name, answer_text)
                    
            except Exception as e:
                print(f"SPARQL error: {e}")

        # EMBEDDING APPROACH
        if requested_approach != "factual":
            # Only try embeddings if explicitly requested OR factual failed
            if requested_approach == "embedding" or not factual_response:
                answer_uri = self.embeddings.find_answer(movie_uri, relation)
                if answer_uri:
                    label = self.entity_label_dict.get(answer_uri, "Unknown")
                    qid = self.get_entity_type_id(answer_uri)
                    answer_text = f"{label} (type: {qid})"
                    
                    # Format with natural language template
                    embedding_response = self._format_natural_response(q_type, movie_name, answer_text)

        # RETURN COMBINED ANSWERS
        if requested_approach == "factual":
            return factual_response or f"I'm sorry, I couldn't find that information about {movie_name} using the factual approach."
        
        if requested_approach == "embedding":
            return embedding_response or f"I'm sorry, I couldn't find that information about {movie_name} using embeddings."

        # When approach not specified (one-hop questions):
        # Priority: Factual first, then embedding fallback
        if factual_response:
            return factual_response
        elif embedding_response:
            return embedding_response
        else:
            return f"I'm sorry, I couldn't find information about that for {movie_name}. Maybe try asking about something else, like the director or genre?"
