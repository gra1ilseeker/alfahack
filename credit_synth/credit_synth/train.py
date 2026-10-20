from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from torch.nn import functional as F
from torch.utils.data import DataLoader, TensorDataset
from sklearn.metrics import average_precision_score, roc_auc_score

from .schema import Codec, validate_profiles
from .models import ConditionalVAE, ConditionalVGAE, normalized_edges, gaussian_kl
from .utils import sample_pairs, write_json


def seed_everything(seed: int, threads: int = 2) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(threads)
    torch.use_deterministic_algorithms(True)


def profile_split(df: pd.DataFrame, seed: int):
    """Unique company IDs are enforced before this split."""
    rng = np.random.default_rng(seed)
    parts = [[], [], []]
    for _, group in df.groupby("scenario", sort=True):
        ids = rng.permutation(group.index.to_numpy())
        if len(ids) < 10:
            raise ValueError("Need >= 10 companies in every represented scenario")
        a, b = int(.70 * len(ids)), int(.85 * len(ids))
        for target, indices in zip(parts, (ids[:a], ids[a:b], ids[b:])):
            target.extend(indices.tolist())
    return tuple(df.loc[sorted(indices)].reset_index(drop=True) for indices in parts)


def _tensors(codec, df):
    return tuple(torch.as_tensor(a) for a in codec.encode(df))


