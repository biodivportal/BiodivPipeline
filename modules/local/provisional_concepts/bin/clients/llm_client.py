import os
import json
import time
import re
from io import BytesIO
from collections import deque
from openai import OpenAI


class RateLimiter:
    def __init__(self):
        self.requests = deque()
        try:
            self.max_requests = int(os.environ.get("WP5_LLM_RPM", "60"))
        except ValueError:
            self.max_requests = 60

    def wait_if_needed(self):
        if self.max_requests <= 0:
            return

        now = time.time()
        while self.requests and now - self.requests[0] > 60:
            self.requests.popleft()

        if len(self.requests) >= self.max_requests:
            sleep_time = 60 - (now - self.requests[0])
            if sleep_time > 0:
                print(
                    f"[Rate Limiter] Rate limit of {self.max_requests} RPM reached. Sleeping for {sleep_time:.2f} seconds..."
                )
                time.sleep(sleep_time)
                now = time.time()
                while self.requests and now - self.requests[0] > 60:
                    self.requests.popleft()

        self.requests.append(time.time())


_rate_limiter = RateLimiter()

WP5_LLM_USE_BATCH = os.environ.get("WP5_LLM_USE_BATCH", "true")
_BATCH_MIN = 50              # No point in using batch for small number of requests (likely can be set higher)
_BATCH_POLL_INTERVAL = 30   # wait for polling
_BATCH_TIMEOUT = 3600       # timeout set to an hour, for large runs set this higher!

_batch_client_cache = None


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
        "json_schema": {"name": "parsed_locality", "schema": schema},
    }


def _parse_and_validate_json(text, schema=None):
    # TODO: Switch to pydantic
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except ValueError:
            pass
    try:
        return json.loads(text)
    except ValueError as e:
        if schema is None:
            return text
        raise e


def query_llm(
    prompt,
    system_instruction=None,
    schema=None,
    max_retries=3,
    use_json_mode=True,
):
    base_url = os.environ.get("WP5_LLM_BASE_URL", None)
    api_key = os.environ.get("WP5_OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "WP5_OPENAI_API_KEY environment variable is not set. "
            "For Nextflow: run `nextflow secrets set WP5_OPENAI_API_KEY <key>`. "
            "For local dev: export WP5_OPENAI_API_KEY=<key>"
        )
    model = os.environ.get("WP5_LLM_MODEL", "gpt-5.4-nano-2026-03-17")

    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
    )

    messages = _prepare_messages(prompt, system_instruction, schema, use_json_mode)
    response_format = _prepare_response_format(schema, use_json_mode)

    kwargs = {
        "model": model,
        "messages": messages,
    }

    if response_format:
        kwargs["response_format"] = response_format

    for attempt in range(max_retries):
        try:
            _rate_limiter.wait_if_needed()
            response = client.chat.completions.create(**kwargs)
            text = response.choices[0].message.content
            return _parse_and_validate_json(text, schema)
        except Exception as e:
            if "response_format" in kwargs and kwargs["response_format"].get("type") == "json_schema":
                print(f"[LLM Client Warning] Structured output schema failed: {e}. Falling back to standard json_object format...")
                kwargs["response_format"] = {"type": "json_object"}
                continue
            elif "response_format" in kwargs:
                print(f"[LLM Client Warning] json_object query failed: {e}. Retrying without response_format...")
                kwargs.pop("response_format", None)
                continue

            raw_response = text if "text" in locals() else "No text response"
            print(
                f"[LLM Client Warning] Attempt {attempt + 1} failed. Raw text:\n{raw_response}\nError: {e}"
            )
            if attempt == max_retries - 1:
                raise RuntimeError(
                    f"Failed to obtain valid JSON from LLM after {max_retries} attempts. Last error: {e}"
                )
            time.sleep(1)


def _batch_client():
    # Set up a batch client cache
    global _batch_client_cache
    if _batch_client_cache is None:
        api_key = os.environ.get("WP5_OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "WP5_OPENAI_API_KEY environment variable is not set. "
                "For Nextflow: run `nextflow secrets set WP5_OPENAI_API_KEY <key>`. "
                "For local dev: export WP5_OPENAI_API_KEY=<key>"
            )
        _batch_client_cache = OpenAI(
            base_url=os.environ.get("WP5_LLM_BASE_URL", None),
            api_key=api_key,
        )
    return _batch_client_cache


def _create_and_upload_batch_file(client, jobs, model):
    """
    Build and upload the JSONL file for batch job
    """
    lines = []
    for i, job in enumerate(jobs):
        schema = job.get("schema")
        body = {
            "model": model,
            "messages": _prepare_messages(job["prompt"], job.get("system"), schema),
        }
        response_format = _prepare_response_format(schema)
        if response_format:
            body["response_format"] = response_format
        lines.append(json.dumps({
            "custom_id": f"req-{i}",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": body,
        }))

    payload = ("\n".join(lines) + "\n").encode("utf-8")
    return client.files.create(file=BytesIO(payload), purpose="batch")


def run_llm_batch(jobs, use_batch=WP5_LLM_USE_BATCH):
    if isinstance(use_batch, str):
        use_batch = use_batch.strip().lower() != "false"

    if not use_batch or len(jobs) < _BATCH_MIN:
        return [
            query_llm(prompt=j["prompt"], system_instruction=j.get("system"), schema=j.get("schema"))
            for j in jobs
        ]

    return _run_openai_batch(jobs)


def _run_openai_batch(jobs):
    client = _batch_client()
    model = os.environ.get("WP5_LLM_MODEL", "gpt-5.4-nano-2026-03-17")

    input_file = _create_and_upload_batch_file(client, jobs, model)

    batch = client.batches.create(
        input_file_id=input_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
    )
    print(f"[LLM Batch] created {batch.id} for {len(jobs)} requests; polling...")

    deadline = time.time() + _BATCH_TIMEOUT
    terminal = {"completed", "failed", "expired", "cancelled"}
    while batch.status not in terminal:
        if time.time() > deadline:
            print(f"[LLM Batch] timeout ({_BATCH_TIMEOUT}s) reached; cancelling {batch.id}")
            try:
                client.batches.cancel(batch.id)
            except Exception as e:
                print(f"[LLM Batch] cancel failed: {e}")
            break
        time.sleep(_BATCH_POLL_INTERVAL)
        batch = client.batches.retrieve(batch.id)
        print(f"[LLM Batch] {batch.id} status={batch.status} counts={getattr(batch, 'request_counts', None)}")

    results = [None] * len(jobs)
    if batch.output_file_id:
        text_out = client.files.content(batch.output_file_id).text
        for raw in text_out.splitlines():
            if not raw:
                continue
            obj = json.loads(raw)
            try:
                idx = int(obj["custom_id"].split("-", 1)[1])
            except (KeyError, ValueError, IndexError):
                continue
            resp = obj.get("response") or {}
            if obj.get("error") or resp.get("status_code") != 200:
                continue
            try:
                content = resp["body"]["choices"][0]["message"]["content"]
            except (KeyError, IndexError):
                continue
            schema = jobs[idx].get("schema") if idx < len(jobs) else None
            try:
                results[idx] = _parse_and_validate_json(content, schema)
            except Exception:
                results[idx] = None

    try:
        client.files.delete(input_file.id)
    except Exception:
        pass

    n_ok = sum(1 for r in results if r is not None)
    print(f"[LLM Batch] {batch.id} done ({batch.status}): {n_ok}/{len(jobs)} parsed; "
          f"{len(jobs) - n_ok} will fall back per-item")
    return results


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
