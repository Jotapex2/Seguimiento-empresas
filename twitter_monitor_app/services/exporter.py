from __future__ import annotations

from io import BytesIO

import pandas as pd


def _transform_excel_layout(df: pd.DataFrame) -> pd.DataFrame:
    export_df = df.copy()
    preferred_columns = [
        "id",
        "createdAt",
        "author_name",
        "author_username",
        "post_url",
        "category_detected",
        "matched_keyword",
        "text",
        "relevance_score",
        "risk_score",
        "engagement_total",
        "viewCount",
        "likeCount",
        "retweetCount",
        "replyCount",
        "quoteCount",
        "query_category",
        "query_batch",
        "is_chile_origin",
        "is_chile_context",
        "risk_terms",
        "matches",
    ]
    existing_columns = [column for column in preferred_columns if column in export_df.columns]
    if not existing_columns:
        return export_df
    remaining_columns = [column for column in export_df.columns if column not in existing_columns]
    return export_df[existing_columns + remaining_columns]


def build_export_frame(df: pd.DataFrame) -> pd.DataFrame:
    export_df = df.copy()
    if "url" not in export_df.columns:
        export_df["url"] = ""
    if "post_url" not in export_df.columns:
        export_df["post_url"] = export_df["url"]
    if "id" in export_df.columns:
        export_df["post_url"] = export_df["post_url"].fillna("")
        export_df.loc[export_df["post_url"] == "", "post_url"] = export_df["id"].apply(
            lambda value: f"https://x.com/i/web/status/{value}" if value else ""
        )
    if "matches" in export_df.columns:
        export_df["matches"] = export_df["matches"].apply(
            lambda values: ", ".join(f"{item['match_type']}:{item['group']}:{item['term']}" for item in values) if isinstance(values, list) else ""
        )
    if "risk_terms" in export_df.columns:
        export_df["risk_terms"] = export_df["risk_terms"].apply(lambda values: ", ".join(values) if isinstance(values, list) else "")
    preferred_columns = [
        "id",
        "createdAt",
        "author_name",
        "author_username",
        "category_detected",
        "matched_keyword",
        "relevance_score",
        "risk_score",
        "engagement_total",
        "likeCount",
        "retweetCount",
        "replyCount",
        "quoteCount",
        "viewCount",
        "url",
        "post_url",
        "text",
        "query_category",
        "query_batch",
        "risk_terms",
        "matches",
    ]
    existing_columns = [column for column in preferred_columns if column in export_df.columns]
    remaining_columns = [column for column in export_df.columns if column not in existing_columns]
    return export_df[existing_columns + remaining_columns]


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return build_export_frame(df).to_csv(index=False).encode("utf-8")


def dataframe_to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        _transform_excel_layout(build_export_frame(df)).to_excel(writer, sheet_name="tweets", index=False)
    return output.getvalue()
