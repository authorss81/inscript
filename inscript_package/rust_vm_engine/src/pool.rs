// inscript_vm_engine/src/pool.rs
// Object Pooling — InScript v3.8.4 Optimization
//
// Purpose: Reuse heap allocations for Vec and HashMap instead of
// allocating/dropping them every time CreateArray / CreateObject fires.
// Common small values (Int 0..=255, Bool, Nil) are interned once and
// shared forever — no allocation on repeated pushes.
//
// Expected speedup: 2-3x for collection-heavy workloads,
// ~1.5x for general code (reduced GC pressure).

use std::sync::Arc;
use std::collections::HashMap;
use parking_lot::Mutex;
use crate::Value;

// ─────────────────────────────────────────────────────────────────────────────
// Interned (shared) constants — created once, cloned O(1) everywhere
// ─────────────────────────────────────────────────────────────────────────────

/// Interned nil singleton
static INTERNED_NIL: std::sync::OnceLock<Arc<Value>> = std::sync::OnceLock::new();

/// Interned bool singletons
static INTERNED_TRUE:  std::sync::OnceLock<Arc<Value>> = std::sync::OnceLock::new();
static INTERNED_FALSE: std::sync::OnceLock<Arc<Value>> = std::sync::OnceLock::new();

/// Interned small integers (-1 to 255)
/// Index = value + 1 (so -1 maps to index 0, 0 to 1, …, 255 to 256)
static INTERNED_INTS: std::sync::OnceLock<Vec<Arc<Value>>> = std::sync::OnceLock::new();

/// Interned empty string
static INTERNED_EMPTY_STR: std::sync::OnceLock<Arc<Value>> = std::sync::OnceLock::new();

const INTERNED_INT_MIN: i64 = -1;
const INTERNED_INT_MAX: i64 = 255;

/// One-time initialiser — call from VMEngine::new() or lazily.
pub fn init_interns() {
    INTERNED_NIL.get_or_init(|| Arc::new(Value::Nil));
    INTERNED_TRUE.get_or_init(|| Arc::new(Value::Bool(true)));
    INTERNED_FALSE.get_or_init(|| Arc::new(Value::Bool(false)));
    INTERNED_EMPTY_STR.get_or_init(|| Arc::new(Value::String(String::new())));
    INTERNED_INTS.get_or_init(|| {
        (INTERNED_INT_MIN..=INTERNED_INT_MAX)
            .map(|i| Arc::new(Value::Int(i)))
            .collect()
    });
}

/// Retrieve an interned Arc<Value> for a nil.
#[inline(always)]
pub fn intern_nil() -> Arc<Value> {
    Arc::clone(INTERNED_NIL.get_or_init(|| Arc::new(Value::Nil)))
}

/// Retrieve an interned Arc<Value> for a bool.
#[inline(always)]
pub fn intern_bool(b: bool) -> Arc<Value> {
    if b {
        Arc::clone(INTERNED_TRUE.get_or_init(|| Arc::new(Value::Bool(true))))
    } else {
        Arc::clone(INTERNED_FALSE.get_or_init(|| Arc::new(Value::Bool(false))))
    }
}

/// Retrieve an interned Arc<Value> for an integer if it falls in the
/// cached range, otherwise heap-allocate a fresh one.
#[inline(always)]
pub fn intern_int(n: i64) -> Arc<Value> {
    if n >= INTERNED_INT_MIN && n <= INTERNED_INT_MAX {
        let ints = INTERNED_INTS.get_or_init(|| {
            (INTERNED_INT_MIN..=INTERNED_INT_MAX)
                .map(|i| Arc::new(Value::Int(i)))
                .collect()
        });
        Arc::clone(&ints[(n - INTERNED_INT_MIN) as usize])
    } else {
        Arc::new(Value::Int(n))
    }
}

