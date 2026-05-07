import unittest

from apps.Portal.services import tagpilot_ai


class TagPilotAITests(unittest.TestCase):
    def test_provider_status_hides_secret_values(self):
        status = tagpilot_ai.provider_status(
            {
                "OPENAI_API_KEY": "sk-test",
                "GEMINI_API_KEY": "",
                "XAI_API_KEY": "xai-test",
            }
        )

        self.assertEqual(
            status,
            {
                "providers": [
                    {
                        "id": "openai",
                        "name": "OpenAI",
                        "configured": True,
                        "models": ["gpt-5.4-mini", "gpt-5.5"],
                    },
                    {
                        "id": "gemini",
                        "name": "Gemini",
                        "configured": False,
                        "models": ["gemini-3-flash-preview", "gemini-3.1-flash-lite-preview"],
                    },
                    {
                        "id": "grok",
                        "name": "Grok",
                        "configured": True,
                        "models": ["grok-4.3", "grok-4"],
                    },
                ]
            },
        )
        self.assertNotIn("sk-test", str(status))
        self.assertNotIn("xai-test", str(status))

    def test_missing_provider_key_error_names_secret(self):
        with self.assertRaises(tagpilot_ai.MissingProviderKey) as ctx:
            tagpilot_ai.require_provider_key("gemini", {})

        self.assertEqual(str(ctx.exception), "GEMINI_API_KEY is not configured")

    def test_provider_errors_do_not_use_gateway_status(self):
        self.assertEqual(tagpilot_ai.PROVIDER_ERROR_STATUS_CODE, 424)

    def test_gemini_api_versions_try_stable_then_beta(self):
        self.assertEqual(tagpilot_ai._candidate_gemini_api_versions({}), ("v1", "v1beta"))
        self.assertEqual(
            tagpilot_ai._candidate_gemini_api_versions({"TAGPILOT_GEMINI_API_VERSIONS": "v1beta"}),
            ("v1beta",),
        )

    def test_grok_responses_payload_uses_image_input(self):
        payload = tagpilot_ai._grok_responses_payload(
            prompt="Return tags only.",
            image_bytes=b"fake-image",
            mime_type="image/png",
            model="grok-4.3",
        )

        self.assertEqual(payload["model"], "grok-4.3")
        self.assertEqual(payload["store"], False)
        content = payload["input"][0]["content"]
        self.assertEqual(content[0]["type"], "input_image")
        self.assertEqual(content[0]["image_url"], "data:image/png;base64,ZmFrZS1pbWFnZQ==")
        self.assertEqual(content[1], {"type": "input_text", "text": "Return tags only."})

    def test_grok_payload_rejects_unsupported_image_types_before_xai(self):
        with self.assertRaises(tagpilot_ai.ProviderRequestError) as ctx:
            tagpilot_ai._grok_responses_payload(
                prompt="Return tags only.",
                image_bytes=b"RIFFxxxxWEBPrest",
                mime_type="application/octet-stream",
                model="grok-4.3",
            )

        self.assertEqual(str(ctx.exception), "Grok image input must be JPEG or PNG, got image/webp")

    def test_normalize_image_mime_rejects_octet_stream_when_filename_or_bytes_identify_image(self):
        self.assertEqual(
            tagpilot_ai.normalize_image_mime_type("application/octet-stream", b"fake-image", "sample.jpg"),
            "image/jpeg",
        )
        self.assertEqual(
            tagpilot_ai.normalize_image_mime_type("application/octet-stream", b"\x89PNG\r\n\x1a\nrest", ""),
            "image/png",
        )

    def test_openai_payload_normalizes_octet_stream_data_url(self):
        payload = tagpilot_ai.build_openai_payload(
            prompt="Return tags only.",
            image_bytes=b"\xff\xd8\xffrest",
            mime_type="application/octet-stream",
            model="gpt-5.4-mini",
        )

        self.assertTrue(payload["input"][0]["content"][1]["image_url"].startswith("data:image/jpeg;base64,"))

    def test_openai_payload_uses_responses_image_input(self):
        payload = tagpilot_ai.build_openai_payload(
            prompt="Return tags only.",
            image_bytes=b"fake-image",
            mime_type="image/jpeg",
            model="gpt-5.5",
        )

        self.assertEqual(payload["model"], "gpt-5.5")
        self.assertEqual(payload["max_output_tokens"], 300)
        content = payload["input"][0]["content"]
        self.assertEqual(content[0], {"type": "input_text", "text": "Return tags only."})
        self.assertEqual(content[1]["type"], "input_image")
        self.assertEqual(content[1]["image_url"], "data:image/jpeg;base64,ZmFrZS1pbWFnZQ==")

    def test_extract_openai_text_reads_output_text(self):
        text = tagpilot_ai.extract_openai_text(
            {
                "output": [
                    {
                        "content": [
                            {"type": "output_text", "text": "tag one, tag two"},
                        ]
                    }
                ]
            }
        )

        self.assertEqual(text, "tag one, tag two")


if __name__ == "__main__":
    unittest.main()
