import argparse
import json

def main():
    parser = argparse.ArgumentParser(description="Resolve provisional concepts")
    parser.add_argument("--input", required=True, help="Path to input unresolved CSV")
    parser.add_argument("--output", required=True, help="Path to output JSON")
    args = parser.parse_args()

    concepts = {}
    
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(concepts, f, indent=2)

if __name__ == "__main__":
    main()
