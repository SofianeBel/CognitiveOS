# Fix: Relations entre User et entités non créées

## Problème

Quand l'utilisateur dit "j'aime les frites du macdo":
- ✅ Le node "frites" est créé
- ✅ Le node "macdo" est créé
- ❌ Le lien User → frites (LIKES) n'est PAS créé
- ❌ Le lien frites → macdo (HAS_PROPERTY ou RELATED_TO) n'est PAS créé

**Cela fonctionnait en Phase 2 mais ne fonctionne plus.**

## Analyse de la cause racine

### Le flux d'extraction (extractor.py:136-183)

```python
def extract(self, user_message: str) -> ExtractionResult:
    result = self.chain.invoke({"user_message": user_message})

    # 1. Convertir les entités extraites en nodes
    entities = []
    for entity_data in result.entities:
        entities.append(Node(
            label=entity_data.label,
            name=entity_data.name,
            description=entity_data.description
        ))

    # 2. Créer le mapping name -> id
    name_to_id = {e.name: e.id for e in entities}

    # 3. Convertir les relations en edges
    for rel_data in result.relations:
        source_name = rel_data.source  # Ex: "User"
        target_name = rel_data.target  # Ex: "frites"

        source_id = name_to_id.get(source_name)  # ❌ PROBLÈME ICI
        target_id = name_to_id.get(target_name)

        if source_id and target_id:
            # Ajouter l'edge
        else:
            logger.warning(f"Skipping relation: {source_name} -> {target_name} (missing entity)")
```

### Le bug identifié

**Ligne 169-183**: Le code vérifie si `source_name` et `target_name` existent dans `name_to_id`.

Le LLM peut retourner:
```json
{
  "entities": [
    {"label": "Preference", "name": "frites", "description": "..."},
    {"label": "Organization", "name": "macdo", "description": "..."}
  ],
  "relations": [
    {"source": "User", "target": "frites", "relation": "LIKES"}
  ]
}
```

**Problème**: Le LLM n'inclut PAS toujours "User" comme entité explicite, mais l'utilise quand même dans les relations. Résultat: `name_to_id.get("User")` retourne `None` → la relation est ignorée.

### Différence OpenAI vs Ollama

Ce n'est **PAS un problème de modèle** en soi, mais plutôt:

1. **GPT-4o** tend à TOUJOURS inclure "User" dans les entités quand il y a une relation
2. **Llama 3.2** peut omettre "User" car le prompt dit "The 'User' entity always exists"

Le LLM interprète cela comme "pas besoin de l'extraire, il existe déjà".

## Solution proposée

### Option A: Ajouter automatiquement User (Recommandé)

Dans `extractor.py`, toujours injecter l'entité "User" si elle n'existe pas mais est référencée dans une relation:

```python
def extract(self, user_message: str) -> ExtractionResult:
    result = self.chain.invoke({"user_message": user_message})

    entities = []
    for entity_data in result.entities:
        entities.append(Node(...))

    # Mapping initial
    name_to_id = {e.name: e.id for e in entities}

    # NOUVEAU: Collecter tous les noms utilisés dans les relations
    relation_names = set()
    for rel in result.relations:
        relation_names.add(rel.source)
        relation_names.add(rel.target)

    # NOUVEAU: Ajouter les entités manquantes (notamment "User")
    for name in relation_names:
        if name not in name_to_id:
            # Créer l'entité manquante
            if name == "User":
                node = Node(label="Person", name="User", description="The user of this system")
            else:
                node = Node(label="Concept", name=name, description=f"Entity referenced in relation")
            entities.append(node)
            name_to_id[name] = node.id
            logger.info(f"Auto-created missing entity: {name}")

    # Continuer avec la création des edges...
```

### Option B: Modifier le prompt pour être plus explicite

Modifier le prompt pour forcer l'inclusion de User:

```diff
## Rules
1. Only extract facts that are explicitly stated or strongly implied
-2. The "User" entity always exists - extract relationships TO the user
+2. ALWAYS include "User" as an entity when extracting relationships that involve the user
3. Use past tense for historical facts, present for current state
```

### Option C: Combiner A + B

La solution la plus robuste.

## Tests de validation

```bash
# Test avec OpenAI
LLM_PROVIDER=openai python -c "
from src.agents.extractor import ExtractionAgent
agent = ExtractionAgent()
result = agent.extract('j\\'aime les frites du macdo')
print('Entities:', [e.name for e in result.entities])
print('Relations:', [(r.source, r.relation, r.target) for r in result.relations])
"

# Test avec Ollama
LLM_PROVIDER=ollama python -c "..."
```

## Fichiers à modifier

| Fichier | Modification |
|---------|-------------|
| `src/agents/extractor.py` | Ajouter auto-création de User et entités manquantes (lignes 159-183) |
| `src/agents/extractor.py` | Optionnel: Clarifier le prompt (ligne 44) |

## Acceptance Criteria

- [ ] Quand on dit "j'aime les frites", le graphe contient:
  - Node: User (Person)
  - Node: frites (Preference ou Concept)
  - Edge: User --LIKES--> frites
- [ ] Fonctionne avec OpenAI ET Ollama
- [ ] Les logs indiquent si User a été auto-créé
- [ ] Tests unitaires ajoutés

## Priorité

**HAUTE** - Bug bloquant qui empêche la fonctionnalité principale de mémoire.
