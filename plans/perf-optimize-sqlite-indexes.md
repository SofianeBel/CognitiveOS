# perf: Optimiser les queries SQLite avec index appropriés

## Overview

Améliorer les performances des requêtes SQLite en ajoutant des index manquants et en optimisant les requêtes existantes pour atteindre l'objectif du PRD: **retrieval < 100ms pour 10K nœuds**.

## État actuel

### Index existants (`src/memory/database.py:147-152`)

```sql
CREATE INDEX IF NOT EXISTS idx_nodes_label ON nodes(label)
CREATE INDEX IF NOT EXISTS idx_nodes_name ON nodes(name)
CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id)
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id)
CREATE INDEX IF NOT EXISTS idx_edges_relation ON edges(relation)
```

### Index manquants identifiés

| Query Pattern | Fichier:Ligne | Index manquant |
|---------------|---------------|----------------|
| `WHERE LOWER(name) = LOWER(?)` | database.py:323 | Index fonctionnel sur `LOWER(name)` |
| `WHERE is_active = 1` | database.py:344, 519, 537 | Index sur `is_active` |
| `ORDER BY distance` | database.py:459 | Géré par sqlite-vec |
| `GROUP BY label` | database.py:563 | Couvert par idx_nodes_label |
| `WHERE e.source_id = ? AND e.is_active = 1` | database.py:519 | Index composite |
| `WHERE e.target_id = ? AND e.is_active = 1` | database.py:537 | Index composite |
| `last_accessed` pour pruning | consolidation | Index sur last_accessed |
| `importance_score` pour pruning | consolidation | Index sur importance_score |

## Acceptance Criteria

- [ ] Ajouter index sur `last_accessed` pour optimiser les requêtes de pruning
- [ ] Ajouter index sur `importance_score` pour les requêtes de consolidation
- [ ] Ajouter index composite `(source_id, is_active)` pour les requêtes de voisinage
- [ ] Ajouter index composite `(target_id, is_active)` pour les requêtes de voisinage
- [ ] Ajouter index sur `is_active` pour le filtrage des edges
- [ ] Créer un collation NOCASE pour les recherches case-insensitive sur `name`
- [ ] Ajouter `ANALYZE` après bulk inserts
- [ ] Benchmark avant/après avec 10K nœuds

## Implementation

### Nouveaux index à ajouter

```sql
-- Consolidation / Pruning optimization
CREATE INDEX IF NOT EXISTS idx_nodes_last_accessed ON nodes(last_accessed);
CREATE INDEX IF NOT EXISTS idx_nodes_importance ON nodes(importance_score);

-- Edge queries optimization
CREATE INDEX IF NOT EXISTS idx_edges_active ON edges(is_active);
CREATE INDEX IF NOT EXISTS idx_edges_source_active ON edges(source_id, is_active);
CREATE INDEX IF NOT EXISTS idx_edges_target_active ON edges(target_id, is_active);

-- Case-insensitive name search (utiliser COLLATE NOCASE à la création)
CREATE INDEX IF NOT EXISTS idx_nodes_name_nocase ON nodes(name COLLATE NOCASE);
```

### Modifications requises

#### 1. `src/memory/database.py:147-152`

Ajouter les nouveaux index après les existants:

```python
# Existing indexes
cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_label ON nodes(label)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_name ON nodes(name)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_relation ON edges(relation)")

# NEW: Consolidation/pruning optimization
cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_last_accessed ON nodes(last_accessed)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_importance ON nodes(importance_score)")

# NEW: Edge query optimization
cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_active ON edges(is_active)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_source_active ON edges(source_id, is_active)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_target_active ON edges(target_id, is_active)")

# NEW: Case-insensitive name search
cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_name_nocase ON nodes(name COLLATE NOCASE)")
```

#### 2. `src/memory/database.py:322-325` - Optimiser recherche par nom

```python
def get_node_by_name(self, name: str) -> Optional[Node]:
    """Get a node by name (case-insensitive)."""
    with self._get_connection() as conn:
        cursor = conn.cursor()
        # Utiliser COLLATE NOCASE pour profiter de l'index
        cursor.execute(
            "SELECT * FROM nodes WHERE name = ? COLLATE NOCASE",
            (name,)
        )
```

#### 3. Ajouter méthode `analyze()` pour statistiques

```python
def analyze(self) -> None:
    """Update query planner statistics after bulk operations."""
    with self._get_connection() as conn:
        conn.execute("ANALYZE")
        logger.debug("Database statistics updated")
```

#### 4. Appeler `analyze()` après migrations et consolidations

Dans `src/memory/migrate.py` et `src/consolidation/engine.py`:

```python
# Après bulk insert/delete
if hasattr(self.memory, '_sqlite_store') and self.memory._sqlite_store:
    self.memory._sqlite_store.analyze()
```

## Benchmark Script

```python
# tests/benchmark_queries.py
import time
from src.memory.database import SQLiteMemoryStore
from src.memory.models import Node

def benchmark(store: SQLiteMemoryStore, num_nodes: int = 10000):
    """Benchmark common queries."""

    # 1. Search similar (vector search)
    start = time.perf_counter()
    results = store.search_similar("test query", top_k=10)
    vec_time = (time.perf_counter() - start) * 1000

    # 2. Get neighbors
    if results:
        node_id = results[0][0].id
        start = time.perf_counter()
        neighbors = store.get_node_neighbors(node_id)
        neighbor_time = (time.perf_counter() - start) * 1000

    # 3. Get by name
    start = time.perf_counter()
    node = store.get_node_by_name("User")
    name_time = (time.perf_counter() - start) * 1000

    print(f"Vector search: {vec_time:.2f}ms")
    print(f"Get neighbors: {neighbor_time:.2f}ms")
    print(f"Get by name: {name_time:.2f}ms")
    print(f"Target: < 100ms")
```

## Success Metrics

| Metric | Target | Method |
|--------|--------|--------|
| Vector search (10K nodes) | < 50ms | sqlite-vec optimized |
| Get neighbors | < 10ms | Composite indexes |
| Get by name | < 5ms | COLLATE NOCASE index |
| Consolidation scan | < 100ms | last_accessed + importance indexes |

## Risques

- **Taille de la DB**: Les index ajoutent ~10-20% à la taille du fichier
- **Write performance**: Légère dégradation sur INSERT (~5-10%)
- **Migration**: Les index seront créés au prochain démarrage

## Références

- PRD Task 2.6: "Optimiser queries avec index appropriés"
- SQLite Index Documentation: https://www.sqlite.org/queryplanner.html
- sqlite-vec: https://github.com/asg017/sqlite-vec
