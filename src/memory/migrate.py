"""Migration tool to convert Phase 1 JSON memory to Phase 2 SQLite."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from src.memory.models import Node, Edge, NodeMetadata, EdgeMetadata, EdgeValidity
from src.memory.database import SQLiteMemoryStore
from src.config import settings

logger = logging.getLogger(__name__)


def migrate_json_to_sqlite(
    json_path: Optional[str] = None,
    db_path: Optional[str] = None,
    clear_existing: bool = False
) -> Dict[str, Any]:
    """
    Migrate Phase 1 JSON memory to Phase 2 SQLite.

    Args:
        json_path: Path to JSON memory file (defaults to settings)
        db_path: Path to SQLite database (defaults to settings)
        clear_existing: Whether to clear existing SQLite data before migration

    Returns:
        Migration summary with counts and any errors
    """
    json_path = json_path or settings().memory_file
    db_path = db_path or settings().database_path

    result = {
        'nodes_migrated': 0,
        'edges_migrated': 0,
        'nodes_skipped': 0,
        'edges_skipped': 0,
        'errors': [],
        'json_path': json_path,
        'db_path': db_path
    }

    # Check if JSON file exists
    json_file = Path(json_path)
    if not json_file.exists():
        result['errors'].append(f"JSON file not found: {json_path}")
        logger.error(f"Migration failed: JSON file not found at {json_path}")
        return result

    # Load JSON data
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded JSON memory from {json_path}")
    except json.JSONDecodeError as e:
        result['errors'].append(f"Invalid JSON: {e}")
        logger.error(f"Migration failed: Invalid JSON - {e}")
        return result

    # Initialize SQLite store
    store = SQLiteMemoryStore(db_path)

    if clear_existing:
        store.clear()
        logger.info("Cleared existing SQLite data")

    # Migrate nodes
    nodes_data = data.get('nodes', [])
    node_id_mapping = {}  # Track ID mappings for edges

    for node_data in nodes_data:
        try:
            # Parse node from JSON
            node = _parse_node(node_data)

            # Add to SQLite (check_duplicate=False to preserve exact data)
            store.add_node(node, check_duplicate=False)
            node_id_mapping[node.id] = node.id
            result['nodes_migrated'] += 1

        except Exception as e:
            result['nodes_skipped'] += 1
            result['errors'].append(f"Node error: {e}")
            logger.warning(f"Skipping node: {e}")

    logger.info(f"Migrated {result['nodes_migrated']} nodes")

    # Migrate edges
    edges_data = data.get('edges', [])

    for edge_data in edges_data:
        try:
            # Parse edge from JSON
            edge = _parse_edge(edge_data)

            # Add to SQLite
            store.add_edge(edge)
            result['edges_migrated'] += 1

        except Exception as e:
            result['edges_skipped'] += 1
            result['errors'].append(f"Edge error: {e}")
            logger.warning(f"Skipping edge: {e}")

    logger.info(f"Migrated {result['edges_migrated']} edges")

    # Validate migration
    stats = store.get_stats()
    result['validation'] = {
        'json_nodes': len(nodes_data),
        'json_edges': len(edges_data),
        'sqlite_nodes': stats['total_nodes'],
        'sqlite_edges': stats['total_edges'],
        'match': (
            stats['total_nodes'] == result['nodes_migrated'] and
            stats['total_edges'] == result['edges_migrated']
        )
    }

    store.close()

    logger.info(f"Migration complete: {result['nodes_migrated']} nodes, {result['edges_migrated']} edges")
    return result


def _parse_node(data: Dict[str, Any]) -> Node:
    """Parse a node from JSON data."""
    # Handle metadata
    metadata_data = data.get('metadata', {})
    metadata = NodeMetadata(
        created_at=_parse_datetime(metadata_data.get('created_at')),
        last_accessed=_parse_datetime(metadata_data.get('last_accessed')),
        access_count=metadata_data.get('access_count', 1),
        importance_score=metadata_data.get('importance_score', 0.5),
        confidence=metadata_data.get('confidence', 1.0),
        source=metadata_data.get('source', 'conversation')
    )

    return Node(
        id=data['id'],
        label=data['label'],
        name=data['name'],
        description=data.get('description'),
        embedding=data.get('embedding'),
        metadata=metadata
    )


def _parse_edge(data: Dict[str, Any]) -> Edge:
    """Parse an edge from JSON data."""
    # Handle metadata
    metadata_data = data.get('metadata', {})
    metadata = EdgeMetadata(
        created_at=_parse_datetime(metadata_data.get('created_at')),
        confidence=metadata_data.get('confidence', 1.0)
    )

    # Handle validity
    validity_data = data.get('validity', {})
    validity = EdgeValidity(
        start=validity_data.get('start'),
        end=validity_data.get('end')
    )

    return Edge(
        id=data['id'],
        source=data['source'],
        target=data['target'],
        relation=data['relation'],
        description=data.get('description'),
        embedding=data.get('embedding'),
        metadata=metadata,
        validity=validity
    )


def _parse_datetime(value: Any) -> datetime:
    """Parse datetime from various formats."""
    if value is None:
        return datetime.now()
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return datetime.now()
    return datetime.now()


def main():
    """CLI entry point for migration."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Migrate CognitiveOS memory from JSON to SQLite'
    )
    parser.add_argument(
        '--json',
        type=str,
        default=None,
        help='Path to JSON memory file (default: from settings)'
    )
    parser.add_argument(
        '--db',
        type=str,
        default=None,
        help='Path to SQLite database (default: from settings)'
    )
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear existing SQLite data before migration'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 50)
    print("CognitiveOS Memory Migration")
    print("=" * 50)
    print()

    result = migrate_json_to_sqlite(
        json_path=args.json,
        db_path=args.db,
        clear_existing=args.clear
    )

    print(f"Source: {result['json_path']}")
    print(f"Target: {result['db_path']}")
    print()
    print(f"Nodes migrated: {result['nodes_migrated']}")
    print(f"Edges migrated: {result['edges_migrated']}")
    print(f"Nodes skipped:  {result['nodes_skipped']}")
    print(f"Edges skipped:  {result['edges_skipped']}")
    print()

    if result.get('validation'):
        v = result['validation']
        print("Validation:")
        print(f"  JSON nodes: {v['json_nodes']}, SQLite nodes: {v['sqlite_nodes']}")
        print(f"  JSON edges: {v['json_edges']}, SQLite edges: {v['sqlite_edges']}")
        print(f"  Match: {'OK' if v['match'] else 'MISMATCH'}")

    if result['errors']:
        print()
        print(f"Errors ({len(result['errors'])}):")
        for error in result['errors'][:10]:
            print(f"  - {error}")
        if len(result['errors']) > 10:
            print(f"  ... and {len(result['errors']) - 10} more")

    print()
    print("=" * 50)


if __name__ == '__main__':
    main()
