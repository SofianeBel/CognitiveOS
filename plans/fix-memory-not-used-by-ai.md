# Fix: L'IA n'utilise pas la mémoire qu'elle crée

## Overview

Le système CognitiveOS stocke correctement les entités et relations en mémoire, mais **ne les récupère jamais** lors des conversations suivantes. L'utilisateur a l'impression que l'IA "oublie tout" alors que les données sont bien présentes.

**Cause racine identifiée** : Le seuil de similarité (`SIMILARITY_THRESHOLD=0.7`) est trop élevé pour le modèle d'embedding utilisé (`all-MiniLM-L6-v2`), qui produit des scores de similarité entre 0.3 et 0.55 pour du contenu pertinent.

## Problem Statement

```
User: "J'aime Python"
  -> Stocké: Node(Python, Skill) + Edge(User LIKES Python)
  -> Embedding généré: OK

User: "Qu'est-ce que j'aime ?"
  -> Query embedding: OK
  -> Similarité avec "Python": 0.52
  -> Seuil actuel: 0.70
  -> Résultat: 0.52 < 0.70 -> AUCUN CONTEXTE RÉCUPÉRÉ
  -> Réponse: "Je ne sais pas ce que vous aimez"
```

## Root Cause Analysis

### Issue 1: SIMILARITY_THRESHOLD trop élevé (CRITIQUE)

**Fichier**: `src/config.py:56`

Actuel:
```python
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))
```

Scores réels observés pour des requêtes pertinentes:
- "What does the user like?" vers "User" node: 0.508
- "Tell me about food preferences" vers best match: 0.389
- "User LIKES MacDo" edge: 0.464

**Impact**: 100% des requêtes échouent à récupérer du contexte.

### Issue 2: Les embeddings des edges ne sont pas recherchés

**Fichier**: `src/memory/graph.py:367-380`

Seuls les nodes sont recherchés actuellement. Les edges ont des embeddings mais ne sont jamais recherchés directement. Edge "User LIKES MacDo" a un score de 0.464 pour "What does the user like?" mais n'est jamais trouvé.

**Impact**: Les relations (LIKES, KNOWS, WORKS_AT) sont sous-utilisées.

### Issue 3: Le prompt n'est pas assez explicite

**Fichier**: `src/graph_loop.py:99-107`

Le prompt actuel est trop permissif ("use this context to personalize"). Le LLM peut ignorer le contexte car l'instruction est vague.

**Impact**: Même quand le contexte est récupéré, le LLM peut l'ignorer.

### Issue 4: Aucune visibilité sur la récupération

**Impact**: Impossible de diagnostiquer pourquoi la mémoire n'est pas utilisée.

## Proposed Solution

### Phase 1: Fix critique du seuil (30 min)

#### 1.1 Modifier src/config.py

```python
# Avant
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))

# Après
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.4"))
```

#### 1.2 Alternative: Modifier .env

```bash
SIMILARITY_THRESHOLD=0.4
```

### Phase 2: Améliorer le prompt (30 min)

**Fichier**: `src/graph_loop.py:89-121`

```python
def _generate_response(self, state: ConversationState) -> dict:
    user_input = state["user_input"]
    context = state["context"]

    memory_count = context.count("\n- ") if context != "No relevant memories found." else 0

    system_content = f"""You are a helpful assistant with access to a personal knowledge graph.

======================================================
RELEVANT MEMORIES (Retrieved: {memory_count} items)
======================================================
{context}
======================================================

IMPORTANT INSTRUCTIONS:
1. You MUST use the memories above when they are relevant to the user's question
2. Reference specific facts naturally without saying "I remember"
3. If memories contradict general knowledge, trust the memories (they are personalized)
4. If no relevant memories exist, provide general helpful assistance

Now respond to the user's query:"""

    system_message = SystemMessage(content=system_content)
    human_message = HumanMessage(content=user_input)
    response = self.llm.invoke([system_message, human_message])

    return {"messages": [HumanMessage(content=user_input), response]}
```

### Phase 3: Ajouter la recherche des edges (2h)

**Fichier**: `src/memory/graph.py` - Modifier get_context()

Ajouter une boucle pour rechercher aussi dans les edges:

```python
# 1. Rechercher dans les nodes (existant)
scored_nodes = []
for node in self.nodes_data.values():
    if node.embedding:
        score = embedding_service.similarity(query_embedding, np.array(node.embedding))
        if score >= threshold:
            scored_nodes.append((node, score, "node"))

# 2. NOUVEAU: Rechercher dans les edges
scored_edges = []
for edge in self.edges_data.values():
    if edge.embedding:
        score = embedding_service.similarity(query_embedding, np.array(edge.embedding))
        if score >= threshold:
            scored_edges.append((edge, score, "edge"))

# 3. Combiner et trier par score
all_results = scored_nodes + scored_edges
all_results.sort(key=lambda x: x[1], reverse=True)
```

### Phase 4: Ajouter des diagnostics (1h)

Ajouter du logging dans `src/memory/graph.py`:

```python
import logging
logger = logging.getLogger(__name__)

# Dans get_context():
if scored_nodes or scored_edges:
    logger.info(f"Query: '{query[:50]}...'")
    logger.info(f"Threshold: {threshold}, Results: {len(all_results)}")
    for item, score, _ in all_results[:5]:
        name = item.name if hasattr(item, 'name') else f"{item.source}->{item.target}"
        logger.info(f"  {score:.3f} - {name}")
else:
    logger.warning(f"No results above threshold {threshold} for: '{query[:50]}'")
```

