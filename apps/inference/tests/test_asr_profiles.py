"""Model selection does not initialize or download a model."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from asr_profiles import PHOWHISPER_SOURCE_SHA256, get_profile


class ProfileTests(unittest.TestCase):
    def test_default_keeps_approved_base(self):
        self.assertEqual(get_profile().key, "whisper-base")
        self.assertEqual(get_profile().path(Path("/models")), Path("/models/whisper"))

    def test_optional_profile_reports_correct_revision(self):
        profile = get_profile("phowhisper-base")
        self.assertEqual(profile.revision, "7ebdb9e88f5cc5271fb88f4d642c82ff9388650e")
        self.assertEqual(
            profile.path(Path("/models")), Path("/models/phowhisper-base-int8")
        )

    def test_timestamp_mode_matches_each_profiles_inference_contract(self):
        self.assertFalse(get_profile("whisper-base").without_timestamps)
        self.assertTrue(get_profile("phowhisper-base").without_timestamps)

    def test_remote_name_and_arbitrary_path_are_rejected(self):
        for name in ("vinai/PhoWhisper-base", "../../tmp/model", "", "whisper-small"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                get_profile(name)


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.profile = get_profile("phowhisper-base")
        self.local = self.profile.path(self.root)
        self.local.mkdir()
        self.manifest = {
            "source": "vinai/PhoWhisper-base",
            "source_revision": self.profile.revision,
            "source_weight_sha256": PHOWHISPER_SOURCE_SHA256,
            "quantization": "int8",
            "local_conversion": True,
            "files": [],
        }
        for name in (
            "model.bin",
            "config.json",
            "tokenizer.json",
            "preprocessor_config.json",
        ):
            raw = f"test fixture {name}".encode()
            (self.local / name).write_bytes(raw)
            self.manifest["files"].append(
                {
                    "file": name,
                    "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
            )
        self.write_manifest()

    def write_manifest(self):
        (self.local / "conversion-manifest.json").write_text(
            json.dumps(self.manifest), "utf8"
        )

    def test_verified_manifest_is_required_before_load(self):
        self.assertEqual(self.profile.validate_for_load(self.root), self.local)

    def test_missing_manifest_fails(self):
        (self.local / "conversion-manifest.json").unlink()
        with self.assertRaises(ValueError):
            self.profile.validate_for_load(self.root)

    def test_malformed_manifest_fails(self):
        for content in ("{", "[]", '"bad"', "null"):
            with self.subTest(content=content):
                (self.local / "conversion-manifest.json").write_text(content)
                with self.assertRaises(ValueError):
                    self.profile.validate_for_load(self.root)

    def test_revision_source_and_quantization_cannot_be_substituted(self):
        for key in (
            "source",
            "source_revision",
            "source_weight_sha256",
            "quantization",
        ):
            with self.subTest(key=key):
                previous = self.manifest[key]
                self.manifest[key] = "wrong"
                self.write_manifest()
                with self.assertRaises(ValueError):
                    self.profile.validate_for_load(self.root)
                self.manifest[key] = previous

    def test_model_digest_tamper_same_length_fails(self):
        path = self.local / "model.bin"
        path.write_bytes(b"x" * path.stat().st_size)
        with self.assertRaises(ValueError):
            self.profile.validate_for_load(self.root)

    def test_model_missing_fails(self):
        (self.local / "model.bin").unlink()
        with self.assertRaises(ValueError):
            self.profile.validate_for_load(self.root)

    def test_unlisted_files_fail(self):
        (self.local / "extra.bin").write_bytes(b"unverified")
        with self.assertRaises(ValueError):
            self.profile.validate_for_load(self.root)

    def test_path_traversal_and_duplicate_records_fail(self):
        previous = self.manifest["files"][0]["file"]
        self.manifest["files"][0]["file"] = "../model.bin"
        self.write_manifest()
        with self.assertRaises(ValueError):
            self.profile.validate_for_load(self.root)
        self.manifest["files"][0]["file"] = previous
        self.manifest["files"].append(self.manifest["files"][0])
        self.write_manifest()
        with self.assertRaises(ValueError):
            self.profile.validate_for_load(self.root)

    def test_legacy_base_does_not_require_optional_model(self):
        self.assertEqual(
            get_profile().validate_for_load(self.root), self.root / "whisper"
        )


if __name__ == "__main__":
    unittest.main()