def train_vae(df, out: Path, epochs: int, seed: int, hidden=128, latent=12, batch_size=128):
    train_df, val_df, test_df = profile_split(df, seed)
    codec = Codec.fit(train_df)  # validation and test never influence preprocessing
    batches = DataLoader(TensorDataset(*_tensors(codec, train_df)), batch_size=batch_size,
                         shuffle=True, generator=torch.Generator().manual_seed(seed))
    val = _tensors(codec, val_df)
    model = ConditionalVAE(hidden, latent)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-5)
    best, best_state, best_epoch = float("inf"), None, 0
    history = []
    warmup = max(1, min(20, epochs // 3))
    for epoch in range(1, epochs + 1):
        model.train()
        total = 0.
        for x, cats, cond in batches:
            opt.zero_grad(set_to_none=True)
            loss, _, _ = model.loss(model(x, cats, cond), x, cats, beta=min(1., epoch / warmup))
            if not torch.isfinite(loss):
                raise FloatingPointError("Non-finite CVAE loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.)
            opt.step()
            total += loss.item() * len(x)
        model.eval()
        with torch.no_grad():
            # A fixed Monte Carlo draw makes validation comparable between epochs.
            with torch.random.fork_rng():
                torch.manual_seed(seed + 991)
                value, recon, kl = model.loss(model(*val), val[0], val[1], beta=1.)
        entry = {"epoch": epoch, "train_loss": total / len(train_df),
                 "validation_negative_elbo": value.item(),
                 "validation_reconstruction_nll": recon.item(), "validation_kl": kl.item()}
        history.append(entry)
        if value.item() < best:
            best, best_state, best_epoch = value.item(), copy.deepcopy(model.state_dict()), epoch
        if epoch == 1 or epoch % 10 == 0 or epoch == epochs:
            print(f"CVAE epoch={epoch} train={entry['train_loss']:.3f} val={best:.3f}", flush=True)
    model.load_state_dict(best_state)
    model.eval()
    test = _tensors(codec, test_df)
    with torch.no_grad():
        test_loss = model.loss(model(*test), test[0], test[1])[0].item()
    torch.save({"kind": "conditional_vae", "schema_version": 1,
                "config": {"hidden": hidden, "latent": latent}, "codec": codec.to_dict(),
                "state_dict": model.state_dict()}, out / "cvae.pt")
    train_df.to_csv(out / "reference_train.csv", index=False)
    val_df.to_csv(out / "reference_validation.csv", index=False)
    test_df.to_csv(out / "reference_test.csv", index=False)
    write_json(out / "cvae_history.json", history)
    return model, codec, {"best_epoch": best_epoch, "validation_negative_elbo": best,
                          "test_negative_elbo": test_loss,
                          "split_rows": [len(train_df), len(val_df), len(test_df)]}


def edge_array(df: pd.DataFrame, edge_df: pd.DataFrame) -> np.ndarray:
    needed = {"source_company_id", "target_company_id"}
    if not needed.issubset(edge_df.columns):
        raise ValueError(f"company_links.csv needs columns {sorted(needed)}")
    mapping = {cid: i for i, cid in enumerate(df.company_id)}
    edges = []
    for row in edge_df.itertuples():
        if row.source_company_id not in mapping or row.target_company_id not in mapping:
            raise ValueError("Unknown company in source graph")
        a, b = sorted((mapping[row.source_company_id], mapping[row.target_company_id]))
        if a == b:
            raise ValueError("Self loops must not be supplied in source graph")
        edges.append((a, b))
    edges = np.array(sorted(set(edges)), dtype=np.int64).reshape(-1, 2)
    if len(edges) < 30:
        raise ValueError("Need at least 30 unique graph edges, or use --skip-graph")
    if len(edges) >= len(df) * (len(df) - 1) // 2:
        raise ValueError("Graph must contain non-edges")
    return edges


def split_edges(edges: np.ndarray, seed: int):
    ids = np.random.default_rng(seed).permutation(len(edges))
    a, b = int(.80 * len(ids)), int(.90 * len(ids))
    return edges[ids[:a]], edges[ids[a:b]], edges[ids[b:]]


def _edge_tensor(edges):
    return torch.as_tensor(edges.T.copy(), dtype=torch.long)


def _edge_metrics(model, z, positive, negative):
    with torch.no_grad():
        logits = torch.cat([model.decode(z, _edge_tensor(positive)),
                            model.decode(z, _edge_tensor(negative))])
        labels = np.r_[np.ones(len(positive)), np.zeros(len(negative))]
        return {"roc_auc": float(roc_auc_score(labels, logits.numpy())),
                "average_precision_balanced_sample": float(average_precision_score(labels, logits.numpy())),
                "balanced_bce": float(F.binary_cross_entropy_with_logits(
                    logits, torch.tensor(labels, dtype=torch.float32)))}


def train_graph(df, edges, codec, out: Path, epochs: int, seed: int):
    rng = np.random.default_rng(seed)
    train_pos, val_pos, test_pos = split_edges(edges, seed)
    all_positive = set(map(tuple, edges.tolist()))
    # Eval negatives and all positive splits are excluded from sampled training negatives.
    val_neg = sample_pairs(len(df), len(val_pos), rng, all_positive)
    exclude = all_positive | set(map(tuple, val_neg.tolist()))
    test_neg = sample_pairs(len(df), len(test_pos), rng, exclude)
    train_exclude = exclude | set(map(tuple, test_neg.tolist()))
    if len(val_neg) == 0 or len(test_neg) == 0:
        raise ValueError("Too few graph non-edges for disjoint evaluation")
    x = torch.as_tensor(codec.graph_features(df))
    model = ConditionalVGAE(x.shape[1])
    adjacency = normalized_edges(_edge_tensor(train_pos), len(df))
    pos = _edge_tensor(train_pos)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=1e-5)
    best, best_state, best_epoch = float("inf"), None, 0
    history = []
    for epoch in range(1, epochs + 1):
        model.train()
        neg = _edge_tensor(sample_pairs(len(df), len(train_pos), rng, train_exclude))
        if neg.shape[1] == 0:
            raise ValueError("No training negatives available")
        opt.zero_grad(set_to_none=True)
        mu, logvar = model.encode(x, adjacency)
        p_mu, p_logvar = model.prior_parameters(x)
        z = mu + torch.randn_like(mu) * (.5 * logvar).exp()
        reconstruction = .5 * (F.softplus(-model.decode(z, pos)).mean() +
                                F.softplus(model.decode(z, neg)).mean())
        # Balanced negative sampling makes scores useful for ranking, not edge probabilities.
        kl = gaussian_kl(mu, logvar, p_mu, p_logvar)
        loss = reconstruction + .03 * min(1., epoch / max(1, epochs // 3)) * kl
        if not torch.isfinite(loss):
            raise FloatingPointError("Non-finite VGAE loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 5.)
        opt.step()
        model.eval()
        with torch.no_grad():
            posterior_mu, _ = model.encode(x, adjacency)
            prior_mu, _ = model.prior_parameters(x)
            val_metrics = _edge_metrics(model, prior_mu, val_pos, val_neg)
        # Generation uses the prior; select its validation performance explicitly.
        if val_metrics["balanced_bce"] < best:
            best = val_metrics["balanced_bce"]
            best_state, best_epoch = copy.deepcopy(model.state_dict()), epoch
        history.append({"epoch": epoch, "train_loss": loss.item(), "kl": kl.item(),
                        "prior_validation": val_metrics})
        if epoch == 1 or epoch % 10 == 0 or epoch == epochs:
            print(f"VGAE epoch={epoch} loss={loss.item():.3f} prior_val_auc={val_metrics['roc_auc']:.3f}", flush=True)
    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        posterior_mu, _ = model.encode(x, adjacency)
        prior_mu, _ = model.prior_parameters(x)
        # Test is touched only after model selection.
        metrics = {"prior_test": _edge_metrics(model, prior_mu, test_pos, test_neg),
                   "posterior_test": _edge_metrics(model, posterior_mu, test_pos, test_neg)}
    torch.save({"kind": "feature_conditional_vgae", "schema_version": 1,
                "config": {"input_dim": int(x.shape[1]), "hidden": 64, "latent": 12},
                "state_dict": model.state_dict(), "mean_degree": 2 * len(edges) / len(df)}, out / "vgae.pt")
    write_json(out / "vgae_history.json", history)
    for name, pairs in [("train", train_pos), ("validation", val_pos), ("test", test_pos)]:
        pd.DataFrame(pairs, columns=["source_index", "target_index"]).to_csv(
            out / f"graph_{name}_positive.csv", index=False)
    write_json(out / "graph_node_order.json", df.company_id.tolist())
    return {"best_epoch": best_epoch, "split_edges": [len(train_pos), len(val_pos), len(test_pos)],
            "mean_degree": 2 * len(edges) / len(df), **metrics,
            "evaluation": "transductive held-out edges; balanced negatives; not unseen-node validation"}


def train(data: Path, out: Path, epochs: int, graph_epochs: int, seed: int, skip_graph=False):
    if epochs < 1 or graph_epochs < 1:
        raise ValueError("Epoch counts must be positive")
    df = pd.read_csv(data / "profiles.csv")
    validate_profiles(df, minimum_rows=100)
    if not skip_graph and not (data / "company_links.csv").exists():
        raise ValueError("Supply company_links.csv or pass --skip-graph")
    if not set(df.scenario) == {"healthy", "borderline", "distressed"}:
        raise ValueError("Training needs all three conditions (healthy, borderline, distressed)")
    seed_everything(seed)
    out.mkdir(parents=True, exist_ok=True)
    _, codec, vae_metrics = train_vae(df, out, epochs, seed)
    graph_metrics = None
    if not skip_graph:
        edges = edge_array(df, pd.read_csv(data / "company_links.csv"))
        graph_metrics = train_graph(df, edges, codec, out, graph_epochs, seed + 17)
    else:
        # A previous graph checkpoint must not silently survive a VAE-only retrain.
        (out / "vgae.pt").unlink(missing_ok=True)
    source_path = data / "source_manifest.json"
    source = json.loads(source_path.read_text()) if source_path.exists() else {"source": "user_supplied"}
    manifest = {"schema_version": 1, "seed": seed, "source": source,
                "profile_sha256": hashlib.sha256((data / "profiles.csv").read_bytes()).hexdigest(),
                "torch_version": str(torch.__version__), "cvae": vae_metrics, "vgae": graph_metrics}
    write_json(out / "training_manifest.json", manifest)
    return manifest


def load_vae(model_dir: Path):
    value = torch.load(model_dir / "cvae.pt", map_location="cpu", weights_only=True)
    if value.get("schema_version") != 1 or value.get("kind") != "conditional_vae":
        raise ValueError("Unsupported CVAE checkpoint")
    model = ConditionalVAE(**value["config"])
    model.load_state_dict(value["state_dict"])
    return model.eval(), Codec.from_dict(value["codec"])


def load_graph(model_dir: Path):
    value = torch.load(model_dir / "vgae.pt", map_location="cpu", weights_only=True)
    if value.get("schema_version") != 1 or value.get("kind") != "feature_conditional_vgae":
        raise ValueError("Unsupported VGAE checkpoint")
    model = ConditionalVGAE(**value["config"])
    model.load_state_dict(value["state_dict"])
    return model.eval(), value["mean_degree"]
