import io
import json
import unittest
from unittest.mock import Mock

from PIL import Image, UnidentifiedImageError
from comfyui_api.comfyui_api import ComfyAPI


class InputSecurityTests(unittest.TestCase):
    def test_workflow_keys_are_data(self):
        key = "']; raise RuntimeError('evaluated'); history['outputs']['"
        api = ComfyAPI()
        api.ws = Mock(connected=True)
        api.ws.recv.return_value = json.dumps({"type": "executing", "data": {"node": None, "prompt_id": "p"}})
        api.queue_prompt = Mock(return_value={"prompt_id": "p"})
        api.get_history = Mock(return_value={"p": {"outputs": {key: {"images": []}}}})
        self.assertEqual(api.generate_images({key: {"class_type": "SaveImage"}}), [])

    def test_nested_output_path_is_literal(self):
        self.assertEqual(ComfyAPI.find_output_node({"outer": {"output": {"class_type": "SaveImage"}}}), ["outer", "output"])

    def test_normal_png_is_fully_decoded(self):
        data = io.BytesIO()
        Image.new("RGB", (2, 3), "red").save(data, format="PNG")
        image = ComfyAPI._decode_image(data.getvalue())
        self.assertEqual(image.getpixel((0, 0)), (255, 0, 0))

    def test_eps_is_rejected_without_ghostscript(self):
        with self.assertRaises(UnidentifiedImageError):
            ComfyAPI._decode_image(b"%!PS-Adobe-3.0 EPSF-3.0\n%%BoundingBox: 0 0 2 2\nshowpage\n")

    def test_oversized_encoded_input_is_rejected(self):
        with self.assertRaises(ValueError):
            ComfyAPI._decode_image(b"x" * (32 * 1024 * 1024 + 1))
