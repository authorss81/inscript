// inscript_v380/ast_cache/ast_cache.py
# Advanced AST Caching System for InScript v3.8.0
# Features:
#   - Content-based caching (hash of source code)
#   - Incremental parsing (only changed lines)
#   - LRU eviction policy
#   - Persistence to disk
#   - Cache statistics and profiling

import hashlib
import json
import os
from collections import OrderedDict
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import threading

@dataclass
class CacheEntry:
    """Single cache entry"""
    source_hash: str
    ast: Any
    metadata: Dict[str, Any]
    created_at: str
    accessed_at: str
    access_count: int
    
    def to_dict(self) -> Dict:
        return {
            "source_hash": self.source_hash,
            "ast": str(self.ast),  # Simplified for storage
            "metadata": self.metadata,
            "created_at": self.created_at,
            "accessed_at": self.accessed_at,
            "access_count": self.access_count,
        }

class ASTCache:
    """Advanced AST caching with multiple strategies"""
    
    def __init__(self, max_entries: int = 10000, cache_dir: Optional[str] = None):
        self.max_entries = max_entries
        self.cache_dir = cache_dir or ".ast_cache"
        self.memory_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.disk_cache: Dict[str, CacheEntry] = {}
        self.lock = threading.RLock()
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.loads = 0
        self.saves = 0
        
        # Ensure cache directory
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
        
        self._load_disk_cache()
    
    def get(self, source: str) -> Optional[Any]:
        """Get AST from cache if exists"""
        with self.lock:
            source_hash = self._hash_source(source)
            
            # Check memory cache first (fast path)
            if source_hash in self.memory_cache:
                entry = self.memory_cache[source_hash]
                entry.access_count += 1
                entry.accessed_at = datetime.now().isoformat()
                
                # Move to end (LRU)
                self.memory_cache.move_to_end(source_hash)
                
                self.hits += 1
                return entry.ast
            
            # Check disk cache
            if source_hash in self.disk_cache:
                entry = self.disk_cache[source_hash]
                # Promote to memory cache
                self.memory_cache[source_hash] = entry
                self.hits += 1
                return entry.ast
            
            self.misses += 1
            return None
    
    def put(
        self,
        source: str,
        ast: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store AST in cache"""
        with self.lock:
            source_hash = self._hash_source(source)
            
            # Create cache entry
            entry = CacheEntry(
                source_hash=source_hash,
                ast=ast,
                metadata=metadata or {},
                created_at=datetime.now().isoformat(),
                accessed_at=datetime.now().isoformat(),
                access_count=1,
            )
            
            # Add to memory cache
            if source_hash in self.memory_cache:
                self.memory_cache.move_to_end(source_hash)
            else:
                self.memory_cache[source_hash] = entry
                
                # Evict if too large
                if len(self.memory_cache) > self.max_entries:
                    self._evict_lru()
            
            # Periodically save to disk
            if len(self.memory_cache) % 100 == 0:
                self._save_disk_cache()
    
    def invalidate(self, source: str) -> None:
        """Invalidate cache entry for source"""
        with self.lock:
            source_hash = self._hash_source(source)
            
            if source_hash in self.memory_cache:
                del self.memory_cache[source_hash]
            
            if source_hash in self.disk_cache:
                del self.disk_cache[source_hash]
    
    def clear(self) -> None:
        """Clear all caches"""
        with self.lock:
            self.memory_cache.clear()
            self.disk_cache.clear()
            self.hits = 0
            self.misses = 0
            self.evictions = 0
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry"""
        if self.memory_cache:
            # Pop first (oldest) item
            key = next(iter(self.memory_cache))
            entry = self.memory_cache.pop(key)
            
            # Move to disk cache
            self.disk_cache[key] = entry
            self.evictions += 1
    
    def _hash_source(self, source: str) -> str:
        """Hash source code"""
        return hashlib.sha256(source.encode()).hexdigest()[:16]
    
    def _load_disk_cache(self) -> None:
        """Load cache from disk"""
        try:
            cache_file = os.path.join(self.cache_dir, "cache.json")
            if os.path.exists(cache_file):
                with open(cache_file, "r") as f:
                    data = json.load(f)
                    for key, entry_dict in data.items():
                        entry = CacheEntry(
                            source_hash=entry_dict["source_hash"],
                            ast=entry_dict["ast"],
                            metadata=entry_dict["metadata"],
                            created_at=entry_dict["created_at"],
                            accessed_at=entry_dict["accessed_at"],
                            access_count=entry_dict["access_count"],
                        )
                        self.disk_cache[key] = entry
                self.loads += 1
        except Exception as e:
            print(f"Warning: Failed to load disk cache: {e}")
    
    def _save_disk_cache(self) -> None:
        """Save cache to disk"""
        try:
            cache_file = os.path.join(self.cache_dir, "cache.json")
            data = {k: v.to_dict() for k, v in self.disk_cache.items()}
            
            with open(cache_file, "w") as f:
                json.dump(data, f, indent=2)
            self.saves += 1
        except Exception as e:
            print(f"Warning: Failed to save disk cache: {e}")
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_hits = self.hits + self.misses
        hit_rate = (self.hits / total_hits * 100) if total_hits > 0 else 0
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total_hits,
            "hit_rate": f"{hit_rate:.2f}%",
            "evictions": self.evictions,
            "memory_entries": len(self.memory_cache),
            "disk_entries": len(self.disk_cache),
            "total_entries": len(self.memory_cache) + len(self.disk_cache),
            "loads": self.loads,
            "saves": self.saves,
        }
    
    def print_stats(self) -> None:
        """Print cache statistics"""
        stats = self.stats()
        print("\n" + "="*60)
        print("AST CACHE STATISTICS")
        print("="*60)
        for key, value in stats.items():
            print(f"{key:.<40} {value}")
        print("="*60)

