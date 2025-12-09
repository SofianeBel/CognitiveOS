# Fix: L'IA ne retrouve pas le nom de l'utilisateur

## Analyse du Probleme

### Symptome
L'utilisateur dit "je m'appelle Sofiane", puis demande "je m'appelle comment?" et l'IA ne se souvient pas du nom.

### Diagnostic

**1. Le nom EST stocke dans la memoire** (verifie)
```
- Sofiane (label: "Name", description: "Your name")
- Sofiane (label: "Person", description: "User")
```

**2. AUCUNE relation vers User** (probleme principal)
Les noeuds "Sofiane" ne sont lies a rien. Pas de edge `User HAS_NAME Sofiane`.

**3. Similarite semantique faible**
- Query: "je m'appelle comment?"
- Node: "Sofiane" (juste un nom propre)
- Score attendu: ~0.25-0.35 (sous le seuil de 0.4)

### Cause Racine

Le prompt d'extraction (`src/agents/extractor.py`) n'a pas de type de relation pour le nom personnel:
- Types actuels: KNOWS, LIKES, WORKS_AT, LIVES_IN, OWNS, LEARNED...
- Manquant: **HAS_NAME, IS_CALLED, NAMED**

Quand l'utilisateur dit "je m'appelle Sofiane", GPT-4o extrait:
- Entity: Sofiane (Person ou Name)
- Mais pas de relation car "HAS_NAME" n'existe pas dans la liste

## Solution Proposee

### Phase 1: Ajouter le type de relation HAS_NAME

**Fichier: `src/agents/extractor.py`**

```python
# Ajouter dans la section ## Relation Types (ligne ~40)
- HAS_NAME: Personal name (e.g., "I'm called John" -> User HAS_NAME John)
- IS_CALLED: Alternative name or nickname
```

### Phase 2: Ajouter des exemples en francais dans le prompt

```python
## Example Input (Personal info in French)
"Je m'appelle Marie et j'habite a Paris"

## Example Output
{{
  "entities": [
    {{"label": "Person", "name": "User", "description": "The user of this system"}},
    {{"label": "Person", "name": "Marie", "description": "User's name"}},
    {{"label": "Location", "name": "Paris", "description": "City in France"}}
  ],
  "relations": [
    {{"source": "User", "target": "Marie", "relation": "HAS_NAME", "description": "User's given name"}},
    {{"source": "User", "target": "Paris", "relation": "LIVES_IN", "description": "Current residence"}}
  ]
}}
```

### Phase 3: Ameliorer l'embedding du noeud nom

**Fichier: `src/memory/graph.py`** - Modifier `add_node()`:

Pour les noeuds de type "Person" lies a "User", enrichir l'embedding:
```python
# Au lieu de juste "Sofiane"
# Utiliser "Sofiane: User's personal name, the user is called Sofiane"
```

### Phase 4: Requete contextuelle intelligente

**Fichier: `src/memory/graph.py`** - Modifier `get_context()`:

Detecter les requetes sur l'identite personnelle:
```python
identity_patterns = ["je m'appelle", "mon nom", "qui suis-je", "comment je m'appelle"]
if any(p in query.lower() for p in identity_patterns):
    # Rechercher specifiquement les relations HAS_NAME de User
    user_node = self.find_node_by_name("User")
    if user_node:
        for edge in self.get_outgoing_edges(user_node.id):
            if edge.relation == "HAS_NAME":
                # Ajouter ce contexte en priorite
```

## Implementation

### Fichiers a modifier

| Fichier | Modification |
|---------|--------------|
| `src/agents/extractor.py` | Ajouter HAS_NAME, exemples francais |
| `src/memory/graph.py` | Ameliorer embedding des noms, detection identite |
| `src/memory/models.py` | Ajouter RelationType enum si necessaire |
| `tests/test_extraction.py` | Nouveau test pour extraction de nom |

### Tests

1. **Test extraction nom**: "je m'appelle Sofiane" -> doit extraire relation HAS_NAME
2. **Test retrieval nom**: query "comment je m'appelle?" -> doit retourner Sofiane
3. **Test multilingue**: "My name is John" -> meme resultat attendu

### Risques

- **Changement de prompt**: Peut affecter autres extractions
- **Migration**: Memoire existante sans HAS_NAME restera incomplete

### Migration des donnees existantes (optionnel)

Script pour lier les noeuds "Sofiane" existants au noeud "User":
```python
# Script: scripts/migrate_names.py
for node in graph.nodes_data.values():
    if node.label in ["Name", "Person"] and node.name != "User":
        if node.description and "name" in node.description.lower():
            # Creer edge User -> node avec relation HAS_NAME
            edge = Edge(
                source=user_node.id,
                target=node.id,
                relation="HAS_NAME",
                description=f"User's personal name is {node.name}"
            )
            graph.add_edge(edge)
```

## Priorite

1. **Haute**: Ajouter HAS_NAME au prompt d'extraction
2. **Moyenne**: Ajouter exemples francais
3. **Basse**: Detection intelligente des requetes identite
4. **Optionnelle**: Migration donnees existantes

## Metriques de succes

- [ ] "je m'appelle Sofiane" cree une relation `User HAS_NAME Sofiane`
- [ ] "comment je m'appelle?" retourne "Sofiane" dans le contexte
- [ ] Score de similarite > 0.4 pour les requetes d'identite
