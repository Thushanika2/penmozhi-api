import unittest

from app.services.ai_assistant import (
    LANGUAGE_MATCHING_RULE,
    build_system_instruction,
    detect_message_language,
)


class AIAssistantLanguageTests(unittest.TestCase):
    def test_detects_english_questions(self):
        questions = [
            "When is my next period due?",
            "How long is my average cycle?",
            "Could my period be late this month?",
        ]

        for question in questions:
            with self.subTest(question=question):
                self.assertEqual(detect_message_language(question), "English")

    def test_detects_tamil_questions(self):
        questions = [
            "எனது அடுத்த மாதவிடாய் எப்போது வரும்?",
            "என்னுடைய சராசரி சுழற்சி எத்தனை நாட்கள்?",
            "இந்த மாதம் மாதவிடாய் தாமதமாகுமா?",
            "எனக்கு PCOS இருக்குமா?",
        ]

        for question in questions:
            with self.subTest(question=question):
                self.assertEqual(detect_message_language(question), "Tamil")

    def test_english_directive_overrides_tamil_reference_context(self):
        instruction = build_system_instruction(
            "கடைசி மாதவிடாய் 28 நாட்களுக்கு முன்பு தொடங்கியது.",
            "When is my next period due?",
        )

        self.assertTrue(instruction.startswith("DETECTED USER MESSAGE LANGUAGE: English."))
        self.assertIn("entire response text and all clarification options must be in English", instruction)
        self.assertIn("reference material below may be in Tamil", instruction)

    def test_tamil_directive_overrides_english_reference_context(self):
        instruction = build_system_instruction(
            "Average cycle length: 28 days",
            "எனது அடுத்த மாதவிடாய் எப்போது வரும்?",
        )

        self.assertTrue(instruction.startswith("DETECTED USER MESSAGE LANGUAGE: Tamil."))
        self.assertIn("entire response text and all clarification options must be in Tamil", instruction)

    def test_critical_language_rule_is_first_system_prompt_rule(self):
        self.assertTrue(LANGUAGE_MATCHING_RULE.startswith("LANGUAGE MATCHING — CRITICAL:"))


if __name__ == "__main__":
    unittest.main()
