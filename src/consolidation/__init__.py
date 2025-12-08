"""Memory consolidation module for CognitiveOS.

This module provides the ConsolidationEngine for optimizing the memory graph:
- Duplicate detection and merging
- Contradiction detection
- Inactive memory pruning
"""

from src.consolidation.engine import ConsolidationEngine

__all__ = ["ConsolidationEngine"]
