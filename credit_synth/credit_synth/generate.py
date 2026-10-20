from __future__ import annotations

import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from scipy.special import expit

from .business import materialize, fixture_profiles
from .export import write_dataset
from .schema import SCENARIOS, DEFAULT_MIX
from .train import load_vae, load_graph, seed_everything
from .utils import sample_pairs, weighted_pairs
from .validate import validate_tables, validate_dataset


def sample_profiles(model_dir: Path, n: int, seed: int, mix=None, batch_size=512):
    if n < 1:
        raise ValueError("companies must be positive")
    mix = np.asarray(DEFAULT_MIX if mix is None else mix, dtype=float)
    if len(mix) != 3 or not np.isfinite(mix).all() or (mix < 0).any() or not np.isclose(mix.sum(), 1):
        raise ValueError("mix needs three nonnegative probabilities summing to one")
    model, codec = load_vae(model_dir)
    conditions = np.random.default_rng(seed).choice(len(SCENARIOS), n, p=mix)
    numbers, categories = [], []
    with torch.inference_mode():
        for offset in range(0, n, batch_size):
            numeric, cats = model.sample(torch.as_tensor(conditions[offset:offset + batch_size]))
            numbers.append(numeric)
            categories.append(cats)
    profiles, projection = codec.decode(np.concatenate(numbers), np.concatenate(categories), conditions)
    profiles["is_fixture"] = False
    profiles["fixture_case"] = ""
    return profiles, projection, codec


def sample_graph(model_dir, profiles, codec, seed, candidates_per_node=32):
    columns = ["link_id", "source_company_id", "target_company_id", "relation", "decoder_score"]
    if not (model_dir / "vgae.pt").exists() or len(profiles) < 2:
        return pd.DataFrame(columns=columns)
    model, mean_degree = load_graph(model_dir)
    n = len(profiles)
    rng = np.random.default_rng(seed)
    budget = min(round(n * mean_degree / 2), n * (n - 1) // 2)
    # Degree remains stable as N grows. No independent Bernoulli thinning of the candidate graph.
    candidates = sample_pairs(n, max(n * candidates_per_node, budget * 3), rng)
    with torch.inference_mode():
        x = torch.as_tensor(codec.graph_features(profiles))
        z = model.sample_prior(x)
        logits = np.concatenate([
            model.decode(z, torch.as_tensor(chunk.T.copy())).numpy()
            for chunk in np.array_split(candidates, max(1, len(candidates) // 50_000 + 1))
        ])
    edges = weighted_pairs(candidates, logits, budget, rng)
    scores = {(int(a), int(b)): float(expit(score)) for (a, b), score in zip(candidates, logits)}
    ids = profiles.company_id.to_numpy()
    return pd.DataFrame({"link_id": [f"R{i:08d}" for i in range(len(edges))],
                         "source_company_id": ids[edges[:, 0]], "target_company_id": ids[edges[:, 1]],
                         "relation": "TRADE_WITH",
                         "decoder_score": [scores[(int(a), int(b))] for a, b in edges]}, columns=columns)


def generate(model_dir: Path, out: Path, companies: int, seed: int, as_of="2026-10-19",
             mix=None, include_fixtures=True):
    seed_everything(seed)
    profiles, projection, codec = sample_profiles(model_dir, companies, seed, mix)
    if include_fixtures:
        profiles = pd.concat([profiles, fixture_profiles()], ignore_index=True)
    tables, fixtures = materialize(profiles, seed + 101, as_of)
    tables["company_links"] = sample_graph(model_dir, profiles, codec, seed + 202)
    # Validate in-memory first. Fail before exposing a broken export.
    validate_tables(tables, fixtures, as_of)
    training_manifest = json.loads((model_dir / "training_manifest.json").read_text())
    metadata = {"schema_version": 1, "as_of": as_of, "seed": seed,
                "generated_companies": companies, "fixture_companies": len(fixtures),
                "scenario_mix": list(DEFAULT_MIX if mix is None else mix),
                "projection_counts": projection, "all_data_synthetic": True,
                "training_source": training_manifest["source"],
                "cvae_sha256": hashlib.sha256((model_dir / "cvae.pt").read_bytes()).hexdigest(),
                "vgae_sha256": hashlib.sha256((model_dir / "vgae.pt").read_bytes()).hexdigest()
                    if (model_dir / "vgae.pt").exists() else None,
                "graph_sampling": "feature-conditioned prior, uniform candidates, weighted fixed edge budget",
                "graph_scores": "ranking scores from balanced negative sampling; NOT calibrated probabilities",
                "labels": "scenario and fixture_case are generation metadata, not credit-default targets"}
    write_dataset(out, tables, metadata, fixtures)
    return validate_dataset(out)
