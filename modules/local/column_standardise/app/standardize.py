import argparse
import sys
import os
import json
import pandas as pd
from io import StringIO

from app import __version__
from app.matching.pipeline import MappingPipeline
from app.services.llm_service import get_llm_prediction
from app.api import DEFAULT_WEIGHTS, abcd_path, load_abcd_descriptions


def main():
    parser = argparse.ArgumentParser(description="ABCD Column Standardizer CLI")
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument("--input", required=True, help="Path to input raw CSV file")
    parser.add_argument(
        "--out-csv", required=True, help="Path to output standardised CSV file"
    )
    parser.add_argument(
        "--out-map", required=True, help="Path to output column mapping JSON file"
    )
    # LLM flag removed, LLM is active when provider and key are given
    parser.add_argument(
        "--llm-provider",
        help="The provider to use for the LLM (e.g. anthropic, openai)",
    )
    parser.add_argument(
        "--llm-model",
        help="The model to use for the LLM (e.g. cclaude-haiku-4-5, gpt-4o)",
    )
    parser.add_argument(
        "--llm-key",
        help="The API key for the LLM provider",
    )
    parser.add_argument(
        "--biodivportal-api-key",
        help="API Key for BioDivPortal to sync the ABCD schema before processing",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=1,
        help="Number of top predictions to consider/send to LLM",
    )

    # Weights
    parser.add_argument(
        "--semantic-weight",
        type=float,
        default=DEFAULT_WEIGHTS.get("semantic_weight", 0.8),
    )
    parser.add_argument(
        "--surface-string-weight",
        type=float,
        default=DEFAULT_WEIGHTS.get("surface_string_weight", 0.15),
    )
    parser.add_argument(
        "--term-string-weight",
        type=float,
        default=DEFAULT_WEIGHTS.get("term_string_weight", 0.05),
    )
    parser.add_argument(
        "--heuristic-weight",
        type=float,
        default=DEFAULT_WEIGHTS.get("heuristic_weight", 1.0),
    )
    parser.add_argument(
        "--profile-weight",
        type=float,
        default=DEFAULT_WEIGHTS.get("profile_weight", 1.0),
    )
    parser.add_argument(
        "--profile-max-boost",
        type=float,
        default=DEFAULT_WEIGHTS.get("profile_max_boost", 0.10),
    )

    args = parser.parse_args()

    # Sniff and read CSV
    try:
        with open(args.input, "rb") as f:
            contents = f.read()

        try:
            decoded = contents.decode("utf-8-sig")
        except UnicodeDecodeError:
            decoded = contents.decode("latin1")

        df = pd.read_csv(StringIO(decoded), sep=None, engine="python")
    except Exception as e:
        print(f"Error reading CSV {args.input}: {e}", file=sys.stderr)
        sys.exit(1)

    if args.biodivportal_api_key:
        from app.sync_abcd import sync_abcd_json

        try:
            sync_abcd_json(api_key=args.biodivportal_api_key)
        except Exception as e:
            print(f"Failed to sync ABCD schema: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        pipeline = MappingPipeline()
    except Exception as e:
        print(f"Failed to initialize MappingPipeline: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        results_df = pipeline.run(
            df,
            semantic_weight=args.semantic_weight,
            surface_string_weight=args.surface_string_weight,
            term_string_weight=args.term_string_weight,
            heuristic_weight=args.heuristic_weight,
            profile_weight=args.profile_weight,
            profile_max_boost=args.profile_max_boost,
            top_n=args.top_n,
        )
    except Exception as e:
        print(f"Pipeline error: {e}", file=sys.stderr)
        sys.exit(1)

    llm_key = (
        args.llm_key
        or os.getenv("LLM_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )

    if args.llm_provider and not llm_key:
        print(
            "Error: --llm-provider specified but no LLM API key provided.",
            file=sys.stderr,
        )
        sys.exit(1)
    if llm_key and not args.llm_provider:
        print(
            "Error: LLM API key found but no --llm-provider specified.", file=sys.stderr
        )
        sys.exit(1)

    llm_model = args.llm_model
    if args.llm_provider and not llm_model:
        if args.llm_provider.lower() == "openai":
            llm_model = "gpt-4o-mini"
        elif args.llm_provider.lower() == "anthropic":
            llm_model = "claude-haiku-4-5"
        else:
            print(
                f"Error: Unsupported LLM provider: {args.llm_provider}", file=sys.stderr
            )
            sys.exit(1)

    term_descriptions = None
    if args.llm_provider and llm_key:
        term_descriptions = load_abcd_descriptions(abcd_path)

    column_mapping = []
    new_headers = {}

    total_input_tokens = 0
    total_output_tokens = 0
    llm_used_at_least_once = False

    for header in df.columns:
        subset = results_df[results_df["header"] == header].sort_values("rank")
        if subset.empty:
            new_headers[header] = header
            continue

        top_pred = subset.iloc[0]
        predicted_header = top_pred["predicted_term"]
        confidence = top_pred.get("confidence_score")
        review_flag = bool(top_pred.get("manual_review", False))

        # Optionally use LLM
        llm_pred = None
        if args.llm_provider and llm_key and llm_model and term_descriptions:
            valid_vals = df[header].dropna().astype(str).tolist()
            example_val = valid_vals[0][:200] if valid_vals else ""

            top_predictions = subset["predicted_term"].tolist()

            llm_pred = get_llm_prediction(
                api_key=llm_key,
                llm_provider=args.llm_provider,
                llm_model=llm_model,
                header=header,
                example_val=example_val,
                predictions=top_predictions,
                term_descriptions=term_descriptions,
            )

            if llm_pred:
                predicted_header = llm_pred.get("prediction")
                total_input_tokens += llm_pred.get("input_tokens", 0)
                total_output_tokens += llm_pred.get("output_tokens", 0)
                llm_used_at_least_once = True

        new_headers[header] = predicted_header

        # Save to mapping array
        col_meta = {
            "header": header,
            "predicted_header": predicted_header,
            "confidence": float(confidence) if confidence is not None else None,
            "review_flag": review_flag,
        }
        if llm_pred:
            col_meta["llm"] = True

        if args.top_n > 1:
            col_meta["predictions"] = subset["predicted_term"].tolist()
            col_meta["confidences"] = [float(s) for s in subset["score"].tolist()]

        column_mapping.append(col_meta)

    # Prepare output structure
    output_data = {
        "mapping": column_mapping,
        "metadata": {
            "configuration": {
                "semantic_weight": args.semantic_weight,
                "surface_string_weight": args.surface_string_weight,
                "term_string_weight": args.term_string_weight,
                "heuristic_weight": args.heuristic_weight,
                "profile_weight": args.profile_weight,
                "profile_max_boost": args.profile_max_boost,
                "top_n": args.top_n,
            }
        },
    }

    if llm_used_at_least_once:
        output_data["metadata"]["llm"] = {
            "used": True,
            "provider": args.llm_provider,
            "model": llm_model,
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
        }

    # Create standardised CSV
    standardised_df = df.rename(columns=new_headers)
    standardised_df.to_csv(args.out_csv, index=False)

    # Save mapping and metadata
    with open(args.out_map, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    print(f"Successfully processed {args.input}")
    print(f"Wrote {args.out_csv}")
    print(f"Wrote {args.out_map}")


if __name__ == "__main__":
    main()
