import copy
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd

from credit_synth.business import annuity, fixture_profiles, materialize
from credit_synth.evaluate import evaluate
from credit_synth.generate import generate
from credit_synth.schema import validate_profiles
from credit_synth.simulator import bootstrap, bootstrap_graph, bootstrap_profiles
from credit_synth.train import edge_array, split_edges, train
from credit_synth.utils import sample_pairs
from credit_synth.validate import validate_tables


class DataContractTests(unittest.TestCase):
    def test_annuity_limit_and_known_payment(self):
        self.assertEqual(annuity(1200, 0, 12), 100)
        self.assertAlmostEqual(annuity(1_000_000, .12, 12), 88848.78868, places=4)

    def test_no_false_negatives_and_disjoint_positive_splits(self):
        df = bootstrap_profiles(160)
        edges = edge_array(df, bootstrap_graph(df))
        parts = split_edges(edges, 42)
        sets = [set(map(tuple, part.tolist())) for part in parts]
        self.assertFalse(sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2])
        self.assertEqual(set.union(*sets), set(map(tuple, edges.tolist())))
        neg = sample_pairs(len(df), 300, np.random.default_rng(1), set.union(*sets))
        self.assertFalse(set(map(tuple, neg.tolist())) & set.union(*sets))
        self.assertTrue((neg[:, 0] < neg[:, 1]).all())

    def test_sparse_pair_sampler_large_branch(self):
        pairs = sample_pairs(2000, 10_000, np.random.default_rng(1))
        self.assertEqual(len(set(map(tuple, pairs.tolist()))), 10_000)
        self.assertTrue((pairs[:, 0] < pairs[:, 1]).all())

    def test_duplicate_company_snapshot_rejected(self):
        df = bootstrap_profiles(100)
        df.loc[1, "company_id"] = df.loc[0, "company_id"]
        with self.assertRaisesRegex(ValueError, "duplicate company_id"):
            validate_profiles(df)

    def test_fixtures_and_broken_history(self):
        tables, fixtures = materialize(fixture_profiles(), 42, "2026-10-19")
        tables["company_links"] = pd.DataFrame(columns=["link_id", "source_company_id", "target_company_id",
                                                         "relation", "decoder_score"])
        report = validate_tables(tables, fixtures, "2026-10-19")
        self.assertEqual(set(report["application_statuses"]),
                         {"APPROVED", "REJECTED", "NEEDS_INFO", "COUNTER_OFFER", "ISSUED"})
        corrupted = copy.deepcopy(tables)
        corrupted["application_events"].loc[1, "to_status"] = "ISSUED"
        with self.assertRaisesRegex(ValueError, "illegal transition"):
            validate_tables(corrupted, fixtures, "2026-10-19")

    def test_cross_company_document_rejected(self):
        tables, fixtures = materialize(fixture_profiles(), 42, "2026-10-19")
        tables["company_links"] = pd.DataFrame(columns=["link_id", "source_company_id", "target_company_id",
                                                         "relation", "decoder_score"])
        tables["documents"].loc[0, "company_id"] = tables["companies"].iloc[1].company_id
        with self.assertRaisesRegex(ValueError, "document/app company mismatch"):
            validate_tables(tables, fixtures, "2026-10-19")


class NeuralPipelineTests(unittest.TestCase):
    def test_training_new_entities_exports_and_reproducibility(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bootstrap(root / "source", 180, 42)
            manifest = train(root / "source", root / "model", epochs=2, graph_epochs=2, seed=42)
            self.assertTrue(np.isfinite(manifest["cvae"]["test_negative_elbo"]))
            self.assertTrue(np.isfinite(manifest["vgae"]["prior_test"]["roc_auc"]))
            for folder in ["a", "b"]:
                report = generate(root / "model", root / folder, 24, 123)
                self.assertTrue(report["valid"] and report["sqlite_foreign_keys_valid"])
                self.assertEqual(report["rows"]["companies"], 29)
            for file in (root / "a").glob("*.csv"):
                self.assertEqual(file.read_bytes(), (root / "b" / file.name).read_bytes(), file.name)
            ref_ids = set(pd.read_csv(root / "source" / "profiles.csv").company_id)
            generated_ids = set(pd.read_csv(root / "a" / "profiles.csv").company_id)
            self.assertFalse(ref_ids & generated_ids)
            quality = evaluate(root / "model", root / "a")
            self.assertEqual(quality["synthetic_rows"], 24)
            self.assertTrue((root / "a" / "dataset.sqlite").stat().st_size > 0)
            self.assertEqual(len(json.loads((root / "a" / "fixtures.json").read_text())), 5)


if __name__ == "__main__":
    unittest.main()
