import os
import json
import time
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def _prepare_messages(prompt, system_instruction, schema=None):
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})

    final_prompt = prompt
    if schema:
        schema_str = json.dumps(schema, indent=2)
        final_prompt += f"\n\nYou MUST format your output strictly as a JSON object matching this JSON Schema:\n{schema_str}"

    messages.append({"role": "user", "content": final_prompt})
    return messages


def _prepare_response_format(schema):
    return None


def _parse_and_validate_json(text, schema=None):
    cleaned_text = text.strip()

    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text[7:]
    elif cleaned_text.startswith("```"):
        cleaned_text = cleaned_text[3:]

    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[:-3]

    cleaned_text = cleaned_text.strip()
    return json.loads(cleaned_text)


def query_llm(
    prompt,
    system_instruction=None,
    schema=None,
    temperature=0.0,
    max_retries=3,
):
    base_url = os.environ.get("LLM_BASE_URL", "http://localhost:1234/v1")
    api_key = os.environ.get("LLM_API_KEY", "lm-studio")
    model = os.environ.get("LLM_MODEL", "google/gemma-4-e4b")
    reasoning_effort = os.environ.get("LLM_REASONING_EFFORT")

    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
    )

    messages = _prepare_messages(prompt, system_instruction, schema)
    response_format = _prepare_response_format(schema)

    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    if response_format:
        kwargs["response_format"] = response_format

    if reasoning_effort:
        kwargs["reasoning_effort"] = reasoning_effort

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(**kwargs)
            text = response.choices[0].message.content
            return _parse_and_validate_json(text, schema)
        except Exception as e:
            if attempt == max_retries - 1:
                raise RuntimeError(
                    f"Failed to obtain valid JSON from LLM after {max_retries} attempts. Last error: {e}"
                )
            time.sleep(1)


def split_text(text):
    prompt = f"""You are an expert botanical data parser. Split the location description into country, location, environment, and rest.
Rules:
- country: The country name if explicitly mentioned in the text, otherwise an empty string.
- location: Geographic placenames, administrative areas, cities, districts, or landmarks.
- environment: Terms describing the habitat or environment the plant was found in (e.g., Fichtenwald, auf Muschelkalk, sandige Krautfluren, Krautige Straßenböschung, Bahngelände). Keep this strictly to environment/habitat terms.
- rest: Everything else, including collection dates, collectors, collection numbers, elevations/altitudes, grid references (e.g. TK 8432/3), or botanical garden cultivation notes (e.g., cult. hort. bot. Berol.).
Example 1: 'Germany: Mittelrhein-Gebiet, Namedyer Werth nördl. Andernach, in Hochstaudenbeständen am Leinpfad. 27.08.1988, Leg.: R. Wisskirchen 913.' -> {{"country": "Germany", "location": "Mittelrhein-Gebiet, Namedyer Werth nördl. Andernach, Leinpfad", "environment": "in Hochstaudenbeständen", "rest": "27.08.1988, Leg.: R. Wisskirchen 913."}}
Example 2: 'Germany: Hessen, Limburger Becken, Runkel-Steeden, Bahngelände in Kerkerbach. 08.05.1983, Leg.: H. Kalheber 83-1812. ex herb. / ded. : ex Herbarium Heinz Kalheber.' -> {{"country": "Germany", "location": "Hessen, Limburger Becken, Runkel-Steeden, Kerkerbach", "environment": "Bahngelände", "rest": "08.05.1983, Leg.: H. Kalheber 83-1812. ex herb. / ded. : ex Herbarium Heinz Kalheber."}}
Input to parse: '{text}'"""
    schema = {
        "type": "object",
        "properties": {
            "country": {"type": "string"},
            "location": {"type": "string"},
            "environment": {"type": "string"},
            "rest": {"type": "string"},
        },
        "required": ["country", "location", "environment", "rest"],
    }
    return query_llm(
        prompt=prompt,
        system_instruction="You are a data parser. Always return JSON matching the schema.",
        schema=schema,
    )


if __name__ == "__main__":
    print("Testing LLM Client...")
    test_text = "Germany: Hessen, Limburger Becken, Runkel-Steeden, Bahngelände in Kerkerbach. 08.05.1983, Leg.: H. Kalheber 83-1812. ex herb. / ded. : ex Herbarium Heinz Kalheber."

    try:
        result = split_text(test_text)
        print("Success! Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"\nTest run failed: {e}")
        print(
            "\nPlease ensure your environment variables are configured correctly in your .env file."
        )
