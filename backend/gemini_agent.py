import os
import time
from google import genai

MODEL_FALLBACKS = [
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def generate_hit_summary(features: dict, prediction: dict) -> tuple[str, str]:
    prompt = f"""
    You are a music industry analyst.
    Do NOT use markdown formatting. Do NOT use **, ##, *, or any symbols.
    Use plain sentences and line breaks only.

    Prediction score: {prediction}
    Audio features: {features}

    Explain whether this song is likely to be a hit.
    Mention strengths, weaknesses, and the most influential audio characteristics.
    Keep the explanation concise and insightful.
    Explain the statistics presented in the features as well.
    """

    last_error = None

    for model in MODEL_FALLBACKS:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                )
                text = getattr(response, "text", None)
                if text:
                    return text.strip(), model
                return "Analysis generated, but no text was returned.", model

            except Exception as e:
                last_error = e
                err = str(e)

                print(err)

                if "503" in err or "UNAVAILABLE" in err or "429" in err or "RESOURCE_EXHAUSTED" in err:
                    wait_time = 3 * (attempt + 1)
                    print(f"Model {model} busy. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                if "404" in err or "not found" in err.lower() or "PERMISSION_DENIED" in err:
                    print(f"Skipping model {model}")
                    break

                print(f"Error with {model}: {e}")
                break

    return "Gemini analysis is temporarily unavailable.", "no model working"