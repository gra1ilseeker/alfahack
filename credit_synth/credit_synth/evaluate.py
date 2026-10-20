"""Diagnostics against unseen source snapshots; not a certificate of realism."""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.neighbors import NearestNeighbors

from .schema import FEATURES, CATEGORIES
from .train import load_vae
from .utils import write_json
from .validate import load_tables


def evaluate(model_dir: Path, dataset: Path, seed: int = 42) -> dict:
    real = pd.read_csv(model_dir / "reference_test.csv")
    training = pd.read_csv(model_dir / "reference_train.csv")
    synth = pd.read_csv(dataset / "profiles.csv")
    synth = synth.loc[~synth.is_fixture.astype(bool)].reset_index(drop=True)
    report = {"reference": "held-out source test companies", "reference_rows": len(real), "synthetic_rows": len(synth),
              "interpretation": "Agreement with the chosen source, not with real bank customers; no pass/fail threshold."}
    report["numeric_ks"] = {name: float(ks_2samp(real[name], synth[name]).statistic) for name in FEATURES}
    report["categorical_total_variation"] = {}
    for name, choices in CATEGORIES.items():
        p = real[name].value_counts(normalize=True).reindex(choices, fill_value=0)
        q = synth[name].value_counts(normalize=True).reindex(choices, fill_value=0)
        report["categorical_total_variation"][name] = float(.5 * np.abs(p - q).sum())
    cols = list(FEATURES)
    c_real = real[cols].corr().fillna(0).to_numpy()
    c_synth = synth[cols].corr().fillna(0).to_numpy()
    mask = ~np.eye(len(cols), dtype=bool)
    report["mean_absolute_correlation_error"] = float(np.abs(c_real - c_synth)[mask].mean())
    report["conditional_numeric_ks"] = {}
    for scenario in sorted(set(real.scenario)):
        r, s = real.loc[real.scenario.eq(scenario)], synth.loc[synth.scenario.eq(scenario)]
        if len(r) >= 5 and len(s) >= 5:
            report["conditional_numeric_ks"][scenario] = {
                name: float(ks_2samp(r[name], s[name]).statistic) for name in FEATURES}
    _, codec = load_vae(model_dir)
    x_real, x_synth = codec.graph_features(real), codec.graph_features(synth)
    if min(len(real), len(synth)) >= 20:
        n = min(len(real), len(synth))
        rng = np.random.default_rng(seed)
        x = np.r_[x_real[rng.choice(len(real), n, replace=False)],
                  x_synth[rng.choice(len(synth), n, replace=False)]]
        y = np.r_[np.zeros(n), np.ones(n)]
        x_train, x_test, y_train, y_test = train_test_split(x, y, stratify=y, test_size=.30, random_state=seed)
        classifier = LogisticRegression(max_iter=1000, random_state=seed).fit(x_train, y_train)
        auc = float(roc_auc_score(y_test, classifier.predict_proba(x_test)[:, 1]))
        report["two_sample_classifier_auc"] = auc
        report["two_sample_classifier_note"] = "Held-out classifier split; 0.5 means harder to distinguish for this classifier only."
    neighbors = NearestNeighbors(n_neighbors=1).fit(codec.graph_features(training))
    distances = neighbors.kneighbors(x_synth, return_distance=True)[0][:, 0]
    report["nearest_training_row_distance_median"] = float(np.median(distances))
    report["exact_training_feature_matches"] = int((distances < 1e-8).sum())
    report["privacy_note"] = "Nearest-neighbor checks do not provide differential privacy guarantees."
    tables = load_tables(dataset)
    n, e = len(tables["companies"]), len(tables["company_links"])
    report["generated_graph"] = {"nodes": n, "edges": e, "mean_degree": 2 * e / n,
                                  "density": 2 * e / (n * (n - 1)) if n > 1 else 0}
    write_json(dataset / "quality.json", report)
    return report
