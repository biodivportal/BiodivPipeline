import os
import json
import urllib.request
from datetime import datetime


def sync_abcd_json(api_key: str, output_path="data/abcd.json"):
    """
    Fetches the ABCD properties from the Biodivportal API and saves them to a local JSON file.
    A system metadata block is prepended at the top of the file containing the sync timestamp.
    """
    if not api_key or api_key == "your_api_key_here":
        raise ValueError("BIODIVPORTAL_API_KEY is not provided or is invalid")

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    url = f"https://data.biodivportal.gfbio.org/ontologies/ABCD/properties?apikey={api_key}"
    print("Fetching data from Biodivportal...")

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        raise Exception(f"Failed to fetch ABCD properties: {e}")

    # Add system metadata at the top
    sysdate = datetime.now().isoformat()
    system_metadata = {"_system_metadata": {"last_sync": sysdate}}

    if isinstance(data, list):
        data.insert(0, system_metadata)
    else:
        # Wrap it if it's not a list, though the current abcd.json is a list
        data = [system_metadata, data]

    output_abs_path = os.path.join(repo_root, output_path)
    os.makedirs(os.path.dirname(output_abs_path), exist_ok=True)

    with open(output_abs_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Successfully synced abcd.json to {output_abs_path} at {sysdate}")


if __name__ == "__main__":
    api_key = os.environ.get("BIODIVPORTAL_API_KEY")
    sync_abcd_json(api_key)
