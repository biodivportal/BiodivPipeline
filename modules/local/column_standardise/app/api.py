import os
import sys
import json
from io import StringIO
import pandas as pd
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header
from pydantic import BaseModel
from contextlib import asynccontextmanager

# Ensure we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import __version__
from app.sync_abcd import sync_abcd_json
from app.matching.pipeline import MappingPipeline
from app.services.llm_service import get_llm_prediction

# Initialize pipeline once on startup
pipeline = None
pipeline_ready = False
pipeline_error = None

# Paths
abcd_path = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), "data", "abcd.json"
)
weights_path = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
    "app",
    "config",
    "weights.json",
)

# Load default weights
try:
    with open(weights_path, "r", encoding="utf-8") as f:
        DEFAULT_WEIGHTS = json.load(f)
except Exception:
    DEFAULT_WEIGHTS = {
        "semantic_weight": 0.8,
        "surface_string_weight": 0.15,
        "term_string_weight": 0.05,
        "heuristic_weight": 1.0,
        "profile_weight": 1.0,
        "profile_max_boost": 0.10,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline, pipeline_ready, pipeline_error
    try:
        pipeline = MappingPipeline()
        pipeline_ready = True
    except Exception as e:
        pipeline_error = str(e)
        print(f"Failed to initialize pipeline: {e}")
        # Let it fail fast or at least be recorded. Since requirement says "fail fast on init... and have /health report", we record it.
    yield


app = FastAPI(title="ABCD Standardization API", version=__version__, lifespan=lifespan)


class HealthResponse(BaseModel):
    status: str
    pipeline_ready: bool
    version: str
    error: Optional[str] = None


@app.get("/health", response_model=HealthResponse)
def health_check():
    return {
        "status": "healthy",
        "pipeline_ready": pipeline_ready,
        "version": __version__,
        "error": pipeline_error,
    }


@app.post("/sync/abcd")
def sync_abcd(abcd_api_key: str = Header(..., description="BioDivPortal API Key")):
    try:
        sync_abcd_json(api_key=abcd_api_key)

        if pipeline is not None and pipeline_ready:
            pipeline.reload()

        return {
            "status": "success",
            "message": "ABCD schema synchronized successfully and pipeline reloaded.",
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Synchronization failed: {str(e)}")


def load_abcd_descriptions(path=abcd_path):
    term_to_desc = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            abcd_data = json.load(f)
        for item in abcd_data:
            if "label" in item and len(item["label"]) > 0:
                label = item["label"][0].replace(" ", "").lower()
                desc = item.get("definition", [""])[0] if item.get("definition") else ""
                term_to_desc[label] = desc
    except Exception as e:
        print(f"Could not load abcd.json descriptions: {e}")
    return term_to_desc


@app.post("/standardize")
async def standardize(
    file: UploadFile = File(...),
    llm_key: Optional[str] = Form(None),
    llm_provider: Optional[str] = Form(
        None, description="The LLM provider to use (e.g., 'anthropic' or 'openai')"
    ),
    llm_model: Optional[str] = Form(None),
    biodivportal_api: Optional[str] = Form(None),
    prediction_length: int = Form(1, ge=1, le=10),
    semantic_weight: float = Form(DEFAULT_WEIGHTS.get("semantic_weight", 0.8)),
    surface_string_weight: float = Form(
        DEFAULT_WEIGHTS.get("surface_string_weight", 0.15)
    ),
    term_string_weight: float = Form(DEFAULT_WEIGHTS.get("term_string_weight", 0.05)),
    heuristic_weight: float = Form(DEFAULT_WEIGHTS.get("heuristic_weight", 1.0)),
    profile_weight: float = Form(DEFAULT_WEIGHTS.get("profile_weight", 1.0)),
    profile_max_boost: float = Form(DEFAULT_WEIGHTS.get("profile_max_boost", 0.10)),
):
    if not pipeline_ready:
        raise HTTPException(
            status_code=500, detail="Pipeline is not ready. Check server logs."
        )

    if llm_provider and not llm_key:
        raise HTTPException(
            status_code=400, detail="llm_key must be provided if llm_provider is used."
        )
    if llm_key and not llm_provider:
        raise HTTPException(
            status_code=400, detail="llm_provider must be provided if llm_key is used."
        )

    if llm_provider and not llm_model:
        if llm_provider.lower() == "openai":
            llm_model = "gpt-4o-mini"
        elif llm_provider.lower() == "anthropic":
            llm_model = "claude-haiku-4-5"
        else:
            raise HTTPException(
                status_code=400, detail=f"Unsupported LLM provider: {llm_provider}"
            )

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    try:
        contents = await file.read()
        try:
            decoded = contents.decode("utf-8-sig")
        except UnicodeDecodeError:
            decoded = contents.decode("latin1")

        df = pd.read_csv(StringIO(decoded), sep=None, engine="python")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV file: {e}")

    if df.empty:
        raise HTTPException(status_code=400, detail="CSV file is empty.")

    try:
        results_df = pipeline.run(
            df,
            semantic_weight=semantic_weight,
            surface_string_weight=surface_string_weight,
            term_string_weight=term_string_weight,
            heuristic_weight=heuristic_weight,
            profile_weight=profile_weight,
            profile_max_boost=profile_max_boost,
            top_n=prediction_length,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

    term_descriptions = None
    if llm_key and llm_provider and llm_model:
        term_descriptions = load_abcd_descriptions(abcd_path)

    metadata_list = []
    headers = list(df.columns)

    total_input_tokens = 0
    total_output_tokens = 0
    llm_used_at_least_once = False

    for header in headers:
        subset = results_df[results_df["header"] == header].sort_values("rank")
        if subset.empty:
            continue

        predicted_terms = subset["predicted_term"].tolist()
        scores = subset["score"].tolist()

        # We also need confidence and review_flag from results_df if available
        # The pipeline output typically includes confidence_score, manual_review
        confidence = (
            float(subset["confidence_score"].iloc[0])
            if "confidence_score" in subset.columns
            else None
        )
        review_flag = (
            bool(subset["manual_review"].iloc[0])
            if "manual_review" in subset.columns
            else False
        )

        col_meta = {
            "header": header,
            "predicted_header": predicted_terms[0],
            "confidence": confidence,
            "review_flag": review_flag,
        }

        if prediction_length > 1:
            col_meta["predictions"] = predicted_terms
            col_meta["confidences"] = [float(s) for s in scores]

        if llm_key and llm_provider and llm_model and term_descriptions:
            valid_vals = df[header].dropna().astype(str).tolist()
            example_val = valid_vals[0][:200] if valid_vals else ""

            llm_pred = get_llm_prediction(
                api_key=llm_key,
                llm_provider=llm_provider,
                llm_model=llm_model,
                header=header,
                example_val=example_val,
                predictions=predicted_terms,
                term_descriptions=term_descriptions,
            )

            if llm_pred:
                col_meta["predicted_header"] = llm_pred.get("prediction")
                total_input_tokens += llm_pred.get("input_tokens", 0)
                total_output_tokens += llm_pred.get("output_tokens", 0)
                col_meta["llm"] = True
                llm_used_at_least_once = True

        metadata_list.append(col_meta)

    # Prepare output structure
    output_data = {
        "mapping": metadata_list,
        "metadata": {
            "configuration": {
                "semantic_weight": semantic_weight,
                "surface_string_weight": surface_string_weight,
                "term_string_weight": term_string_weight,
                "heuristic_weight": heuristic_weight,
                "profile_weight": profile_weight,
                "profile_max_boost": profile_max_boost,
                "top_n": prediction_length,
            }
        },
    }

    if llm_used_at_least_once:
        output_data["metadata"]["llm"] = {
            "used": True,
            "provider": llm_provider,
            "model": llm_model,
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
        }

    return output_data


class AddSynonymRequest(BaseModel):
    target: str
    synonym: str


@app.post("/config/synonym")
def add_synonym(request: AddSynonymRequest):
    if not request.target or not request.synonym:
        raise HTTPException(
            status_code=400, detail="Target and synonym must be provided."
        )

    targets_path = os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        "app",
        "config",
        "profiling_targets.json",
    )

    try:
        with open(targets_path, "r", encoding="utf-8") as f:
            targets_data = json.load(f)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Could not read profiling_targets.json: {e}"
        )

    entries = targets_data.get("entries", [])

    target_entry = None
    for entry in entries:
        if entry.get("abcd_field") == request.target:
            target_entry = entry
            break

    if not target_entry:
        raise HTTPException(
            status_code=400, detail=f"Target '{request.target}' does not exist."
        )

    new_synonym_lower = request.synonym.lower().strip()

    # Check if synonym is already present in ANY of the arrays
    for entry in entries:
        target_key = entry.get("abcd_field")
        synonyms_list = entry.get("synonyms", [])
        for existing_synonym in synonyms_list:
            if existing_synonym.lower().strip() == new_synonym_lower:
                raise HTTPException(
                    status_code=400,
                    detail=f"Synonym '{request.synonym}' is already mapped to '{target_key}'. Refusing to maintain a unique mapping.",
                )

    # Add synonym
    target_entry.setdefault("synonyms", []).append(request.synonym.strip())

    try:
        with open(targets_path, "w", encoding="utf-8") as f:
            json.dump(targets_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Could not save profiling_targets.json: {e}"
        )

    return {
        "status": "success",
        "message": f"Added '{request.synonym}' to '{request.target}'.",
    }
