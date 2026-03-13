import csv
import numpy as np
from sklearn.metrics.pairwise import pairwise_distances
from utils import EMB_BASE_PATH

class EmbeddingManager:
    def __init__(self, base_path: str = EMB_BASE_PATH):
        self.base_path = base_path
        self.entity_emb = None
        self.rel_emb = None
        self.idx_to_entity = {}
        self.entity_index = {}
        self.rel_index = {}
        self.load_embeddings()

    # embeddings loading and usage
    def load_embeddings(self):
        # Load all embeddings and their mappings
        self.entity_emb = np.load(self.base_path + "entity_embeds.npy")
        self.rel_emb = np.load(self.base_path + "relation_embeds.npy")

        self.idx_to_entity = {}
        self.entity_index = {}
        with open(self.base_path + "entity_ids.del", "r", encoding="utf-8") as f:
            for row in csv.reader(f, delimiter="\t"):
                idx, uri = int(row[0]), row[1]
                self.idx_to_entity[idx] = uri
                self.entity_index[uri] = idx

        self.rel_index = {}
        with open(self.base_path + "relation_ids.del", "r", encoding="utf-8") as f:
            for row in csv.reader(f, delimiter="\t"):
                idx, uri = int(row[0]), row[1]
                self.rel_index[uri] = idx

    def find_answer(self, entity_uri, relation_uri):
        # Use TransE embeddings: entity + relation ≈ answer
        if entity_uri not in self.entity_index or relation_uri not in self.rel_index:
            return None

        e_vec = self.entity_emb[self.entity_index[entity_uri]]
        r_vec = self.rel_emb[self.rel_index[relation_uri]]
        combined = (e_vec + r_vec).reshape((1, -1))

        distances = pairwise_distances(combined, self.entity_emb).flatten()
        best_idx = distances.argsort()[0]
        return self.idx_to_entity[best_idx]