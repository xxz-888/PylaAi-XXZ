import unittest
from unittest.mock import Mock, patch

import numpy as np

from detect import Detect, _build_providers, _fallback_providers_after_runtime_failure
from utils import DefaultEasyOCR
from gpu_support import resolve_easyocr_gpu


class ProviderSelectionTests(unittest.TestCase):
    @patch("detect.ort.get_available_providers", return_value=[
        "CUDAExecutionProvider",
        "DmlExecutionProvider",
        "CPUExecutionProvider",
    ])
    def test_auto_prefers_directml_before_cuda_when_available(self, *_):
        providers = _build_providers("auto")
        self.assertEqual(providers[0], "DmlExecutionProvider")

    @patch("detect.ort.get_available_providers", return_value=[
        "DmlExecutionProvider",
        "CPUExecutionProvider",
    ])
    def test_amd_alias_uses_directml(self, *_):
        providers = _build_providers("amd")
        self.assertEqual(providers[0], "DmlExecutionProvider")

    @patch("detect.ort.get_available_providers", return_value=[
        "CUDAExecutionProvider",
        "DmlExecutionProvider",
        "CPUExecutionProvider",
    ])
    def test_gpu_prefers_directml_before_cuda_when_available(self, *_):
        providers = _build_providers("gpu")
        self.assertEqual(providers[0], "DmlExecutionProvider")

    @patch("detect.ort.get_available_providers", return_value=[
        "CUDAExecutionProvider",
        "CPUExecutionProvider",
    ])
    def test_auto_uses_cuda_when_directml_is_not_installed(self, *_):
        providers = _build_providers("auto")
        self.assertEqual(providers[0][0], "CUDAExecutionProvider")

    @patch("detect.ort.get_available_providers", return_value=[
        "CUDAExecutionProvider",
        "DmlExecutionProvider",
        "CPUExecutionProvider",
    ])
    def test_explicit_cuda_still_selects_cuda(self, *_):
        providers = _build_providers("cuda")
        self.assertEqual(providers[0][0], "CUDAExecutionProvider")

    @patch("detect.ort.get_available_providers", return_value=[
        "CUDAExecutionProvider",
        "DmlExecutionProvider",
        "CPUExecutionProvider",
    ])
    def test_cuda_provider_uses_fast_cudnn_options(self, *_):
        providers = _build_providers("cuda")
        options = providers[0][1]
        self.assertEqual(options["cudnn_conv_algo_search"], "EXHAUSTIVE")
        self.assertEqual(options["cudnn_conv_use_max_workspace"], "1")
        self.assertEqual(options["use_tf32"], "1")

    @patch("detect.ort.get_available_providers", return_value=[
        "CUDAExecutionProvider",
        "DmlExecutionProvider",
        "CPUExecutionProvider",
    ])
    def test_cuda_runtime_failure_falls_back_to_directml_then_cpu(self, *_):
        providers = _fallback_providers_after_runtime_failure("CUDAExecutionProvider")
        self.assertEqual(providers[0], "DmlExecutionProvider")
        self.assertEqual(providers[-1], "CPUExecutionProvider")

    @patch("detect.ort.get_available_providers", return_value=[
        "CUDAExecutionProvider",
        "CPUExecutionProvider",
    ])
    def test_cuda_runtime_failure_falls_back_to_cpu_without_directml(self, *_):
        providers = _fallback_providers_after_runtime_failure("CUDAExecutionProvider")
        self.assertEqual(providers, ["CPUExecutionProvider"])

    def test_detect_objects_retries_after_runtime_provider_failure(self):
        detector = Detect.__new__(Detect)
        detector.device = "CUDAExecutionProvider"
        detector.output_names = ["output"]
        detector.input_name = "input"
        detector.classes = ["player"]
        detector.ignore_classes = set()
        detector.preprocess_image = Mock(return_value=(np.zeros((1, 3, 10, 10), dtype=np.float32), 10, 10))
        detector.postprocess = Mock(return_value=[])
        detector._fallback_after_runtime_failure = Mock(return_value=True)
        detector.model = Mock()
        detector.model.run.side_effect = [
            RuntimeError("CUDNN_FE failure 11: no kernel image is available for execution on the device"),
            [np.zeros((1, 6), dtype=np.float32)],
        ]

        result = detector.detect_objects(np.zeros((10, 10, 3), dtype=np.uint8))

        self.assertEqual(result, {})
        self.assertEqual(detector.model.run.call_count, 2)
        detector._fallback_after_runtime_failure.assert_called_once()

    @patch("gpu_support.resolve_easyocr_gpu", return_value=False)
    @patch("easyocr.Reader")
    def test_easyocr_uses_cpu_when_gpu_unavailable(self, mock_reader, _):
        DefaultEasyOCR()
        self.assertFalse(mock_reader.call_args.kwargs["gpu"])

    @patch("gpu_support.resolve_easyocr_gpu", return_value=True)
    @patch("gpu_support.primary_vendor", return_value="amd")
    @patch("easyocr.Reader")
    def test_easyocr_attempts_gpu_when_amd_directml_available(self, mock_reader, *_):
        DefaultEasyOCR()
        self.assertTrue(mock_reader.call_args.kwargs["gpu"])

    @patch("gpu_support.has_cuda_torch", return_value=False)
    @patch("gpu_support.has_torch_directml", return_value=False)
    @patch("gpu_support.primary_vendor", return_value="amd")
    def test_resolve_easyocr_gpu_false_without_backends(self, *_):
        self.assertFalse(resolve_easyocr_gpu())


if __name__ == "__main__":
    unittest.main()