Ajouter mode debug dans `src/graph_loop.py`:

```python
import os

class CognitiveLoop:
    def __init__(self, memory_path=None):
        self.debug_mode = os.getenv("DEBUG_MEMORY", "false").lower() == "true"

    def _retrieve_context(self, state):
        user_input = state["user_input"]
        context_items = self.memory.get_context(user_input)
        formatted_context = self.memory.format_context_for_llm(context_items)

        if self.debug_mode:
            print(f"\n[DEBUG] Query: {user_input}")
            print(f"[DEBUG] Retrieved {len(context_items)} items")
            for item in context_items:
                print(f"[DEBUG]   - {item['entity']}: {item.get('relevance', 'N/A'):.3f}")

        return {"context": formatted_context}
```

## Acceptance Criteria

### Issue 1: Seuil de similarité
- [ ] L'utilisateur stocke "J'aime Python"
- [ ] L'utilisateur demande plus tard "Qu'est-ce que j'aime ?"
- [ ] La réponse mentionne "Python"
- [ ] Les logs montrent le score de similarité et le seuil

### Issue 2: Recherche des edges
- [ ] Les embeddings des edges sont recherchés dans get_context()
- [ ] La requête "Qui est-ce que je connais ?" récupère les relations KNOWS
- [ ] Les résultats top-K incluent un mix de nodes et edges

### Issue 3: Utilisation du contexte
- [ ] Le prompt LLM inclut une instruction explicite d'utiliser le contexte
- [ ] Test manuel: 10 requêtes avec contexte, 9+ l'utilisent dans la réponse

### Issue 4: Observabilité
- [ ] DEBUG_MEMORY=true affiche les items récupérés et leurs scores
- [ ] Les logs incluent: query, résultats, scores, seuil
- [ ] Documentation mise à jour

### Général
- [ ] Tests existants passent (pytest tests/ -v)
- [ ] Nouveaux tests d'intégration ajoutés
- [ ] CHANGELOG.md mis à jour
- [ ] CLAUDE.md mis à jour avec les nouveaux paramètres par défaut

## Files to Modify

| Fichier | Changement | Priorité |
|---------|------------|----------|
| src/config.py:56 | Changer default threshold de 0.7 à 0.4 | CRITIQUE |
| .env | Ajouter SIMILARITY_THRESHOLD=0.4 | CRITIQUE |
| src/graph_loop.py:89-121 | Renforcer le prompt système | HAUTE |
| src/memory/graph.py:340-394 | Ajouter recherche des edges | MOYENNE |
| src/memory/graph.py | Ajouter logging de diagnostic | MOYENNE |
| src/graph_loop.py | Ajouter mode DEBUG_MEMORY | MOYENNE |
| CLAUDE.md | Documenter les nouveaux paramètres | BASSE |
| CHANGELOG.md | Documenter le fix | BASSE |

## Test Plan

### Test 1: Vérification du seuil

```python
def test_threshold_allows_retrieval():
    memory = MemoryGraph()
    memory.add_node(Node(name="Python", label="Skill", description="Programming language"))
    memory.add_edge(Edge(source="User", target="Python", relation="LIKES"))
    memory.save()

    context = memory.get_context("What programming languages do I like?")

    assert len(context) > 0, "No context retrieved!"
    assert any("Python" in str(item) for item in context)
```

### Test 2: Vérification de l'utilisation du contexte

```python
def test_llm_uses_context():
    loop = CognitiveLoop()
    loop.memory.add_node(Node(name="Bob", label="Person", description="User's brother who is a doctor"))
    loop.memory.save()

    response = loop.chat("What does Bob do for work?")

    assert "doctor" in response.lower()
```

### Test 3: Recherche des edges

```python
def test_edge_search():
    memory = MemoryGraph()
    memory.add_node(Node(name="User", label="Person"))
    memory.add_node(Node(name="Alice", label="Person"))
    memory.add_edge(Edge(source="User", target="Alice", relation="KNOWS", description="Best friend"))
    memory.save()

    context = memory.get_context("Who do I know?")

    assert any("KNOWS" in str(item) or "Alice" in str(item) for item in context)
```

## Implementation Order

1. **Immédiat (30 min)**: Changer SIMILARITY_THRESHOLD de 0.7 à 0.4
2. **Immédiat (30 min)**: Renforcer le prompt dans _generate_response
3. **Court terme (1h)**: Ajouter logging de diagnostic
4. **Court terme (2h)**: Implémenter la recherche des edges
5. **Moyen terme**: Ajouter tests d'intégration
6. **Moyen terme**: Mettre à jour documentation

## Success Metrics

- **Avant fix**: 0% des requêtes récupèrent du contexte pertinent
- **Après fix**: >80% des requêtes sémantiquement liées récupèrent du contexte
- **Mesure**: Logs de get_context() montrant les scores et résultats

## References

### Internal
- src/config.py:56 - Configuration du seuil
- src/memory/graph.py:340-394 - Logique de récupération
- src/graph_loop.py:89-121 - Génération de réponse avec contexte
- src/memory/embeddings.py - Service d'embedding (all-MiniLM-L6-v2)

### External
- Anthropic Contextual Retrieval: https://www.anthropic.com/news/contextual-retrieval
- LangGraph Memory Concepts: https://github.com/langchain-ai/langgraph/blob/main/docs/docs/concepts/persistence.md
- sentence-transformers all-MiniLM-L6-v2: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2

---

Généré le: 2025-12-08
Auteur: Claude Code
Version: 1.0
