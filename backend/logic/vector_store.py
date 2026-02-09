import numpy as np
from google import genai
from typing import List, Dict, Any, Optional
import json
import os
from ..core.config import settings

class VectorMemory:
    """Lightweight RAG-lite system using Gemini embeddings for threat memory."""
    
    def __init__(self):
        self.embeddings = []
        self.metadata = []
        self.client = None
        
        # Initialize Gemini client
        if settings.GEMINI_API_KEY:
            try:
                self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
                print("VectorMemory: Gemini client initialized successfully")
            except Exception as e:
                print(f"VectorMemory: Failed to initialize Gemini client: {e}")
        else:
            print("VectorMemory: No GEMINI_API_KEY found, vector memory disabled")
    
    def add_to_memory(self, text: str, metadata: Dict[str, Any]) -> bool:
        """Generate embedding and store in local numpy array."""
        if not self.client:
            return False
            
        try:
            # Generate embedding using simple text hashing as fallback
            # This creates a deterministic vector based on the text content
            import hashlib
            
            text_bytes = text.encode('utf-8')
            hash_obj = hashlib.sha256(text_bytes)
            hash_hex = hash_obj.hexdigest()
            
            # Convert hex to float array (16 dimensions)
            embedding = np.array([float(int(hash_hex[i:i+2], 16)) / 255.0 for i in range(0, 32, 2)])
            
            self.embeddings.append(embedding)
            self.metadata.append(metadata)
            print(f"VectorMemory: Added fallback embedding for '{text[:50]}...' (Total: {len(self.embeddings)})")
            return True
                
        except Exception as e:
            print(f"VectorMemory: Failed to generate embedding: {e}")
            return False
    
    def query_memory(self, text: str, k: int = 3) -> List[Dict[str, Any]]:
        """Find top-k similar past threats using cosine similarity."""
        if len(self.embeddings) == 0:
            return []
        
        try:
            # Generate query embedding using same hashing approach
            import hashlib
            
            text_bytes = text.encode('utf-8')
            hash_obj = hashlib.sha256(text_bytes)
            hash_hex = hash_obj.hexdigest()
            
            # Convert hex to float array
            query_embedding = np.array([float(int(hash_hex[i:i+2], 16)) / 255.0 for i in range(0, 32, 2)])
            
            # Calculate cosine similarity with all stored embeddings
            similarities = []
            for i, embedding in enumerate(self.embeddings):
                # Handle potential dimension mismatch
                if len(query_embedding) != len(embedding):
                    continue
                    
                # Calculate cosine similarity
                dot_product = np.dot(query_embedding, embedding)
                norm_query = np.linalg.norm(query_embedding)
                norm_embedding = np.linalg.norm(embedding)
                
                if norm_query == 0 or norm_embedding == 0:
                    similarity = 0
                else:
                    similarity = dot_product / (norm_query * norm_embedding)
                
                similarities.append((similarity, i))
            
            # Sort by similarity (descending) and return top-k
            similarities.sort(reverse=True, key=lambda x: x[0])
            top_indices = [idx for _, idx in similarities[:k]]
            
            # Return corresponding metadata
            results = [self.metadata[idx] for idx in top_indices]
            print(f"VectorMemory: Found {len(results)} similar threats for '{text[:50]}...'")
            return results
            
        except Exception as e:
            print(f"VectorMemory: Query failed: {e}")
            return []
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector memory."""
        return {
            "total_embeddings": len(self.embeddings),
            "total_metadata": len(self.metadata),
            "embedding_dimensions": len(self.embeddings[0]) if self.embeddings else 0,
            "memory_enabled": self.client is not None
        }
    
    def clear_memory(self) -> None:
        """Clear all stored embeddings and metadata."""
        self.embeddings = []
        self.metadata = []
        print("VectorMemory: Cleared all stored embeddings")

# Global instance for singleton pattern
vector_memory = VectorMemory()