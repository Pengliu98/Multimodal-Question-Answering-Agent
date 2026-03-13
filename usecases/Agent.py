from rdflib import Graph
from speakeasypy import Chatroom, EventType, Speakeasy
import time
from utils import build_movie_label_dict
from image_handler import ImageHandler

import inspect


from utils import (
    DEFAULT_HOST_URL,
    GRAPH_PATH,
    build_label_dicts,
)

from Embeddings import EmbeddingManager
from movie_extractor import MovieExtractor
from property_query import QuestionHandler
from recommendation import Recommender

class Agent:
    def __init__(self, username: str, password: str):
        self.username = username

        # Load RDF graph
        print("Loading knowledge graph...")
        self.graph = Graph()
        self.graph.parse(GRAPH_PATH, format="nt")
        print(f"Graph loaded with {len(self.graph):,} triples.\n")

        # Label dictionaries
        print("Building label dictionaries...")
        self.label_entity_dict, self.entity_label_dict = build_label_dicts(self.graph)
        print("Label dictionaries ready.\n")

        # Build movie-only label dictionary
        print("Building movie-only label dictionary...")
        self.movie_label_dict = build_movie_label_dict(self.graph)
        print("Movie label dictionary ready.\n")

        # Add image handler
        print("Initializing image handler...")
        self.image_handler = ImageHandler(
            self.graph,
            self.entity_label_dict
        )
        print("Image handler ready.\n")

        

        self.embeddings = EmbeddingManager()

        self.movie_extractor = MovieExtractor(self.movie_label_dict)
        self.question_handler = QuestionHandler(
            self.graph,
            self.embeddings,
            self.label_entity_dict,
            self.entity_label_dict,
            self.movie_label_dict
        )
        self.recommender = Recommender(
            self.graph,
            self.movie_label_dict,
            self.entity_label_dict,
        )

        # Connect to Speakeasy server
        self.speakeasy = Speakeasy(host=DEFAULT_HOST_URL, username=username, password=password)
        self.speakeasy.login()
        self.speakeasy.register_callback(self.on_new_message, EventType.MESSAGE)

    def debug_single_movie(self, movie_name):
        """Debug why a movie has no factual information"""
        
        print(f"\n{'='*60}")
        print(f"DEBUGGING: {movie_name}")
        print(f"{'='*60}")
        
        # Step 1: Can we find the URI?
        uri = self.question_handler.get_entity_uri_by_label(movie_name)
        print(f"\n1. URI found by get_entity_uri_by_label():")
        print(f"   {uri}")
        
        if not uri:
            print("   No URI found!")
            return
        
        # Step 2: What type is this entity?
        type_query = f"""
        SELECT ?type ?typeLabel WHERE {{
            <{uri}> <http://www.wikidata.org/prop/direct/P31> ?type .
            ?type <http://www.w3.org/2000/01/rdf-schema#label> ?typeLabel .
        }}
        """
        
        print(f"\n2. Entity type (P31):")
        types = list(self.graph.query(type_query))
        if types:
            for t in types:
                print(f"   - {t[1]}")
        else:
            print("   No type found!")
        
        # Step 3: Does it have a director?
        director_query = f"""
        SELECT ?director ?directorLabel WHERE {{
            <{uri}> <http://www.wikidata.org/prop/direct/P57> ?director .
            ?director <http://www.w3.org/2000/01/rdf-schema#label> ?directorLabel .
        }}
        """
        
        print(f"\n3. Director (P57):")
        directors = list(self.graph.query(director_query))
        if directors:
            for d in directors:
                print(f"   - {d[1]}")
        else:
            print("   No director found!")
        
        # Step 4: Does it have awards?
        awards_query = f"""
        SELECT ?award ?awardLabel WHERE {{
            <{uri}> <http://www.wikidata.org/prop/direct/P166> ?award .
            ?award <http://www.w3.org/2000/01/rdf-schema#label> ?awardLabel .
        }} LIMIT 5
        """
        
        print(f"\n4. Awards (P166):")
        awards = list(self.graph.query(awards_query))
        if awards:
            for a in awards:
                print(f"   - {a[1]}")
        else:
            print("   No awards found!")
        
        # Step 5: Check how many entities have this label
        count_query = f"""
        SELECT ?entity ?type ?typeLabel WHERE {{
            ?entity <http://www.w3.org/2000/01/rdf-schema#label> "{movie_name}" .
            OPTIONAL {{
                ?entity <http://www.wikidata.org/prop/direct/P31> ?type .
                ?type <http://www.w3.org/2000/01/rdf-schema#label> ?typeLabel .
            }}
        }}
        """
        
        print(f"\n5. How many entities have this exact label:")
        entities = list(self.graph.query(count_query))
        print(f"   Found {len(entities)} entities:")
        for i, ent in enumerate(entities[:5]):  # Show first 5
            print(f"   {i+1}. {ent[0]}")
            print(f"      Type: {ent[2] if len(ent) > 2 else 'No type'}")
        
        # Step 6: Is it in movie_label_dict?
        print(f"\n6. In movie_label_dict?")
        if movie_name in self.movie_label_dict:
            print(f"   Yes: {self.movie_label_dict[movie_name]}")
        else:
            print(f"   No!")
        
        print(f"{'='*60}\n")

    def debug_search_movie_labels(self, search_term):
        """Search for all movie labels containing a term"""
        
        print(f"\n{'='*60}")
        print(f"SEARCHING: Movies with '{search_term}' in label")
        print(f"{'='*60}")
        
        # Search in movie_label_dict
        print(f"\nIn movie_label_dict:")
        found_in_dict = []
        for label, uris in self.movie_label_dict.items():
            if search_term.lower() in label.lower():
                found_in_dict.append((label, uris))
        
        if found_in_dict:
            for label, uris in found_in_dict[:10]:  # Show first 10
                print(f"  - '{label}': {uris[0]}")
        else:
            print(f"  No movies found with '{search_term}' in label")
        
        # Also check the graph directly
        print(f"\nIn knowledge graph (all entities):")
        query = f"""
        SELECT ?entity ?label ?type ?typeLabel WHERE {{
            ?entity <http://www.w3.org/2000/01/rdf-schema#label> ?label .
            FILTER(CONTAINS(LCASE(?label), "{search_term.lower()}"))
            OPTIONAL {{
                ?entity <http://www.wikidata.org/prop/direct/P31> ?type .
                ?type <http://www.w3.org/2000/01/rdf-schema#label> ?typeLabel .
            }}
        }} LIMIT 10
        """
        
        results = list(self.graph.query(query))
        if results:
            for r in results:
                print(f"  - Label: '{r[1]}'")
                print(f"    URI: {r[0]}")
                print(f"    Type: {r[3] if len(r) > 3 and r[3] else 'No type'}")
                print()
        else:
            print(f"No entities found")
        
        print(f"{'='*60}\n")
    
    def listen(self):
        """Start listening for events"""
        self.speakeasy.start_listening()

    @staticmethod
    def get_time():
        return time.strftime("%H:%M:%S, %d-%m-%Y", time.localtime())

    def on_new_message(self, message: str, room: Chatroom):
        """Handle new messages from Speakeasy chatrooms"""
        print("\n" + "=" * 60)
        print(f"Received: {message[:100]}...")
        print("=" * 60)

        msg_upper = message.strip().upper()
        if msg_upper.startswith("PREFIX") or msg_upper.startswith("SELECT"):
            # Execute direct SPARQL query
            try:
                results = self.graph.query(message)
                rows = [[str(v) for v in row] for row in results]
                if not rows:
                    response = "No results found."
                else:
                    response = "\n".join(" | ".join(r) for r in rows[:10])
            except Exception as e:
                response = f"Error running SPARQL: {e}"
            room.post_messages(response)
            return
            
        # CHECK FOR IMAGE QUERIES
        image_path, entity_name = self.image_handler.handle_image_query(message)
        if image_path:
            # Image found! Post it
            try:
                # Remove base path
                image_id = image_path.replace('/space_mounts/atai-hs25/dataset/images/', '')
                
                # Remove .jpg extension properly
                if image_id.endswith('.jpg'):
                    image_id = image_id[:-4]
                
                room.post_messages(f"Here's the picture:image:{image_id}")
                
                print(f"Posted image: {image_path}")
                print(f"Image ID used: {image_id}")
                return
            except Exception as e:
                print(f"Error posting image: {e}")
                room.post_messages(f"Sorry, I found an image for {entity_name} but couldn't display it.")
                return
        elif entity_name:
            # Image query detected but no image found
            room.post_messages(f"Sorry, I couldn't find an image for {entity_name}.")
            return


        # Film extraction
        movies = self.movie_extractor.extract_movies(message)
        print(f"DEBUG: extracted movies = {movies}")

        # Approach selection
        approach = self.question_handler.detect_requested_approach(message)
        q_type = self.question_handler.detect_question_type(message)

        # RECOMMENDATION LOGIC
        if approach == "recommendation":
            # Case 1: Has movies - normal recommendation flow
            if movies and len(movies) >= 1:
                response = self.recommender.recommend(movies, user_message=message)
                room.post_messages(response)
                return
            
            # Case 2: No movies but recommendation requested
            # Check if genre + actor mentioned
            else:
                response = self._handle_genre_actor_recommendation(message)
                if response:
                    room.post_messages(response)
                    return
                else:
                    room.post_messages("I couldn't find any movies to base recommendations on. Please mention some movies you like or specify a genre!")
                    return
        
        # Handle case where 2+ movies but no explicit approach
        if len(movies) >= 2 and q_type is None:
            response = self.recommender.recommend(movies, user_message=message)
            room.post_messages(response)
            return

        # PROPERTY QUESTION LOGIC
        if q_type:
            response = self.question_handler.handle_question(message, q_type, movies)
        else:
            response = (
                "I can answer questions about directors, screenwriters, genres, "
                "ratings, release dates, and countries. "
                "You can also ask me to recommend similar movies!"
            )

        room.post_messages(response)

    def _handle_genre_actor_recommendation(self, message):
        """
        Handle recommendation queries with genre and/or actor but no movie titles.
        Examples: 
        - "Can you recommend action movies with Arnold Schwarzenegger?"
        - "I like Arnold Schwarzenegger, can you recommend his movies?"
        - "Can you recommend some horror movies?"
    
        Returns:
            Recommendation string or None if can't handle
        """
    
        # Detect if genre is mentioned
        genre = self.recommender.detect_requested_genre(message)
        print(f"DEBUG: Detected genre = '{genre}'")
    
        # Try to detect actor/person mentions in the message
        import re
    
        # Patterns to detect person names
        patterns = [
            r'i like ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'given (?:that )?i like ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'with ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'starring ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'by ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
    
        person_name = None
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                person_name = match.group(1)
                print(f"DEBUG: Detected genre='{genre}', person='{person_name}'")
                break
    
        # Build recommendation with actual movies
        if genre and person_name:
            # Both genre and actor - fetch combined
            print(f"DEBUG: Fetching genre_actor: ({genre}, {person_name})") 
            movies = self.recommender.retriever.fetch_movies("genre_actor", (genre, person_name), limit=10)
            print(f"DEBUG: Found {len(movies) if movies else 0} movies")
            response = f"Adequate recommendations will be {genre} movies starring {person_name.lower()}."
            if movies:
                response += f"\n• Examples: {self.recommender._format_movie_list(movies)}"
            return response
        
        elif person_name:
            # Just actor, no genre
            print(f"DEBUG: Fetching actor: {person_name}")
            movies = self.recommender.retriever.fetch_movies("actor", person_name, limit=10)
            response = f"Adequate recommendations will be movies starring {person_name.lower()}."
            if movies:
                response += f"\n• Examples: {self.recommender._format_movie_list(movies)}"
            else:
                response += "\n(No specific examples found in our database)" 
            return response
        
        elif genre:
            # Just genre, no actor
            print(f"DEBUG: Fetching genre: {genre}")
            movies = self.recommender.retriever.fetch_movies("genre", genre, limit=10)
            response = f"Adequate recommendations will be {genre} movies."
            if movies:
                response += f"\n• Examples: {self.recommender._format_movie_list(movies)}"
            else:
                response += "\n(No specific examples found in our database)"
            return response
        
        else:
            # Neither genre nor actor found
            return None

if __name__ == "__main__":
    bot = Agent("RedGobblingTurkey", "Rp0Wh6gZ")
    print(f"Agent '{bot.username}' ready at {bot.get_time()}\n")
    # Run the debug:
    # bot.debug_single_movie("It")
    # bot.debug_single_movie("Us")
    # bot.debug_single_movie("Him")

    # bot.debug_search_movie_labels("It")
    # bot.debug_search_movie_labels("Us")
    # bot.debug_search_movie_labels("Him")
    
    bot.listen()