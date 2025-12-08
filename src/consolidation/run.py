"""CLI entry point for memory consolidation.

Usage:
    python -m src.consolidation.run [OPTIONS]

Options:
    --dry-run           Preview changes without applying them
    --duplicate-threshold FLOAT  Similarity threshold for duplicates (default: 0.9)
    --prune-days INT    Days of inactivity for pruning (default: 30)
    --prune-importance FLOAT  Max importance to prune (default: 0.3)
    --show-candidates   Show duplicate and prune candidates then exit
    --verbose          Enable verbose logging
"""

import argparse
import logging
import sys
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.memory.graph import MemoryGraph
from src.consolidation.engine import ConsolidationEngine
from src.config import settings

console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the CLI."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def show_candidates(engine: ConsolidationEngine, args: argparse.Namespace) -> None:
    """Show duplicate and prune candidates without running consolidation."""
    console.print("\n[bold cyan]Duplicate Candidates[/bold cyan]\n")

    duplicates = engine.get_duplicate_candidates(threshold=args.duplicate_threshold)
    if duplicates:
        table = Table(title="Potential Duplicates")
        table.add_column("Node A", style="green")
        table.add_column("Node B", style="yellow")
        table.add_column("Label", style="blue")
        table.add_column("Similarity", justify="right")

        for dup in duplicates[:20]:  # Show top 20
            table.add_row(
                dup["node_a"],
                dup["node_b"],
                dup["label"],
                f"{dup['similarity']:.3f}"
            )
        console.print(table)
        console.print(f"Total: {len(duplicates)} potential duplicates\n")
    else:
        console.print("[dim]No duplicates found above threshold[/dim]\n")

    console.print("\n[bold cyan]Prune Candidates[/bold cyan]\n")

    prune = engine.get_prune_candidates(
        days_threshold=args.prune_days,
        importance_threshold=args.prune_importance
    )
    if prune:
        table = Table(title="Nodes to Prune")
        table.add_column("Name", style="red")
        table.add_column("Label", style="blue")
        table.add_column("Days Inactive", justify="right")
        table.add_column("Importance", justify="right")
        table.add_column("Accesses", justify="right")

        for node in prune[:20]:  # Show top 20
            table.add_row(
                node["name"],
                node["label"],
                str(node["days_inactive"]),
                f"{node['importance']:.2f}",
                str(node["access_count"])
            )
        console.print(table)
        console.print(f"Total: {len(prune)} nodes would be pruned\n")
    else:
        console.print("[dim]No nodes eligible for pruning[/dim]\n")


def run_consolidation(engine: ConsolidationEngine, args: argparse.Namespace) -> None:
    """Run the consolidation process."""
    mode = "[yellow]DRY RUN[/yellow]" if args.dry_run else "[green]LIVE[/green]"
    console.print(
        Panel(
            f"Running memory consolidation ({mode})\n\n"
            f"Duplicate threshold: {args.duplicate_threshold}\n"
            f"Prune after: {args.prune_days} days inactive\n"
            f"Prune importance below: {args.prune_importance}",
            title="Consolidation",
            border_style="blue"
        )
    )

    # Run consolidation
    result = engine.run_full_consolidation(
        dry_run=args.dry_run,
        merge_threshold=args.duplicate_threshold,
        prune_days=args.prune_days,
        prune_importance=args.prune_importance
    )

    # Display results
    console.print("\n[bold green]Results[/bold green]\n")

    # Merged duplicates
    if result.duplicates_merged:
        console.print("[cyan]Duplicates Merged:[/cyan]")
        for merge in result.duplicates_merged:
            merged_names = ", ".join(merge.merged_names)
            console.print(
                f"  • {merged_names} → [green]{merge.primary_name}[/green] "
                f"(similarity: {merge.similarity:.3f})"
            )
    else:
        console.print("[dim]No duplicates merged[/dim]")

    # Contradictions
    if result.contradictions_found:
        console.print("\n[yellow]Contradictions Found:[/yellow]")
        for contradiction in result.contradictions_found:
            relations = ", ".join(contradiction.relations)
            console.print(
                f"  ⚠ {contradiction.source_name} --[{relations}]--> "
                f"{contradiction.target_name}"
            )
    else:
        console.print("\n[dim]No contradictions found[/dim]")

    # Pruned nodes
    if result.nodes_pruned:
        console.print("\n[red]Nodes Pruned:[/red]")
        for name in result.nodes_pruned[:10]:  # Show first 10
            console.print(f"  ✗ {name}")
        if len(result.nodes_pruned) > 10:
            console.print(f"  ... and {len(result.nodes_pruned) - 10} more")
    else:
        console.print("\n[dim]No nodes pruned[/dim]")

    # Summary
    duration = (result.completed_at - result.started_at).total_seconds()
    console.print(
        Panel(
            f"Nodes: {result.total_nodes_before} → {result.total_nodes_after}\n"
            f"Edges: {result.total_edges_before} → {result.total_edges_after}\n"
            f"Duration: {duration:.2f}s",
            title="Summary" + (" (DRY RUN)" if args.dry_run else ""),
            border_style="green" if not args.dry_run else "yellow"
        )
    )


def main() -> int:
    """Main entry point for consolidation CLI."""
    parser = argparse.ArgumentParser(
        description="CognitiveOS Memory Consolidation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Preview what would be consolidated
    python -m src.consolidation.run --dry-run

    # Show duplicate and prune candidates
    python -m src.consolidation.run --show-candidates

    # Run with custom thresholds
    python -m src.consolidation.run --duplicate-threshold 0.85 --prune-days 60

    # Run full consolidation
    python -m src.consolidation.run
        """
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them"
    )
    parser.add_argument(
        "--duplicate-threshold",
        type=float,
        default=settings().duplicate_merge_threshold,
        help=f"Similarity threshold for duplicates (default: {settings().duplicate_merge_threshold})"
    )
    parser.add_argument(
        "--prune-days",
        type=int,
        default=settings().prune_inactive_days,
        help=f"Days of inactivity for pruning (default: {settings().prune_inactive_days})"
    )
    parser.add_argument(
        "--prune-importance",
        type=float,
        default=settings().prune_importance_threshold,
        help=f"Max importance to prune (default: {settings().prune_importance_threshold})"
    )
    parser.add_argument(
        "--show-candidates",
        action="store_true",
        help="Show duplicate and prune candidates then exit"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    try:
        # Initialize memory graph and consolidation engine
        console.print("[dim]Loading memory graph...[/dim]")
        memory = MemoryGraph()
        engine = ConsolidationEngine(memory)

        stats = memory.get_stats()
        console.print(
            f"[dim]Loaded {stats['total_nodes']} nodes, "
            f"{stats['total_edges']} edges[/dim]\n"
        )

        if stats["total_nodes"] == 0:
            console.print("[yellow]Memory is empty. Nothing to consolidate.[/yellow]")
            return 0

        if args.show_candidates:
            show_candidates(engine, args)
        else:
            run_consolidation(engine, args)

        return 0

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
