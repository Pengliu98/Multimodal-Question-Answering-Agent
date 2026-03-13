import os
import json
from pathlib import Path

class ImageHandler:
    """
    Handles image-related queries and retrieval from multimedia dataset.
    """
    
    def __init__(self, graph, entity_label_dict, image_base_path="/space_mounts/atai-hs25/dataset/images"):
        self.graph = graph
        self.entity_label_dict = entity_label_dict
        self.image_base_path = image_base_path
        
        # Load image data
        print("Loading image data...")
        self.images_data = self._load_images_json()
        print(f"Loaded {len(self.images_data)} images\n")
        
        # Build IMDb to Wikidata mapping
        print("Building IMDb → Wikidata mapping...")
        self.imdb_to_wikidata = self._build_imdb_mapping()
        print(f"Mapped {len(self.imdb_to_wikidata)} IMDb IDs\n")
        
        # Build entity to images mapping
        print("Building entity → images mapping...")
        self.entity_images = self._build_entity_image_mapping()
        print(f"Mapped {len(self.entity_images)} entities to images\n")
    
    def _load_images_json(self):
        """Load images.json"""
        mapping_file = "/space_mounts/atai-hs25/dataset/additional/images.json"
        
        try:
            with open(mapping_file, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"ERROR loading images.json: {e}")
            return []
    
    def _build_imdb_mapping(self):
        """
        Build mapping from IMDb IDs to Wikidata Q IDs.
        Uses P345 (IMDb ID) property from the graph.
        """
        mapping = {}
        
        # Query for all IMDb IDs in the graph
        query = """
        SELECT ?entity ?imdbId WHERE {
            ?entity <http://www.wikidata.org/prop/direct/P345> ?imdbId .
        }
        """
        
        results = self.graph.query(query)
        
        for entity, imdb_id in results:
            entity_uri = str(entity)
            imdb_str = str(imdb_id)
            
            # Extract Q-ID
            qid = entity_uri.split('/')[-1]
            
            mapping[imdb_str] = qid
        
        return mapping
    
    def _build_entity_image_mapping(self):
        entity_images = {}
    
        for img_obj in self.images_data:
        
            # Process movies - store full object
            for imdb_id in img_obj.get("movie", []):
                if imdb_id in self.imdb_to_wikidata:
                    qid = self.imdb_to_wikidata[imdb_id]
                
                    if qid not in entity_images:
                        entity_images[qid] = {"movie_images": [], "person_images": []}
                
                    # Store the whole image object
                    entity_images[qid]["movie_images"].append(img_obj)
        
            # Process cast members - store full object
            for imdb_id in img_obj.get("cast", []):
                if imdb_id in self.imdb_to_wikidata:
                    qid = self.imdb_to_wikidata[imdb_id]
                
                    if qid not in entity_images:
                        entity_images[qid] = {"movie_images": [], "person_images": []}
                
                    # Store the whole image object so we can filter by cast count
                    entity_images[qid]["person_images"].append(img_obj)
    
        return entity_images


    
    def detect_image_query(self, message):
        """Detect if the message is asking for an image."""
        message_lower = message.lower()
    
        # Specific poster keywords
        if any(word in message_lower for word in ['poster of', 'poster for', 'movie poster']):
            return 'movie_poster'
    
        # Specific person keywords
        if any(word in message_lower for word in ['what does', 'look like']):
            return 'person_photo'
    
        # Generic image keywords - return a default and let get_image_for_entity() figure it out
        if any(word in message_lower for word in ['picture', 'pic', 'photo', 'image', 'show me']):
            return 'auto_detect'  # New type
    
        return None
    
    def extract_entity_from_query(self, message):
        """Extract person or movie name from image query."""
        import re
        
        patterns = [
        # MOST SPECIFIC FIRST: "show/give/... (me)? a/an picture/photo/image/pic of X"
        r'(?:show|give|display|find|get|offer|provide|present)\s+(?:me\s+)?(?:a|an)\s+(?:picture|photo|image|pic)\s+of\s+(.*?)(?:\?|\.|\!|$)',
    
        # "poster of X"
        r'poster\s+of\s+(.*?)(?:\?|\.|\!|$)',
    
        # "what does X look like"
        r'what\s+does\s+(.*?)\s+look\s+like',
    
        # LEAST SPECIFIC LAST: "show/give/... (me)? X"
        r'(?:show|give|display|find|get|offer|provide|present)\s+(?:me\s+)?(.*?)(?:\?|\.|\!|$)',
]
    
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                entity_name = match.group(1).strip()
                if entity_name.lower().startswith('the '):
                    entity_name = entity_name[4:]
                entity_name = entity_name.rstrip('.,!?')
                return entity_name
        
        return None
    
    def get_entity_uri_by_label(self, label):
        """Find entity URI by label with fuzzy matching"""
    
        # Try exact match first
        for uri, entity_label in self.entity_label_dict.items():
            if entity_label.lower() == label.lower():
                return uri
    
        # Try fuzzy match
        from difflib import get_close_matches
    
        all_labels = list(self.entity_label_dict.values())
        close_matches = get_close_matches(label, all_labels, n=5, cutoff=0.70)  # Get top 5
    
        if close_matches:
            print(f"DEBUG: Fuzzy matches for '{label}': {close_matches[:3]}")
        
            # Try to find the MOVIE version first
            for match in close_matches:
                for uri, entity_label in self.entity_label_dict.items():
                    if entity_label == match:
                        # Check if it has images (likely a movie/person)
                        qid = uri.split('/')[-1]
                        if qid in self.entity_images:
                            print(f"DEBUG: Found match with images: '{match}' → {uri}")
                            return uri
        
            # Fallback to first match
            best_match = close_matches[0]
            print(f"DEBUG: Using first match: '{best_match}'")
            for uri, entity_label in self.entity_label_dict.items():
                if entity_label == best_match:
                    return uri
    
        return None
    
    def get_image_for_entity(self, entity_uri, query_type):
        
        
        """
        Get image path for an entity.
    
        Args:
            entity_uri: Wikidata URI like "http://www.wikidata.org/entity/Q175535"
            query_type: "movie_poster", "person_photo", or "auto_detect"
    
        Returns:
            Image path or None
        """
        # Extract Q-ID
        qid = entity_uri.split('/')[-1]
    
        if qid not in self.entity_images:
            print(f"DEBUG: No images found for {qid}")
            return None
    
        images = self.entity_images[qid]
    
        # Check what type of images we have available
        has_movie_images = bool(images.get("movie_images"))
        has_person_images = bool(images.get("person_images"))
    
        print(f"DEBUG: has_movie_images={has_movie_images}, has_person_images={has_person_images}")
    
        # ========== AUTO-DETECT LOGIC ==========
        if query_type == "auto_detect":
            # Prioritize movie images first (posters are usually better quality)
            if has_movie_images:
                print(f"DEBUG: Auto-detected as movie")
                query_type = "movie_poster"
            elif has_person_images:
                print(f"DEBUG: Auto-detected as person")
                query_type = "person_photo"
            else:
                print(f"DEBUG: No images available for auto-detect")
                return None
    
        # ========== MOVIE POSTER LOGIC ==========
        if query_type == "movie_poster":
            movie_imgs = images.get("movie_images", [])
        
            if not movie_imgs:
                print(f"DEBUG: No movie images found")
                return None
        
            # Prioritize poster type
            type_priority = ["poster", "still_frame", "event", "behind_the_scenes"]
        
            # Sort by type priority
            movie_imgs_sorted = sorted(
                movie_imgs,
                key=lambda x: type_priority.index(x["type"]) if x["type"] in type_priority else len(type_priority)
            )
        
            img_path = movie_imgs_sorted[0]["img"]
            img_type = movie_imgs_sorted[0]["type"]
            print(f"DEBUG: Found poster: {img_path} (type={img_type})")
            return img_path
    
        # ========== PERSON PHOTO LOGIC ==========
        elif query_type == "person_photo":
            person_imgs = images.get("person_images", [])
        
            if not person_imgs:
                print(f"DEBUG: No person images found")
                return None
        
            # Filter for solo photos (cast array has only 1 person)
            solo_imgs = [
                img for img in person_imgs
                if len(img.get("cast", [])) == 1
            ]
        
            print(f"DEBUG: Found {len(solo_imgs)} solo images out of {len(person_imgs)} total")
        
            # If we have solo images, use them. Otherwise fall back to any image
            imgs_to_use = solo_imgs if solo_imgs else person_imgs
        
            # Prioritize publicity photos for persons
            type_priority = ["publicity", "profile", "event", "behind_the_scenes"]
        
            # Sort by type priority
            imgs_sorted = sorted(
                imgs_to_use,
                key=lambda x: type_priority.index(x["type"]) if x["type"] in type_priority else len(type_priority)
            )
        
            img_path = imgs_sorted[0]["img"]
            img_type = imgs_sorted[0]["type"]
            cast_count = len(imgs_sorted[0].get("cast", []))
            print(f"DEBUG: Found photo: {img_path} (type={img_type}, cast_count={cast_count})")
            return img_path

        return None

    def find_image_file(self, image_filename):
        """
        Find the actual image file in the dataset.
        
        Args:
            image_filename: Like "0000/evjpqWPUY4VpOdyLpeRfkGU8DiR.jpg"
        
        Returns:
            Full path to image file or None
        """
        if not image_filename:
            return None
        
        # Build full path
        full_path = os.path.join(self.image_base_path, image_filename)
        
        if os.path.exists(full_path):
            print(f"DEBUG: Found image at {full_path}")
            return full_path
        
        print(f"DEBUG: Image file not found at {full_path}")
        return None
    
    def handle_image_query(self, message):
        """
        Main handler for image queries.
        
        Returns:
            tuple: (image_path, entity_name) or (None, None)
        """
        # Detect if it's an image query
        query_type = self.detect_image_query(message)
        if not query_type:
            return None, None
        
        print(f"DEBUG: Image query detected, type = {query_type}")
        
        # Extract entity name
        entity_name = self.extract_entity_from_query(message)
        if not entity_name:
            return None, None
        
        print(f"DEBUG: Extracted entity name = '{entity_name}'")
        
        # Get entity URI
        entity_uri = self.get_entity_uri_by_label(entity_name)
        if not entity_uri:
            from difflib import get_close_matches
            all_labels = list(self.entity_label_dict.values())
            suggestions = get_close_matches(entity_name, all_labels, n=2, cutoff=0.6)
            
            if suggestions:
                suggestion_text = f"Did you mean: {' or '.join(suggestions)}?"
                return None, f"{entity_name} (not found. {suggestion_text})"
            else:
                return None, entity_name
        
        print(f"DEBUG: Found entity URI = {entity_uri}")
        
        # Get image for entity
        image_ref = self.get_image_for_entity(entity_uri, query_type)
        if not image_ref:
            print(f"DEBUG: No image available for '{entity_name}'")
            return None, entity_name
        
        # Find actual file
        image_path = self.find_image_file(image_ref)
        if not image_path:
            print(f"DEBUG: Could not find image file for '{image_ref}'")
            return None, entity_name
        
        return image_path, entity_name
