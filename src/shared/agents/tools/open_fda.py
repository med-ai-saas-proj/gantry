from src.shared.utils.logger import LOGGER

import re
from typing import Any, Literal, Optional, TypedDict, NotRequired

import requests
from pydantic_ai import RunContext
from pydantic_ai.toolsets import FunctionToolset


OPEN_FDA_ENDPOINT = "https://api.fda.gov/drug/label.json"

__all__ = ["OPEN_FDA_TOOLSET"]


class ToolOutput(TypedDict):
    url: NotRequired[str]
    results: NotRequired[Any]
    error: NotRequired[str]


get_drug_prescription_info_return_fields = [
    "description",
    "information_for_patients",
    "boxed_warning",
    "indications_and_usage",
    "dosage_and_administration",
]
get_population_specific_drug_info_return_fields = [
    "use_in_specific_populations",
    "pregnancy",
    "nursing_mothers",
    "pediatric_use",
    "geriatric_use",
]
get_drug_safety_and_interaction_info_return_fields = [
    "overdosage",
    "contraindications",
    "warnings_and_cautions",
    "adverse_reactions",
    "drug_interactions",
]


def make_fda_tool(return_fields: list[str], name: str, doc_string: str):
    def get_drug_info(
        ctx: RunContext, drug_name: str, limit: int = 5
    ) -> ToolOutput:
        try:
            LOGGER.debug("Calling tool", name=name, drug_name=drug_name)
            return search_openfda(
                map_properties_to_openfda_fields(
                    {"drug_name": drug_name, "limit": limit},
                    search_fields={
                        "drug_name": [
                            "openfda.generic_name",
                            "openfda.brand_name",
                        ]
                    },
                ),
                endpoint_url=OPEN_FDA_ENDPOINT,
                return_fields=return_fields,
            )
        except Exception as e:
            LOGGER.error("Fail to search openfda", error=str(e))
            return {"error": "Server error"}

    get_drug_info.__name__ = name
    get_drug_info.__doc__ = (
        doc_string
        + f"""
Return a list of dictionary contain the following: {", ".join(return_fields)}

Args:
    drug_name (str): Name of the drug to search for
    limit (int, optional): The number of record to return. Default to 5 
"""
    )

    return get_drug_info


OPEN_FDA_TOOLSET = FunctionToolset(
    tools=[
        make_fda_tool(
            get_drug_prescription_info_return_fields,
            "get_drug_prescription_info",
            """Retrieves essential prescription information for a given drug.
Given a drug name, this function returns drug's description, patient information, boxed warnings, approved uses, and dosage guidelines.)""",
        ),
        make_fda_tool(
            get_population_specific_drug_info_return_fields,
            "get_population_specific_drug_info",
            """Retrieves drug safety and usage information for specific populations.
Given a drug name, this function returns detailed guidance on its use during pregnancy, while nursing, and for pediatric and geriatric populations.""",
        ),
        make_fda_tool(
            get_drug_safety_and_interaction_info_return_fields,
            "get_drug_safety_and_interaction_info",
            """Retrieves safety-related information and drug interactions for a specified drug.
Given a drug name, this function returns details about overdose risks, contraindications, warnings, potential adverse reactions, and known drug interactions.""",
        ),
    ]
)


def extract_nested_fields(
    records: list[dict], fields: list[str], keywords=None
) -> list[dict]:
    """Recursively extracts nested fields from a list of dictionaries.

    :param records: List of dictionaries from which to extract fields
    :param fields: List of nested fields to extract, each specified with dot notation (e.g., 'openfda.brand_name')

    :return: List of dictionaries containing only the specified fields
    """
    extracted_records = []
    for record in records:
        extracted_record = {}
        for field in fields:
            keys = field.split(".")
            value = record
            try:
                for key in keys:
                    value = value[key]
                if (
                    key != "openfda"
                    and key != "generic_name"
                    and key != "brand_name"
                ):
                    if len(keywords) > 0:
                        value = extract_sentences_with_keywords(
                            value, keywords
                        )
                extracted_record[field] = value
            except KeyError:
                extracted_record[field] = None
        if any(extracted_record.values()):
            extracted_records.append(extracted_record)
    return extracted_records


def map_properties_to_openfda_fields(
    arguments: dict, search_fields: dict
) -> dict:
    """Maps the provided arguments to the corresponding openFDA fields based on the search_fields mapping.

    :param arguments: The input arguments containing property names and values.
    :param search_fields: The mapping of property names to openFDA fields.

    :return: A dictionary with openFDA fields and corresponding values.
    """
    mapped_arguments = {}

    for key, value in list(arguments.items()):
        if key in search_fields:
            openfda_fields = search_fields[key]
            if isinstance(openfda_fields, list):
                for field in openfda_fields:
                    mapped_arguments[field] = value
            else:
                mapped_arguments[openfda_fields] = value
            del arguments[key]
    arguments["search_fields"] = mapped_arguments
    return arguments


