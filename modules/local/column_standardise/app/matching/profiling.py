"""
Column profiling utilities for ABCD column standardization.

This module analyzes the values inside dataset columns and derives profile
scores for characteristic data patterns such as coordinates, dates, URLs,
scientific names, identifiers, free-text fields or country values.

The resulting profile scores are used by the mapping pipeline as additional
evidence when ranking candidate ABCD terms.
"""

import re
import json
import pandas as pd
from pathlib import Path

# Load config
CONFIG_DIR = Path(__file__).parent.parent / "config"
RULES_FILE = CONFIG_DIR / "profiling_rules.json"
TARGETS_FILE = CONFIG_DIR / "profiling_targets.json"

with open(RULES_FILE, "r") as f:
    PROFILE_RULES = json.load(f)


def evaluate_rule(series, config):
    """
    Evaluate a single profiling rule on a column.

    The rule configuration defines which pattern or value characteristic should
    be tested. Supported rule types include numeric ranges, regular expressions,
    keyword lists, text metrics and composite rules that combine several checks.

    Args:
        series: Column values as a pandas Series.
        config: Rule configuration loaded from ``profiling_rules.json``.

    Returns:
        A score between 0.0 and 1.0 indicating how well the column matches the
        profiling rule.
    """    
    rule_type = config.get("type")

    # Missingness and uniqueness caching
    total_len = max(len(series.dropna()), 1)
    notna_sum = max(series.notna().sum(), 1)

    if rule_type == "numeric":
        num = pd.to_numeric(series, errors="coerce").dropna()
        if len(num) == 0:
            return 0.0

        in_range = ((num >= config["min"]) & (num <= config["max"])).mean()
        has_decimals = (num % 1 != 0).mean()
        is_numeric = len(num) / total_len

        base_score = in_range * is_numeric * (0.5 + 0.5 * has_decimals)
        mean_val = num.mean()

        if config["hint_min"] <= mean_val <= config["hint_max"]:
            hint = config.get("hint_weight", 1.0)
        else:
            hint = config.get("fallback_weight", 1.0)

        return round(min(base_score * hint, 1.0), 3)

    elif rule_type == "regex":
        sample = series.dropna().astype(str).head(200)
        if len(sample) == 0:
            return 0.0

        flags = re.IGNORECASE if config.get("ignore_case") else 0
        pattern = re.compile(config["pattern"], flags)
        return round(sample.apply(lambda x: bool(pattern.match(x.strip()))).mean(), 3)

    elif rule_type == "keyword":
        sample = series.dropna().astype(str).head(200)
        if len(sample) == 0:
            return 0.0

        values = set(config["values"])
        return round(sample.apply(lambda x: x.strip().lower() in values).mean(), 3)

    elif rule_type == "text_metrics":
        sample = series.dropna().astype(str).head(200)
        if len(sample) == 0:
            return 0.0

        avg_len = sample.str.len().mean()
        length_score = min(avg_len / config.get("length_divisor", 1), 1.0)

        score = length_score
        if config.get("require_spaces"):
            score *= sample.str.contains(" ").mean()

        if config.get("uniqueness_multiplier"):
            uniqueness = series.nunique() / notna_sum
            score *= min(uniqueness * config["uniqueness_multiplier"], 1.0)

        if config.get("missingness_multiplier"):
            missingness = 1 - series.notna().mean()
            score *= min(missingness * config["missingness_multiplier"], 1.0)

        return round(score, 3)

    elif rule_type == "composite":
        sample = series.dropna().astype(str).head(200)
        if len(sample) == 0:
            return 0.0

        score = 1.0

        # Base pattern
        if "base_pattern" in config:
            flags = re.IGNORECASE if config.get("ignore_case") else 0
            pattern = re.compile(config["base_pattern"], flags)
            score *= sample.apply(lambda x: bool(pattern.match(x.strip()))).mean()

        # Base rule dependency
        if "base_rule" in config:
            base_rule_config = PROFILE_RULES[config["base_rule"]]
            score *= evaluate_rule(series, base_rule_config)

        # Keyword regex
        if "keyword_regex" in config:
            flags = re.IGNORECASE if config.get("ignore_case") else 0
            pattern = re.compile(config["keyword_regex"], flags)
            keyword_ratio = sample.apply(lambda x: bool(pattern.search(x))).mean()

            base_w = config.get("base_weight", 0.0)
            kw_w = config.get("keyword_weight", 1.0)
            score *= base_w + kw_w * keyword_ratio

        # Text metrics embedded
        if "length_divisor" in config:
            avg_len = sample.str.len().mean()
            score *= min(avg_len / config["length_divisor"], 1.0)
        if config.get("require_spaces"):
            score *= sample.str.contains(" ").mean()

        # Missingness checks
        if "missingness_threshold" in config:
            missingness = 1 - series.notna().mean()
            if missingness < config["missingness_threshold"]:
                score *= config.get("missingness_below_weight", 1.0)
            else:
                score *= config.get("missingness_above_weight", 1.0)

        # Uniqueness checks
        if config.get("multiply_by_uniqueness"):
            score *= series.nunique() / notna_sum

        if "uniqueness_threshold" in config:
            uniqueness = series.nunique() / notna_sum
            if uniqueness < config["uniqueness_threshold"]:
                score *= config.get("uniqueness_below_weight", 1.0)
            else:
                score *= config.get("uniqueness_above_weight", 1.0)

        # Few values check
        if "few_values_threshold" in config:
            n_unique = series.nunique()
            threshold = config["few_values_threshold"]
            if n_unique <= threshold:
                pass  # weight 1.0
            else:
                penalty_divisor = config.get("few_values_penalty_divisor", 1)
                few_values_hint = max(
                    0.0, 1.0 - (n_unique - threshold) / penalty_divisor
                )
                score *= few_values_hint

        # Exclude keywords
        if "exclude_keywords" in config:
            exclude_set = set(config["exclude_keywords"])
            country_ratio = sample.apply(
                lambda x: x.strip().lower() in exclude_set
            ).mean()
            score *= 1.0 - country_ratio

        # Diversity
        if "diversity_divisor" in config:
            diversity_ok = min(series.nunique() / config["diversity_divisor"], 1.0)
            score *= diversity_ok

        return round(min(score, 1.0), 3)

    return 0.0