/// Retrieve an interned empty string or heap-allocate a new string.
#[inline(always)]
pub fn intern_string(s: String) -> Arc<Value> {
    if s.is_empty() {
        Arc::clone(INTERNED_EMPTY_STR.get_or_init(|| Arc::new(Value::String(String::new()))))
    } else {
        Arc::new(Value::String(s))
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// ArrayPool — recycles Vec<Arc<Value>> allocations
// ─────────────────────────────────────────────────────────────────────────────

const ARRAY_POOL_CAPACITY: usize = 64;   // max vecs held in pool
const ARRAY_VEC_MAX_REUSE: usize = 4096; // don't keep giant vecs

/// Pool of recycled Vec<Arc<Value>> buffers.
pub struct ArrayPool {
    pool: Mutex<Vec<Vec<Arc<Value>>>>,
    // stats
    pub recycles: std::sync::atomic::AtomicUsize,
    pub misses:   std::sync::atomic::AtomicUsize,
}

impl ArrayPool {
    pub fn new() -> Self {
        ArrayPool {
            pool: Mutex::new(Vec::with_capacity(ARRAY_POOL_CAPACITY)),
            recycles: std::sync::atomic::AtomicUsize::new(0),
            misses:   std::sync::atomic::AtomicUsize::new(0),
        }
    }

    /// Get a cleared, reusable Vec (or allocate a fresh one).
    #[inline]
    pub fn acquire(&self, hint_capacity: usize) -> Vec<Arc<Value>> {
        let mut pool = self.pool.lock();
        if let Some(mut v) = pool.pop() {
            v.clear();
            if v.capacity() < hint_capacity {
                v.reserve(hint_capacity - v.capacity());
            }
            self.recycles.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
            v
        } else {
            self.misses.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
            Vec::with_capacity(hint_capacity.max(8))
        }
    }

    /// Return a Vec back to the pool. Drops if pool is full or vec is huge.
    #[inline]
    pub fn release(&self, mut v: Vec<Arc<Value>>) {
        if v.capacity() > ARRAY_VEC_MAX_REUSE {
            return; // let huge vecs drop naturally
        }
        v.clear();
        let mut pool = self.pool.lock();
        if pool.len() < ARRAY_POOL_CAPACITY {
            pool.push(v);
        }
        // otherwise drop v
    }

    pub fn stats(&self) -> (usize, usize) {
        (
            self.recycles.load(std::sync::atomic::Ordering::Relaxed),
            self.misses.load(std::sync::atomic::Ordering::Relaxed),
        )
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// ObjectPool — recycles HashMap<String, Arc<Value>> allocations
// ─────────────────────────────────────────────────────────────────────────────

const OBJECT_POOL_CAPACITY: usize = 32;
const OBJECT_MAP_MAX_REUSE: usize = 256; // don't keep huge maps

/// Pool of recycled HashMap<String, Arc<Value>> buffers.
pub struct ObjectPool {
    pool: Mutex<Vec<HashMap<String, Arc<Value>>>>,
    pub recycles: std::sync::atomic::AtomicUsize,
    pub misses:   std::sync::atomic::AtomicUsize,
}

impl ObjectPool {
    pub fn new() -> Self {
        ObjectPool {
            pool: Mutex::new(Vec::with_capacity(OBJECT_POOL_CAPACITY)),
            recycles: std::sync::atomic::AtomicUsize::new(0),
            misses:   std::sync::atomic::AtomicUsize::new(0),
        }
    }

    /// Get a cleared, reusable HashMap.
    #[inline]
    pub fn acquire(&self) -> HashMap<String, Arc<Value>> {
        let mut pool = self.pool.lock();
        if let Some(mut m) = pool.pop() {
            m.clear();
            self.recycles.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
            m
        } else {
            self.misses.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
            HashMap::with_capacity(8)
        }
    }

    /// Return a HashMap back to the pool.
    #[inline]
    pub fn release(&self, mut m: HashMap<String, Arc<Value>>) {
        if m.capacity() > OBJECT_MAP_MAX_REUSE {
            return;
        }
        m.clear();
        let mut pool = self.pool.lock();
        if pool.len() < OBJECT_POOL_CAPACITY {
            pool.push(m);
        }
    }

    pub fn stats(&self) -> (usize, usize) {
        (
            self.recycles.load(std::sync::atomic::Ordering::Relaxed),
            self.misses.load(std::sync::atomic::Ordering::Relaxed),
        )
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Combined pool stats for VMStats
// ─────────────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub struct PoolStats {
    pub array_recycles: usize,
    pub array_misses:   usize,
    pub object_recycles: usize,
    pub object_misses:   usize,
}

impl PoolStats {
    pub fn array_hit_rate(&self) -> f64 {
        let total = self.array_recycles + self.array_misses;
        if total == 0 { 0.0 } else { self.array_recycles as f64 / total as f64 }
    }
    pub fn object_hit_rate(&self) -> f64 {
        let total = self.object_recycles + self.object_misses;
        if total == 0 { 0.0 } else { self.object_recycles as f64 / total as f64 }
    }
}
