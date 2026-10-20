from __future__ import annotations

import json
from pathlib import Path
import numpy as np


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def sample_pairs(n: int, count: int, rng: np.random.Generator,
                 excluded: set[tuple[int, int]] | None = None) -> np.ndarray:
    """Uniform unique undirected pairs, O(count) memory for large sparse graphs."""
    excluded = excluded or set()
    available = n * (n - 1) // 2 - len(excluded)
    count = min(count, available)
    if count <= 0:
        return np.empty((0, 2), dtype=np.int64)
    if n * (n - 1) // 2 < 50_000:
        pairs = np.array([(a, b) for a in range(n) for b in range(a + 1, n)
                          if (a, b) not in excluded], dtype=np.int64)
        return pairs[rng.choice(len(pairs), count, replace=False)]
    selected = set()
    while len(selected) < count:
        batch = rng.integers(0, n, size=(max(256, 2 * (count - len(selected))), 2))
        batch.sort(axis=1)
        for a, b in batch:
            pair = (int(a), int(b))
            if a != b and pair not in excluded:
                selected.add(pair)
                if len(selected) == count:
                    break
    # Stable ordering is necessary for reproducibility across Python processes.
    return np.asarray(sorted(selected), dtype=np.int64)


def weighted_pairs(candidates: np.ndarray, logits: np.ndarray, count: int,
                   rng: np.random.Generator) -> np.ndarray:
    """Gumbel top-k: fixed edge budget, weighted without replacement."""
    count = min(count, len(candidates))
    if not count:
        return np.empty((0, 2), dtype=np.int64)
    keys = logits + rng.gumbel(size=len(logits))
    indices = np.argpartition(keys, -count)[-count:]
    pairs = candidates[indices]
    return pairs[np.lexsort((pairs[:, 1], pairs[:, 0]))]