def extract_sentences_with_keywords(
    text_list: list[str], keywords: list[str]
) -> str:
    """Extracts sentences containing any of the specified keywords from the text."""
    sentences_with_keywords = []
    for text in text_list:
        sentence_pattern = re.compile(r"(?<=[.!?]) +")
        sentences = sentence_pattern.split(text)

        for sentence in sentences:
            if any(
                keyword.lower() in sentence.lower() for keyword in keywords
            ):
                sentences_with_keywords.append(sentence)

    return "......".join(sentences_with_keywords)


def search_openfda(
    params: dict,
    endpoint_url: str,
    return_fields: str | list[str],
    api_key: Optional[str] = None,
    sort: Optional[str] = None,
    limit: int = 5,
    skip: Optional[int] = None,
    count: Optional[int] = None,
    exists: Optional[str | list[str]] = None,
    exist_option: Literal["AND", "OR"] = "OR",
    search_keyword_option: Literal["AND", "OR"] = "AND",
    keywords_filter=True,
) -> ToolOutput:
    # Initialize params if not provided
    if params is None:
        params = {}

    if return_fields == "ALL":
        exists = None

    # Initialize search fields and construct search query
    search_fields = params.get("search_fields", {})
    search_query = []
    keywords_list = []
    if search_fields:
        for field, value in search_fields.items():
            # Merge multiple continuous black spaces into one and use one '+'
            if (
                keywords_filter
                and field != "openfda.brand_name"
                and field != "openfda.generic_name"
            ):
                keywords_list.extend(value.split())
            if field == "openfda.generic_name":
                value = value.upper()  # all generic names are in uppercase
            value = value.replace(
                " and ", " "
            )  # remove 'and' in the search query
            value = value.replace(
                " AND ", " "
            )  # remove 'AND' in the search query
            value = " ".join(value.split())
            if search_keyword_option == "AND":
                search_query.append(f"{field}:({value.replace(' ', '+AND+')})")
            if search_keyword_option == "OR":
                search_query.append(f"{field}:({value.replace(' ', '+')})")
        del params["search_fields"]
    if search_query:
        params["search"] = "+".join(search_query)
        params["search"] = "(" + params["search"] + ")"
    # Validate the presence of at least one of search, count, or sort
    if not (
        params.get("search")
        or params.get("count")
        or params.get("sort")
        or search_fields
    ):
        return {
            "error": "You must provide at least one of 'search', 'count', or 'sort' parameters."
        }

    # Set additional query parameters
    params["limit"] = params.get("limit", limit)
    params["sort"] = params.get("sort", sort)
    params["skip"] = params.get("skip", skip)
    params["count"] = params.get("count", count)
    if exists is not None:
        if isinstance(exists, str):
            exists = [exists]
        if "search" in params:
            if exist_option == "AND":
                params["search"] += (
                    "+AND+("
                    + "+AND+".join(
                        [f"_exists_:{keyword}" for keyword in exists]
                    )
                    + ")"
                )
            elif exist_option == "OR":
                params["search"] += (
                    "+AND+("
                    + "+".join([f"_exists_:{keyword}" for keyword in exists])
                    + ")"
                )
        else:
            if exist_option == "AND":
                params["search"] = "+AND+".join(
                    [f"_exists_:{keyword}" for keyword in exists]
                )
            elif exist_option == "OR":
                params["search"] = "+".join(
                    [f"_exists_:{keyword}" for keyword in exists]
                )
        # Ensure that at least one of the search fields exists
        params["search"] += (
            "+AND+("
            + "+".join([f"_exists_:{field}" for field in search_fields.keys()])
            + ")"
        )
        # params['search']+="+AND+_exists_:openfda"

    # Construct full query with additional parameters
    if api_key:
        params["api_key"] = api_key

    response = requests.get(endpoint_url, params)

    # Get the JSON response
    try:
        response_data = response.json()
    except:
        response_data = {"error": "openFDA server error"}
    if "error" in response_data:
        return {"error": response_data["error"]}

    # Extract results and return only the specified return fields
    results = response_data.get("results", [])
    if return_fields == "ALL":
        return results
    required_fields = list(search_fields.keys()) + return_fields
    extracted_results = extract_nested_fields(
        results, required_fields, keywords_list
    )
    # for extracted_result in extracted_results:
    #     if "openfda.generic_name" in extracted_result:
    #         del extracted_result["openfda.generic_name"]
    return {
        "url": response.url,
        "results": extracted_results,
    }
