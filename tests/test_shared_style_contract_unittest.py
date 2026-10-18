"""Portable style contract test without additional test dependencies."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from bili_learning.config import ConfigurationError, load_obsidian_style_contract


class StyleContractTests(unittest.TestCase):
    def test_checkout_name_changes_do_not_modify_consumer_code(self):
        with tempfile.TemporaryDirectory(prefix="bili-style-") as temp:
            contract = Path(temp) / "style.json"
            raw = {
                "schema_version": 1, "repository": "https://github.com/example/new-style-name",
                "core": "snippets/learning-lab.css",
                "extensions": ["snippets/video-note.css", "snippets/new-extension.css"],
                "cssclasses": ["learning-page", "video-note"],
            }
            contract.write_text(json.dumps(raw), encoding="utf-8")
            url, files = load_obsidian_style_contract(contract)
            self.assertEqual(url, raw["repository"])
            self.assertEqual(files, ("learning-lab.css", "video-note.css", "new-extension.css"))

            raw["extensions"] = ["../untrusted.css"]
            contract.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ConfigurationError, "Unsafe or invalid"):
                load_obsidian_style_contract(contract)

    def test_actual_repo_contract_loads(self):
        repository, names = load_obsidian_style_contract()
        self.assertTrue(repository.startswith("https://github.com/"))
        self.assertEqual(names, ("learning-lab.css", "video-note.css"))


if __name__ == "__main__":
    unittest.main()
