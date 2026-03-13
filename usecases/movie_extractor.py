import re

class MovieExtractor:
    def __init__(self, label_entity_dict):
        self.label_entity_dict = label_entity_dict
        self.normalized_to_original = {}
        
        # Regular stopwords (always skip)
        self.stopwords = {
            'i', 'my', 'you', 'your', 'he', 'she', 'is', 'am', 'are',
            'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'a', 'an', 'the', 'and', 'or', 'but',
            'if', 'of', 'at', 'by', 'for', 'with', 'about', 'to', 'from',
            'in', 'on', 'who', 'what', 'when', 'where', 'why', 'how',
            'can', 'could', 'will', 'would', 'should', 'tell', 'ask',
            'show', 'give', 'that', 'this', 'these', 'those', 'xxx'
        }
        
        # Ambiguous titles - pronouns/common words that are also movies
        self.ambiguous_titles = {'her', 'me', 'him', 'it', 'us', 'them', 'up', 'go', 'in', 'out', 'box', 'the box', 'more', 'country', 'made', 'watch', 'other', 'women'}
        
        # Movie context keywords for fallback
        self.movie_keywords = {
            'movie', 'movies', 'film', 'films', 'director', 'cast', 'genre',
            'rating', 'recommend', 'like', 'similar', 'watched', 'seen',
            'favorite', 'loved', 'enjoyed', 'starring', 'screenwriter', 'composer', 'award', 'office'
        }
        
        # Build normalized index
        articles = ['the', 'a', 'an']
        
        for label in label_entity_dict.keys():
            normalized = self._normalize(label)
            
            # Skip stopwords but NOT ambiguous titles
            if normalized in self.stopwords:
                continue
            
            # Skip very short labels
            if len(normalized) <= 1:
                continue
            
            self.normalized_to_original[normalized] = label
            
            # Also store version without leading article
            words = normalized.split()
            if words and words[0] in articles:
                without_article = ' '.join(words[1:])
                if without_article not in self.stopwords and len(without_article) > 1:
                    self.normalized_to_original[without_article] = label
    
    def _normalize(self, text):
        """Normalize text for matching"""
        text = text.lower()
        
        # Remove all types of quotes
        text = text.replace('\u2018', '')  # '
        text = text.replace('\u2019', '')  # '
        text = text.replace('\u201C', '')  # "
        text = text.replace('\u201D', '')  # "
        text = text.replace('"', '')
        text = text.replace("'", '')
        
        # Remove other punctuation
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Collapse multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _check_capitalization(self, original_message, word):
        """
        Check if a word appears capitalized in the original message.
        Returns True if the word is capitalized, False otherwise.
        """
        # Find all occurrences of the word (case-insensitive)
        pattern = r'\b' + re.escape(word) + r'\b'
        matches = list(re.finditer(pattern, original_message, re.IGNORECASE))
        
        if not matches:
            return False
        
        # Check if ANY occurrence is capitalized
        for match in matches:
            start = match.start()
            original_word = original_message[start:start + len(word)]
            if original_word and original_word[0].isupper():
                return True
        
        return False
    
    def _has_movie_context(self, words):
        """Check if the message contains movie-related context words"""
        return any(word in self.movie_keywords for word in words)
    
    def extract_movies(self, message):
        original_message = message
        normalized_msg = self._normalize(message)
        normalized_words = normalized_msg.split()
    
       
    
        has_movie_context = self._has_movie_context(normalized_words)
    
        found_movies = []
        used_indices = set()
    
        for length in range(min(15, len(normalized_words)), 0, -1):
            for i in range(len(normalized_words) - length + 1):
                if any(idx in used_indices for idx in range(i, i + length)):
                    continue
            
                ngram = ' '.join(normalized_words[i:i+length])
            
                if len(ngram) <= 1 or ngram in self.stopwords:
                    continue
            
            
                # Check if it's in dictionary first
                if ngram in self.normalized_to_original:
                
                    # HYBRID APPROACH for ambiguous titles
                    if ngram in self.ambiguous_titles:
                        print(f"DEBUG:   → Is ambiguous title")
                        is_capitalized = self._check_capitalization(original_message, ngram)
                        print(f"DEBUG:   → Is capitalized: {is_capitalized}")
                    
                        if is_capitalized:
                            print(f"DEBUG:   → Extracting (capitalized)")
                            original = self.normalized_to_original[ngram]
                            found_movies.append(original)
                            used_indices.update(range(i, i + length))
                        else:
                            movie_intro_words = {'like', 'of', 'watched', 'seen', 'loved', 'enjoyed', 'similar'}
                            prev_word = normalized_words[i-1] if i > 0 else None
                            print(f"DEBUG:   → Previous word: '{prev_word}'")
                        
                            if i > 0 and normalized_words[i-1] in movie_intro_words:
                                print(f"DEBUG:   → Extracting (has adjacent intro)")
                                original = self.normalized_to_original[ngram]
                                found_movies.append(original)
                                used_indices.update(range(i, i + length))
                            else:
                                print(f"DEBUG:   → Skipping (no adjacent intro)")
                    else:
                        # Not ambiguous, just extract
                        print(f"DEBUG:   → Extracting (not ambiguous)")
                        original = self.normalized_to_original[ngram]
                        found_movies.append(original)
                        used_indices.update(range(i, i + length))
    
        print(f"DEBUG: Final result: {found_movies}")
        return found_movies
