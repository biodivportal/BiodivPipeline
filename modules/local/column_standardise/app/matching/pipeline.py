"""
Main mapping pipeline for ABCD column standardization.

This module implements the central mapping pipeline that assigns input dataset
headers to standardized ABCD terms. It combines multiple complementary
matching strategies, including semantic similarity, lexical matching,
rule-based heuristics and data profiling.

The individual matching scores are aggregated into a final ranking for each
input header. The pipeline also computes confidence scores and determines
whether a prediction should be flagged for manual review.

The MappingPipeline class serves as the primary entry point for the matching
process and is used by both the REST API and the command-line interface.
"""

import json
import pandas as pd

from app.matching.string_matching import (
    normalize_text,
    split_term,
    string_similarity,
    term_string_similarity,
)
from app.matching.semantic_matching import (
    get_header_embeddings,
    get_candidate_embeddings,
    calculate_similarity_matrix,
    top3_mean,
)
from app.matching.heuristic_matching import heuristic_bonus
from app.matching.profiling import get_profile_scores, improved_profile_boost
from app.matching.confidence import (
    compute_confidence,
    get_review_reasons,
    manual_review_flag,
)


class MappingPipeline:
    """
    Coordinates the complete ABCD column mapping workflow.

    The pipeline initializes all required resources, executes the individual matching strategies,
    aggregates their scores, ranks ABCD terms and enriches the results with confidence scores
    and manual review flags.
    """

    def __init__(
        self,
        abcd_path="data/abcd.json",
        profiling_targets_path="app/config/profiling_targets.json",
    ):
        """
        Initialize the mapping pipeline and load all candidate terms.
        
        Args:
            abcd_path: Path to the local ABCD terms JSON file.
            profiling_targets_path: Path to the JSON file containing additional target terms
                and surface forms used for profiling and matching.
        """

        self.abcd_path = abcd_path
        self.profiling_targets_path = profiling_targets_path
        self.reload()

    def reload(self):
        """
        Reload candidate terms and recompute their semantic embeddings.
        
        This method is useful after the local ABCD schema or the profiling target
        configuration has changed, for example after synchronizing the ABCD data
        from BiodivPortal.
        """
        self._load_candidates()
        self.candidate_embeddings = get_candidate_embeddings(self.candidate_df)

    def _load_candidates(self):
        """
        Load ABCD terms and surface forms used as mapping candidates.

        The method reads canonical ABCD terms from the local ABCD schema file and
        combines them with additional terms and synonyms from the profiling target
        configuration. Each term is expanded into one or more surface forms, which
        are later used for semantic and lexical matching.

        The resulting candidate table is stored in ``self.candidate_df``.
        """    
        # Load ABCD base terms
        with open(self.abcd_path, "r", encoding="utf-8") as f:
            abcd_json = json.load(f)

        base_terms = set()
        for item in abcd_json:
            if "label" in item and len(item["label"]) > 0:
                # Use the first label as the term
                base_terms.add(item["label"][0].strip())

        # Load synonyms from profiling targets
        with open(self.profiling_targets_path, "r", encoding="utf-8") as f:
            profiling_targets = json.load(f)

        candidate_rows = []

        # Some target terms in profiling_targets might not be exactly identical to abcd.json labels,
        # but the request implies profiling_targets handles synonyms for the terms.
        # We will iterate over all base terms. If they have synonyms in profiling_targets, we use them.
        # Otherwise, just use the base term itself as the only surface form.
        for term in base_terms:
            synonyms = []
            # We check if this term or a normalized version of it exists in profiling_targets keys
            # To be safe, we also include terms in profiling_targets that might not be in base_terms
            # (as the prompt says "I removed the logic to profiling_targets")
            pass

        base_terms_normalized = {t.replace(" ", "").lower(): t for t in base_terms}

        # Since profiling targets act as the source of truth for the synonyms mapping to targets:
        # profiling_targets is now `{"entries": [{"abcd_field": "...", "synonyms": [...]}]}`
        entries = profiling_targets.get("entries", [])
        synonyms_map = {}
        for entry in entries:
            abcd_field = entry.get("abcd_field")
            syns = entry.get("synonyms", [])
            if abcd_field:
                # Map abcd_field to canonical base term if it differs only by spaces/casing
                normalized_field = abcd_field.replace(" ", "").lower()
                canonical_term = base_terms_normalized.get(normalized_field, abcd_field)

                if canonical_term in synonyms_map:
                    synonyms_map[canonical_term].extend(syns)
                else:
                    synonyms_map[canonical_term] = list(syns)

        all_terms = set(synonyms_map.keys()).union(base_terms)

        for term in all_terms:
            synonyms = synonyms_map.get(term, [])

            # Combine the term itself with its synonyms
            surface_forms = [term] + synonyms

            for surface_form in set(surface_forms):
                candidate_rows.append(
                    {
                        "term": term,
                        "surface_form": surface_form,
                        "normalized_surface_form": normalize_text(surface_form),
                        "normalized_term": split_term(term),
                    }
                )

        self.candidate_df = pd.DataFrame(candidate_rows)

    def run(
        self,
        df,
        semantic_weight=0.8,
        surface_string_weight=0.15,
        term_string_weight=0.05,
        heuristic_weight=1.0,
        profile_weight=1.0,
        profile_max_boost=0.10,
        top_n=10,
    ):
        """
        Run the complete mapping pipeline on a tabular dataset.

        For each input column, the pipeline compares the column header against all
        candidate ABCD terms and their surface forms. It combines semantic
        similarity, string similarity, heuristic rules and column profiling into
        a final score. The highest-ranked predictions are returned together with
        confidence information and manual review flags.

        Args:
            df: Input dataset as a pandas DataFrame.
            semantic_weight: Weight applied to the semantic similarity score.
            surface_string_weight: Weight applied to the string similarity between
                the header and candidate surface forms.
            term_string_weight: Weight applied to the string similarity between
                the header and canonical ABCD terms.
            heuristic_weight: Weight applied to rule-based heuristic bonuses.
            profile_weight: Weight applied to data profiling boosts.
            profile_max_boost: Maximum profiling boost added to a candidate term.
            top_n: Number of ranked predictions returned per input column.

        Returns:
            A pandas DataFrame containing ranked mapping predictions. The top-ranked
            prediction for each header includes the score margin, confidence score,
            manual review flag and review reasons.
        """
                
        headers = list(df.columns)
        header_embeddings = get_header_embeddings(headers, normalize_text)
        similarity_matrix = calculate_similarity_matrix(
            header_embeddings, self.candidate_embeddings
        )

        profile_scores_df = get_profile_scores(df)

        rows = []

        for header_idx, header in enumerate(headers):
            similarities = similarity_matrix[header_idx]
            header_lower = header.lower().strip()

            temp = self.candidate_df.copy()
            temp["semantic_surface_score"] = similarities

            temp["surface_string_score"] = temp["surface_form"].apply(
                lambda x: string_similarity(header, x)
            )

            temp["term_string_score"] = temp["term"].apply(
                lambda x: term_string_similarity(header, x)
            )

            term_rows = []

            for term, group in temp.groupby("term"):
                semantic_score = top3_mean(group["semantic_surface_score"].values)
                surface_string_score = top3_mean(group["surface_string_score"].values)
                term_string_score = group["term_string_score"].max()

                h_bonus = heuristic_bonus(header, term)
                p_boost = improved_profile_boost(
                    profile_scores_df, header, term, max_boost=profile_max_boost
                )

                final_score = (
                    semantic_weight * semantic_score
                    + surface_string_weight * surface_string_score
                    + term_string_weight * term_string_score
                    + heuristic_weight * h_bonus
                    + profile_weight * p_boost
                )

                # Check for exact synonym match
                is_exact_synonym = False
                temp_syns = self.candidate_df[self.candidate_df["term"] == term][
                    "surface_form"
                ].tolist()
                for s in temp_syns:
                    if s != term and s.lower().strip() == header_lower:
                        is_exact_synonym = True
                        break

                if is_exact_synonym:
                    final_score = 100.0

                term_rows.append(
                    {
                        "header": header,
                        "term": term,
                        "semantic_score": semantic_score,
                        "surface_string_score": surface_string_score,
                        "term_string_score": term_string_score,
                        "heuristic_bonus": h_bonus,
                        "profile_boost": p_boost,
                        "final_score": final_score,
                        "is_exact_synonym": is_exact_synonym,
                    }
                )

            ranking = (
                pd.DataFrame(term_rows)
                .sort_values("final_score", ascending=False)
                .reset_index(drop=True)
            )

            # confidence estimation is based on the gap between the best
            # and second-best candidate in the final ranking
            top1 = ranking.iloc[0]

            if len(ranking) > 1:
                top2 = ranking.iloc[1]
            else:
                top2 = top1

            margin = float(top1["final_score"] - top2["final_score"])

            if top1.get("is_exact_synonym", False):
                confidence_score = 1.0
                manual_review = False
                review_reasons = []
            else:
                confidence_score = compute_confidence(top1, top2)
                review_reasons = get_review_reasons(margin, confidence_score)
                manual_review = manual_review_flag(margin, confidence_score)

            for rank, row in enumerate(ranking.head(top_n).itertuples(), start=1):
                rows.append(
                    {
                        "header": header,
                        "rank": rank,
                        "predicted_term": row.term.replace(" ", ""),
                        "score": float(row.final_score),
                        "semantic_score": float(row.semantic_score),
                        "surface_string_score": float(row.surface_string_score),
                        "term_string_score": float(row.term_string_score),
                        "heuristic_bonus": float(row.heuristic_bonus),
                        "profile_boost": float(row.profile_boost),
                        "margin": margin if rank == 1 else None,
                        "confidence_score": confidence_score if rank == 1 else None,
                        "manual_review": manual_review if rank == 1 else None,
                        "review_reasons": review_reasons if rank == 1 else [],
                    }
                )

        return pd.DataFrame(rows)
