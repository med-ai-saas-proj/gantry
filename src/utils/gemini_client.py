import requests
from typing import Optional
from src.utils.logger import LOGGER


class GeminiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

    async def generate_text(self, prompt: str, temperature: float = 0.7) -> str:
        """Generate text using Gemini API"""
        try:
            headers = {"Content-Type": "application/json"}

            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "topK": 1,
                    "topP": 1,
                    "maxOutputTokens": 8192,
                    "stopSequences": [],
                    "responseMimeType": "application/json",
                    "responseSchema": {
                        "type": "object",
                        "properties": {
                            "isRelevant": {"type": "boolean"},
                            "confidenceScore": {"type": "number"},
                            "reason": {"type": "string"},
                            "newIsBetter": {"type": "boolean"},
                            "answer": {"type": "string"},
                            "regulationReferences": {"type": "array", "items": {"type": "string"}},
                            "questions": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
                "systemInstruction": {
                    "parts": [
                        {
                            "text": "You are a JSON response generator. Always respond with valid JSON only. Never include explanations, markdown formatting, or any text outside the JSON structure."
                        }
                    ]
                },
            }

            url = f"{self.base_url}?key={self.api_key}"

            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()

            result = response.json()

            if "candidates" in result and len(result["candidates"]) > 0:
                content = result["candidates"][0]["content"]["parts"][0]["text"]
                return self._clean_json_response(content.strip())
            else:
                LOGGER.error(f"No candidates in Gemini response: {result}")
                return ""

        except requests.exceptions.RequestException as e:
            LOGGER.error(f"Gemini API request failed: {str(e)}")
            raise Exception(f"Failed to call Gemini API: {str(e)}")
        except Exception as e:
            LOGGER.error(f"Gemini API error: {str(e)}")
            raise Exception(f"Gemini API error: {str(e)}")

    def _clean_json_response(self, response: str) -> str:
        """Clean and extract JSON from response"""
        # Remove markdown code blocks if present
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end != -1:
                response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                response = response[start:end].strip()

        # Find JSON object boundaries
        start_brace = response.find("{")
        end_brace = response.rfind("}")

        if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
            return response[start_brace : end_brace + 1]

        return response.strip()
