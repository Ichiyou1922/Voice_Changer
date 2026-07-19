"""voice_clone_launcher のプロファイル検証テスト。"""

import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "voice_clone_launcher.py"
SPEC = importlib.util.spec_from_file_location("voice_clone_launcher", MODULE_PATH)
launcher = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(launcher)


class ResolveProfileCommandTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo_dir = Path(self.tempdir.name)
        self.original_repo_dir = launcher.REPO_DIR
        self.original_zero_runner_path = launcher.ZERO_SHOT_RUNNER_PATH
        self.original_finetuned_runner_path = launcher.FINETUNED_RUNNER_PATH
        launcher.REPO_DIR = self.repo_dir
        launcher.ZERO_SHOT_RUNNER_PATH = self.repo_dir / "scripts" / "run_seedvc_zero_shot.sh"
        launcher.FINETUNED_RUNNER_PATH = self.repo_dir / "scripts" / "run_seedvc_finetuned.sh"

    def tearDown(self):
        launcher.REPO_DIR = self.original_repo_dir
        launcher.ZERO_SHOT_RUNNER_PATH = self.original_zero_runner_path
        launcher.FINETUNED_RUNNER_PATH = self.original_finetuned_runner_path
        self.tempdir.cleanup()

    def test_zero_shot_uses_default_seedvc_model(self):
        self.assertEqual(
            launcher.resolve_profile_command(
                {
                    "id": "zero",
                    "name": "Zero",
                    "pipeline": "v1-zero-shot-realtime",
                    "checkpoint_path": None,
                    "config_path": None,
                    "reference_audio_path": None,
                }
            ),
            [
                str(launcher.ZERO_SHOT_RUNNER_PATH),
                "--profile-name", "Zero",
                "--profile-source", "Built-in zero-shot checkpoint",
            ],
        )

    def test_finetuned_profile_requires_both_artifacts(self):
        with self.assertRaisesRegex(launcher.ProfileError, "checkpoint が未配置"):
            launcher.resolve_profile_command(
                {
                    "id": "fine",
                    "name": "Fine",
                    "pipeline": "v1-finetuned-realtime",
                    "checkpoint_path": "models/ft_model.pth",
                    "config_path": "models/config.yml",
                    "reference_audio_path": "models/reference.wav",
                }
            )

    def test_finetuned_profile_passes_checkpoint_and_config_together(self):
        model_dir = self.repo_dir / "models"
        model_dir.mkdir()
        (model_dir / "ft_model.pth").touch()
        (model_dir / "config.yml").touch()
        (model_dir / "reference.wav").touch()
        command = launcher.resolve_profile_command(
            {
                "id": "fine",
                "name": "Fine",
                "pipeline": "v1-finetuned-realtime",
                "checkpoint_path": "models/ft_model.pth",
                "config_path": "models/config.yml",
                "reference_audio_path": "models/reference.wav",
            }
        )
        self.assertEqual(
            command,
            [
                str(launcher.FINETUNED_RUNNER_PATH),
                "--checkpoint-path", str(model_dir / "ft_model.pth"),
                "--config-path", str(model_dir / "config.yml"),
                "--profile-name", "Fine",
                "--profile-source", "Loaded fine-tuned checkpoint: models/ft_model.pth",
                "--reference-audio-path", str(model_dir / "reference.wav"),
            ],
        )

    def test_rejects_partial_finetuned_pipeline_definition(self):
        with self.assertRaisesRegex(launcher.ProfileError, "checkpoint と config"):
            launcher.resolve_profile_command(
                {
                    "id": "bad",
                    "name": "Bad",
                    "pipeline": "v1-finetuned-realtime",
                    "checkpoint_path": "models/ft_model.pth",
                    "config_path": None,
                    "reference_audio_path": None,
                }
            )

    def test_finetuned_profile_can_choose_reference_in_gui(self):
        model_dir = self.repo_dir / "models"
        model_dir.mkdir()
        (model_dir / "ft_model.pth").touch()
        (model_dir / "config.yml").touch()
        command = launcher.resolve_profile_command(
            {
                "id": "fine-no-default-reference",
                "name": "Fine",
                "pipeline": "v1-finetuned-realtime",
                "checkpoint_path": "models/ft_model.pth",
                "config_path": "models/config.yml",
                "reference_audio_path": None,
            }
        )
        self.assertNotIn("--reference-audio-path", command)

    def test_zero_shot_rejects_custom_checkpoint(self):
        with self.assertRaisesRegex(launcher.ProfileError, "custom model"):
            launcher.resolve_profile_command(
                {
                    "id": "bad-zero",
                    "name": "Bad Zero",
                    "pipeline": "v1-zero-shot-realtime",
                    "checkpoint_path": "models/ft_model.pth",
                    "config_path": "models/config.yml",
                    "reference_audio_path": None,
                }
            )


if __name__ == "__main__":
    unittest.main()
