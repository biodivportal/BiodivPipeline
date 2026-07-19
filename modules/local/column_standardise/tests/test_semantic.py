import pandas as pd
from app.matching.semantic_matching import (
    get_header_embeddings,
    get_candidate_embeddings,
    calculate_similarity_matrix,
)


def test_semantic_matching():
    # Setup dummy data
    headers = ["Latitude", "Bild"]
    candidates = pd.DataFrame(
        {
            "term": ["LatitudeDecimal", "LongitudeDecimal", "Image"],
            "normalized_surface_form": [
                "latitude decimal",
                "longitude decimal",
                "image",
            ],
        }
    )

    # Mock normalize fn for headers
    def norm_fn(x):
        return str(x).lower()

    # Get embeddings
    h_emb = get_header_embeddings(headers, norm_fn)
    c_emb = get_candidate_embeddings(candidates)

    # Calculate similarity
    sim_matrix = calculate_similarity_matrix(h_emb, c_emb)

    # Ensure shape is correct (2 headers x 3 candidates)
    assert sim_matrix.shape == (2, 3)

    # Check that "Latitude" (index 0) is closest to "latitude decimal" (index 0)
    assert sim_matrix[0][0] > sim_matrix[0][1]

    # Check that "Bild" (norm to "bild") is somewhat close to "image" (multilingual-e5 should handle this)
    # The score for "image" should be the highest among the 3 candidates for "Bild"
    assert sim_matrix[1][2] > sim_matrix[1][0]
    assert sim_matrix[1][2] > sim_matrix[1][1]
