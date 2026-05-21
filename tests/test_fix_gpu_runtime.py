import unittest
from unittest.mock import patch

from gpu_support import auto_candidate_variants, detect_runtime_variant
from tools import fix_gpu_runtime


class FixGpuRuntimeTests(unittest.TestCase):
    @patch("gpu_support.detect_graphics_cards", return_value=[("nvidia", "RTX 4070")])
    def test_auto_selects_directml_for_nvidia(self, _):
        self.assertEqual(detect_runtime_variant(), "directml")

    def test_auto_candidate_order_tries_cuda_only_for_nvidia(self):
        self.assertEqual(
            auto_candidate_variants([("nvidia", "RTX 4070")]),
            ["directml", "cuda", "cpu"],
        )
        self.assertEqual(
            auto_candidate_variants([("amd", "Radeon RX")]),
            ["directml", "cpu"],
        )

    @patch("gpu_support.detect_graphics_cards", return_value=[])
    def test_auto_selects_directml_without_detected_gpu(self, _):
        self.assertEqual(detect_runtime_variant(), "directml")

    @patch("utils.save_dict_as_toml")
    @patch("utils.load_toml_as_dict", return_value={})
    def test_update_config_sets_amd_directml_device_id(self, mock_load, mock_save):
        with patch(
            "gpu_support.detect_graphics_cards",
            return_value=[("intel", "Intel UHD"), ("amd", "AMD Radeon RX 7600")],
        ), patch(
            "gpu_support._wmic_video_controllers",
            return_value=["Intel UHD Graphics", "AMD Radeon RX 7600"],
        ):
            fix_gpu_runtime.update_config("directml")
        saved_config = mock_save.call_args[0][0]
        self.assertEqual(saved_config["cpu_or_gpu"], "directml")
        self.assertEqual(saved_config["directml_device_id"], "1")

    @patch("tools.fix_gpu_runtime.subprocess.run")
    def test_benchmark_variant_parses_marker_output(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = (
            'noise\nPYLA_RUNTIME_BENCHMARK={"variant":"directml","provider":"DmlExecutionProvider","ips":42.5}\n'
        )
        mock_run.return_value.stderr = ""

        result = fix_gpu_runtime.benchmark_variant("directml", runs=1)

        self.assertTrue(result["ok"])
        self.assertEqual(result["provider"], "DmlExecutionProvider")
        self.assertEqual(result["ips"], 42.5)


if __name__ == "__main__":
    unittest.main()
