import os
import json
import time
import re
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def _prepare_messages(prompt, system_instruction, schema=None, use_json_mode=True):
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})

    final_prompt = prompt
    if schema:
        schema_str = json.dumps(schema, indent=2)
        final_prompt += f"\n\nYou MUST format your output strictly as a JSON object matching this JSON Schema:\n{schema_str}"

    messages.append({"role": "user", "content": final_prompt})
    return messages


def _prepare_response_format(schema, use_json_mode=True):
    if not schema or not use_json_mode:
        return None
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "parsed_locality",
            "schema": schema
        }
    }


def _parse_and_validate_json(text, schema=None):
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        return json.loads(match.group(1).strip())
    return json.loads(text)


def query_llm(
    prompt,
    system_instruction=None,
    schema=None,
    temperature=0.0,
    max_retries=3,
    use_json_mode=True,
):
    base_url = os.environ.get("LLM_BASE_URL", "http://localhost:1234/v1")
    api_key = os.environ.get("LLM_API_KEY", "lm-studio")
    model = os.environ.get("LLM_MODEL", "google/gemma-4-e4b")
    reasoning_effort = os.environ.get("LLM_REASONING_EFFORT")

    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
    )

    messages = _prepare_messages(prompt, system_instruction, schema, use_json_mode)
    response_format = _prepare_response_format(schema, use_json_mode)

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
            raw_response = text if "text" in locals() else "No text response"
            print(f"[LLM Client Warning] Attempt {attempt + 1} failed to parse JSON. Raw text:\n{raw_response}\nError: {e}")
            if attempt == max_retries - 1:
                raise RuntimeError(
                    f"Failed to obtain valid JSON from LLM after {max_retries} attempts. Last error: {e}"
                )
            time.sleep(1)


if __name__ == "__main__":
    print("Testing LLM Client...")
    test_prompt = "Say hello!"

    try:
        result = query_llm(
            prompt=test_prompt,
            system_instruction="You are a helpful assistant.",
        )
        print("Success! Result:")
        print(result)
    except Exception as e:
        print(f"\nTest run failed: {e}")
        print(
            "\nPlease ensure your environment variables are configured correctly in your .env file."
        )
