"""CognitiveOS - Local Memory System for LLMs.

A console-based chat interface with persistent memory.
"""

import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.logging import RichHandler

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.graph_loop import CognitiveLoop

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)]
)
logger = logging.getLogger("cognitive_os")

console = Console()


def print_stats(cognitive: CognitiveLoop) -> None:
    """Display memory statistics in a table."""
    stats = cognitive.get_memory_stats()

    table = Table(title="Memory Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Nodes", str(stats['total_nodes']))
    table.add_row("Total Edges", str(stats['total_edges']))

    if stats['node_types']:
        types_str = ", ".join(
            f"{k}: {v}" for k, v in stats['node_types'].items()
        )
        table.add_row("Node Types", types_str)

    if stats['relation_types']:
        rels_str = ", ".join(
            f"{k}: {v}" for k, v in stats['relation_types'].items()
        )
        table.add_row("Relations", rels_str)

    console.print(table)


def print_help() -> None:
    """Display help information."""
    help_text = """
[bold]Available Commands:[/bold]

  [cyan]stats[/cyan]    - Show memory statistics
  [cyan]clear[/cyan]    - Clear the screen
  [cyan]help[/cyan]     - Show this help message
  [cyan]quit[/cyan]     - Exit the program

[bold]Tips:[/bold]
- Share facts about yourself and the system will remember them
- Ask questions that reference past conversations
- The more you share, the more personalized responses become
"""
    console.print(Panel(help_text, title="Help", border_style="blue"))


def main() -> None:
    """Main entry point for CognitiveOS."""
    console.print(Panel.fit(
        "[bold blue]CognitiveOS[/bold blue] - Local Memory System\n\n"
        "I remember everything you tell me across conversations.\n"
        "Type [cyan]help[/cyan] for commands, [cyan]quit[/cyan] to exit.",
        title="Welcome",
        border_style="blue"
    ))

    try:
        console.print("[dim]Initializing memory system...[/dim]")
        cognitive = CognitiveLoop()
        console.print("[green]Ready![/green]\n")
    except Exception as e:
        console.print(f"[red]Failed to initialize: {e}[/red]")
        console.print("[dim]Make sure you have a .env file with OPENAI_API_KEY[/dim]")
        return

    # Show initial stats if we have existing memory
    stats = cognitive.get_memory_stats()
    if stats['total_nodes'] > 0:
        console.print(
            f"[dim]Loaded {stats['total_nodes']} memories from previous sessions[/dim]\n"
        )

    while True:
        try:
            user_input = console.input("\n[bold green]You:[/bold green] ").strip()

            if not user_input:
                continue

            # Handle commands
            cmd = user_input.lower()

            if cmd == 'quit' or cmd == 'exit':
                console.print("[yellow]Goodbye! Your memories are saved.[/yellow]")
                break

            if cmd == 'stats':
                print_stats(cognitive)
                continue

            if cmd == 'help':
                print_help()
                continue

            if cmd == 'clear':
                console.clear()
                continue

            # Regular chat
            with console.status("[dim]Thinking...[/dim]", spinner="dots"):
                response = cognitive.chat(user_input)

            console.print(f"\n[bold blue]Assistant:[/bold blue] {response}")

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Goodbye![/yellow]")
            break
        except Exception as e:
            logger.exception("Error during chat")
            console.print(f"[red]Error: {e}[/red]")
            console.print("[dim]Try again or type 'quit' to exit[/dim]")


if __name__ == "__main__":
    main()