def get_profile_scores(df):
    """
    Compute all profiling scores for all columns in a dataset.

    Each column is evaluated against every profiling rule from
    ``profiling_rules.json``. In addition, basic column statistics such as
    missingness and uniqueness are included.

    Args:
        df: Input dataset as a pandas DataFrame.

    Returns:
        A pandas DataFrame with one row per input column and one score column
        per profiling rule.
    """
    headers = list(df.columns)
    profile_rows = []

    for header in headers:
        series = df[header]

        row = {
            "header": header,
            "missingness": round(1 - series.notna().mean(), 3),
            "uniqueness": round(series.nunique() / max(series.notna().sum(), 1), 3),
        }

        for rule_name, rule_config in PROFILE_RULES.items():
            row[rule_name] = evaluate_rule(series, rule_config)

        profile_rows.append(row)

    return pd.DataFrame(profile_rows)


def improved_profile_boost(profile_scores_df, header, term, max_boost=0.10):
    """
    Calculate the profiling-based score boost for a candidate ABCD term.

    The function checks whether the candidate term is listed as a target for
    any profiling rule in ``profiling_targets.json``. If matching rules exist,
    the highest corresponding profile score for the given header is converted
    into a bounded boost value.

    Args:
        profile_scores_df: DataFrame returned by ``get_profile_scores``.
        header: Original input column header.
        term: Candidate ABCD term.
        max_boost: Maximum boost that can be added to the candidate score.

    Returns:
        A float between 0.0 and ``max_boost``.
    """
    row = profile_scores_df[profile_scores_df["header"] == header]

    if len(row) == 0:
        return 0.0

    row = row.iloc[0]
    boosts = []

    term_lower = str(term).lower()

    for rule_name, rule_config in PROFILE_RULES.items():
        abcd_term = rule_config.get("abcd_term")

        # If abcd_term is provided in the config, we match against it
        if abcd_term:
            if str(abcd_term).replace(" ", "").lower() == term_lower.replace(" ", ""):
                boosts.append(row.get(rule_name, 0.0))
        # Otherwise, we fallback to checking if the rule_name matches the term
        elif rule_name.replace(" ", "").lower() == term_lower.replace(" ", ""):
            boosts.append(row.get(rule_name, 0.0))

    if len(boosts) == 0:
        return 0.0

    return max(boosts) * max_boost
