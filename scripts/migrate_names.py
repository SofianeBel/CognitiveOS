"""Migration script to add HAS_NAME relationships for existing name nodes.

This script finds nodes that appear to be user names (based on their description
or label) and creates HAS_NAME edges linking them to the User node.

Usage:
    python -m scripts.migrate_names [--dry-run]

Options:
    --dry-run    Preview changes without modifying the database
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.memory.graph import MemoryGraph
from src.memory.models import Edge
from src.config import settings


def find_user_node(graph: MemoryGraph):
    """Find the User node in the graph."""
    for node in graph.nodes_data.values():
        if node.name == "User" and node.label == "Person":
            return node
    return None


def find_name_nodes(graph: MemoryGraph, user_node_id: str):
    """Find nodes that look like user names but aren't linked to User."""
    name_indicators = [
        "name", "nom", "appelle", "called", "prenom", "given name",
        "personal name", "user's name"
    ]

    name_nodes = []

    for node in graph.nodes_data.values():
        # Skip User node itself
        if node.id == user_node_id:
            continue

        # Skip nodes already linked to User with HAS_NAME
        already_linked = False
        for edge in graph.edges_data.values():
            if (edge.source == user_node_id and
                edge.target == node.id and
                edge.relation == "HAS_NAME"):
                already_linked = True
                break

        if already_linked:
            continue

        # Check if this looks like a name node
        is_name_node = False

        # Check description for name indicators
        if node.description:
            desc_lower = node.description.lower()
            if any(indicator in desc_lower for indicator in name_indicators):
                is_name_node = True

        # Check if label is "Name"
        if node.label == "Name":
            is_name_node = True

        # Check if label is "Person" and description mentions user
        if node.label == "Person" and node.description:
            if "user" in node.description.lower():
                is_name_node = True

        if is_name_node:
            name_nodes.append(node)

    return name_nodes


def migrate_names(dry_run: bool = False):
    """Run the migration to add HAS_NAME relationships."""
    config = settings()
    print(f"Loading memory graph from: {config.memory_file}")

    graph = MemoryGraph()

    # Find User node
    user_node = find_user_node(graph)
    if not user_node:
        print("ERROR: No User node found in graph!")
        print("Please ensure the graph has a User node before running migration.")
        return 1

    print(f"Found User node: {user_node.id}")

    # Find potential name nodes
    name_nodes = find_name_nodes(graph, user_node.id)

    if not name_nodes:
        print("\nNo unlinked name nodes found. Nothing to migrate.")
        return 0

    print(f"\nFound {len(name_nodes)} potential name node(s) to link:\n")

    for i, node in enumerate(name_nodes, 1):
        print(f"  {i}. {node.name} (label: {node.label})")
        if node.description:
            print(f"     Description: {node.description}")
        print()

    if dry_run:
        print("\n[DRY RUN] Would create the following edges:")
        for node in name_nodes:
            print(f"  User --HAS_NAME--> {node.name}")
        print("\nRun without --dry-run to apply changes.")
        return 0

    # Create HAS_NAME edges
    print("\nCreating HAS_NAME relationships...")
    created_count = 0

    for node in name_nodes:
        edge = Edge(
            source=user_node.id,
            target=node.id,
            relation="HAS_NAME",
            description=f"User's personal name is {node.name}"
        )

        try:
            graph.add_edge(edge)
            print(f"  Created: User --HAS_NAME--> {node.name}")
            created_count += 1
        except Exception as e:
            print(f"  ERROR creating edge for {node.name}: {e}")

    # Save changes
    graph.save()
    print(f"\nMigration complete! Created {created_count} HAS_NAME relationship(s).")

    return 0


def main():
    """Main entry point."""
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("=== DRY RUN MODE ===\n")

    try:
        return migrate_names(dry_run=dry_run)
    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
