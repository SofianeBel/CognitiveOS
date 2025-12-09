"""Script to enrich name nodes with better descriptions for improved retrieval.

When a node is linked to User via HAS_NAME, this script updates its description
to include name-related keywords in multiple languages, improving semantic
similarity scores for name queries.

Usage:
    python -m scripts.enrich_name_nodes [--dry-run]
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.memory.graph import MemoryGraph
from src.memory.embeddings import embedding_service
from src.config import settings


def enrich_name_nodes(dry_run: bool = False):
    """Enrich name nodes with better descriptions."""
    print("Loading memory graph...")
    graph = MemoryGraph()

    # Find User node
    user_node = None
    for node in graph.nodes_data.values():
        if node.name == "User" and node.label == "Person":
            user_node = node
            break

    if not user_node:
        print("ERROR: No User node found!")
        return 1

    # Find all HAS_NAME edges from User
    name_edges = []
    for edge in graph.edges_data.values():
        if edge.source == user_node.id and edge.relation == "HAS_NAME":
            name_edges.append(edge)

    if not name_edges:
        print("No HAS_NAME relationships found. Run migrate_names.py first.")
        return 1

    print(f"Found {len(name_edges)} HAS_NAME relationship(s)")

    # Enrich each name node
    changes = []
    for edge in name_edges:
        target_node = graph.nodes_data.get(edge.target)
        if not target_node:
            continue

        name = target_node.name

        # Create enriched description with multilingual keywords
        new_description = (
            f"User's personal name is {name}. "
            f"Je m'appelle {name}. My name is {name}. "
            f"The user is called {name}. Comment je m'appelle: {name}. "
            f"Quel est mon nom: {name}."
        )

        if target_node.description != new_description:
            changes.append({
                'node_id': target_node.id,
                'name': name,
                'old_desc': target_node.description,
                'new_desc': new_description
            })

    if not changes:
        print("\nAll name nodes already have enriched descriptions.")
        return 0

    print(f"\nWill update {len(changes)} node(s):\n")
    for change in changes:
        print(f"  {change['name']}:")
        print(f"    Old: {change['old_desc']}")
        print(f"    New: {change['new_desc'][:80]}...")
        print()

    if dry_run:
        print("[DRY RUN] No changes made.")
        return 0

    # Apply changes
    print("Applying changes...")
    for change in changes:
        node = graph.nodes_data[change['node_id']]
        node.description = change['new_desc']

        # Regenerate embedding with new description
        text = f"{node.name}: {node.description}"
        node.embedding = embedding_service.embed(text).tolist()
        print(f"  Updated {node.name} with new embedding")

    # Also update the edge descriptions and embeddings
    print("\nUpdating HAS_NAME edges...")
    for edge in name_edges:
        target_node = graph.nodes_data.get(edge.target)
        if target_node:
            # Enrich edge description
            edge.description = (
                f"User's personal name is {target_node.name}. "
                f"Je m'appelle {target_node.name}. "
                f"Comment je m'appelle: {target_node.name}."
            )

            # Regenerate edge embedding
            source_name = user_node.name
            target_name = target_node.name
            text = f"{source_name} {edge.relation} {target_name}: {edge.description}"
            edge.embedding = embedding_service.embed(text).tolist()
            print(f"  Updated edge: User --HAS_NAME--> {target_name}")

    graph.save()
    print(f"\nDone! Updated {len(changes)} node(s) and {len(name_edges)} edge(s).")

    return 0


def main():
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("=== DRY RUN MODE ===\n")

    try:
        return enrich_name_nodes(dry_run=dry_run)
    except Exception as e:
        print(f"Failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
