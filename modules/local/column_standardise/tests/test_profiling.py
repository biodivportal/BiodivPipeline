import pandas as pd
from app.matching.profiling import improved_profile_boost, get_profile_scores


def test_get_profile_scores_and_boost():
    df = pd.DataFrame(
        {
            "Lat": [45.1, 46.2, 44.9],
            "Long": [-12.1, -11.5, -10.0],
            "Empty": [None, None, None],
            "Strings": ["a", "b", "c"],
        }
    )

    # Run profiling
    scores_df = get_profile_scores(df)

    # Lat should match latitude numeric profile strongly
    lat_row = scores_df[scores_df["header"] == "Lat"].iloc[0]
    assert lat_row["latitude"] > lat_row["longitude"]

    # Empty and Strings should have zero profiling scores for numeric categories
    empty_row = scores_df[scores_df["header"] == "Empty"].iloc[0]
    strings_row = scores_df[scores_df["header"] == "Strings"].iloc[0]
    assert empty_row["latitude"] == 0.0
    assert strings_row["latitude"] == 0.0

    # Test improved_profile_boost
    # Term 'LatitudeDecimal' targets the 'latitude' rule
    boost = improved_profile_boost(scores_df, "Lat", "LatitudeDecimal", max_boost=0.1)
    assert boost > 0.0
    assert boost == lat_row["latitude"] * 0.1

    # Irrelevant term should get 0 boost
    boost_zero = improved_profile_boost(
        scores_df, "Lat", "SomethingElse", max_boost=0.1
    )
    assert boost_zero == 0.0
