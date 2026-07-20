"""
Semantic matching utilities based on sentence embeddings.

This module encodes input headers and candidate ABCD surface forms with a
multilingual SentenceTransformer model. The resulting embeddings are compared
with cosine similarity and used as the semantic score component in the mapping
pipeline.
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

model = SentenceTransformer("intfloat/multilingual-e5-small")


def query_text(text):
    """
    Format a header text as a query for the embedding model.

    Args:
        text: Input header text.

    Returns:
        The text prefixed in query format.
    """
    return "query: " + str(text)


def passage_text(text):
    """
    Format a candidate surface form as a passage for the embedding model.

    Args:
        text: Candidate term or surface form.

    Returns:
        The text prefixed in passage format.
    """
    return "passage: " + str(text)


def top3_mean(scores):
    """
    Calculate the mean of the three highest scores.

    Args:
        scores: Iterable of numeric similarity scores.

    Returns:
        Mean value of the three highest scores.
    """
    scores = np.sort(scores)[::-1]
    return np.mean(scores[:3])


def get_header_embeddings(headers, normalize_text_fn):
    """
    Generate embeddings for input dataset headers.

    Args:
        headers: List of original input column headers.
        normalize_text_fn: Function used to normalize headers before encoding.

    Returns:
        NumPy array containing normalized header embeddings.
    """
    return model.encode(
        [query_text(normalize_text_fn(header)) for header in headers],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )


def get_candidate_embeddings(candidate_df):
    """
    Generate embeddings for candidate ABCD surface forms.

    Args:
        candidate_df: DataFrame containing a ``normalized_surface_form`` column.

    Returns:
        NumPy array containing normalized candidate embeddings.
    """
    return model.encode(
        [passage_text(text) for text in candidate_df["normalized_surface_form"]],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )


def calculate_similarity_matrix(header_embeddings, candidate_embeddings):
    """
    Compute cosine similarities between header and candidate embeddings.

    Args:
        header_embeddings: NumPy array of encoded input headers.
        candidate_embeddings: NumPy array of encoded candidate surface forms.

    Returns:
        Similarity matrix with one row per header and one column per candidate.
    """
    return cosine_similarity(header_embeddings, candidate_embeddings)