class IncrementalASTCache(ASTCache):
    """Incremental parsing cache - only reparse changed lines"""
    
    def __init__(self, max_entries: int = 10000, cache_dir: Optional[str] = None):
        super().__init__(max_entries, cache_dir)
        self.line_hashes: Dict[str, List[str]] = {}
    
    def get_incremental(self, source: str, old_source: Optional[str] = None) -> Tuple[Optional[Any], List[int]]:
        """
        Get AST with incremental updates
        Returns: (AST, list of changed line numbers)
        """
        # Get full AST if exists
        ast = self.get(source)
        if ast is None:
            return None, list(range(len(source.split('\n'))))
        
        if old_source is None:
            return ast, []
        
        # Find changed lines
        new_lines = source.split('\n')
        old_lines = old_source.split('\n')
        
        changed_lines = []
        for i, (new_line, old_line) in enumerate(zip(new_lines, old_lines)):
            if new_line != old_line:
                changed_lines.append(i)
        
        # Add new lines
        if len(new_lines) > len(old_lines):
            changed_lines.extend(range(len(old_lines), len(new_lines)))
        
        return ast, changed_lines
    
    def invalidate_lines(self, source: str, line_numbers: List[int]) -> None:
        """Invalidate specific lines in cache"""
        source_hash = self._hash_source(source)
        if source_hash in self.memory_cache:
            # Mark lines as changed (simplified)
            self.invalidate(source)

# Global cache instance
_global_cache = ASTCache()
_global_incremental_cache = IncrementalASTCache()

def get_ast(source: str) -> Optional[Any]:
    """Get AST from global cache"""
    return _global_cache.get(source)

def cache_ast(source: str, ast: Any, metadata: Optional[Dict] = None) -> None:
    """Cache AST in global cache"""
    _global_cache.put(source, ast, metadata)

def get_cache_stats() -> Dict[str, Any]:
    """Get global cache statistics"""
    return _global_cache.stats()

def clear_cache() -> None:
    """Clear global cache"""
    _global_cache.clear()
    _global_incremental_cache.clear()

# Example usage
if __name__ == "__main__":
    cache = ASTCache(max_entries=1000)
    
    # Simulate caching
    source1 = "let x = 42;\nlet y = x + 1;"
    source2 = "fn add(a, b) { return a + b; }"
    
    # Simulate AST objects (simplified)
    ast1 = {"type": "program", "statements": [{"type": "var_decl"}]}
    ast2 = {"type": "program", "statements": [{"type": "fn_def"}]}
    
    # Cache entries
    cache.put(source1, ast1, {"lines": 2, "complexity": "low"})
    cache.put(source2, ast2, {"lines": 1, "complexity": "medium"})
    
    # Retrieve
    print("Retrieved AST1:", cache.get(source1))
    print("Retrieved AST2:", cache.get(source2))
    print("Cache miss:", cache.get("let z = 100;"))
    
    # Show statistics
    cache.print_stats()
