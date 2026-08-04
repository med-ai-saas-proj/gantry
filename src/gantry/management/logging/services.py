from pyrusult import Ok, Err, Result
from gantry.shared.custom_types.error_exception import RecoverableError

import json
import datetime
from typing import Literal, TypedDict

import httpx
from structlog.stdlib import BoundLogger


LOG_QUERY_ENDPOINT = "/loki/api/v1/query_range"

LOG_LABEL_ENDPOINT = "/loki/api/v1/labels"

LOG_LABEL_VALUE_ENDPOINT = "/loki/api/v1/label/<name>/values"

type LogFilterKey = Literal["orgId", "projectId"] | str


class KeywordSearchQuery(TypedDict):
    """Represents a search term in the log query pipeline."""

    mode: Literal["eq", "ne", "regex", "ne_regex"]
    value: str


class FilterQuery(TypedDict):
    """Represents a filter term in the log query pipeline."""

    mode: Literal["eq", "ne", "regex", "ne_regex", "gt", "lt", "gte", "lte"]
    value: str


class InvalidLogQueryError(RecoverableError):
    """Raised when an invalid log query is encountered."""

    status = 400
    code = "log_query_error"
    title = "Log query error"
    detail = "An error occurred while querying logs. Please check your query and try again."


class LogQueryServiceError(RecoverableError):
    """Raised when an unexpected error occurs in the log query service."""

    status = 500
    code = "log_query_service_error"
    title = "Log query service error"
    detail = "An unexpected error occurred while querying logs. Please try again later."


class LogQueryService:
    def __init__(self, http_client: httpx.AsyncClient, logger: BoundLogger):
        self.http_client = http_client
        self.logger = logger

    async def search_logs(
        self,
        org_id: str,
        service_name: str,
        start: int | float | datetime.datetime,
        end: int | float | datetime.datetime,
        limit: int = 1000,
        direction: Literal["forward", "backward"] = "forward",
        level: Literal["debug", "info", "warn", "error"] | None = None,
        keyword: str
        | KeywordSearchQuery
        | list[KeywordSearchQuery | str]
        | None = None,
        filter: dict[LogFilterKey, str | FilterQuery | list[str]] | None = None,
        user_query: str | None = None,
    ):
        """Search logs from Loki with optional filters."""
        labels = []
        if service_name:
            labels.append(f'service_name="{service_name}"')
        selector = "{" + ", ".join(labels) + "}" if labels else "{}"

        pipeline = []

        if keyword:
            if isinstance(keyword, list):
                for v in keyword:
                    pipeline.append(keyword_pipeline(v))
            else:
                pipeline.append(keyword_pipeline(keyword))

        pipeline.append("| json")

        pipeline.append(f'| level="{level}"') if level else None
        pipeline.append(f'| orgId="{org_id}"')

        if filter:
            for key, value in filter.items():
                pipeline.append(f"| {filter_pipeline(key, value)}")

        if user_query:
            if user_query.startswith("|"):
                pipeline.append(user_query)
            else:
                pipeline.append(f"| {user_query}")

        query = f"{selector} {' '.join(pipeline)}".strip()

        # print(f"Querying logs with query: {query}, start: {start}, end: {end}, limit: {limit}, direction: {direction}")
        return await self.query_logs(
            query=query, start=start, end=end, limit=limit, direction=direction
        )

    async def query_logs(
        self,
        query: str,
        start: int | float | datetime.datetime,
        end: int  # nanoseconds since epoch, or datetime object
        | float  # seconds since epoch
        | datetime.datetime,
        limit: int = 1000,
        direction: Literal["forward", "backward"] = "forward",
    ) -> Result[list[dict], InvalidLogQueryError | LogQueryServiceError]:
        """Query logs from Loki."""
        params = {
            "query": query,
            "start": to_nanoseconds(start),
            "end": to_nanoseconds(end),
            "limit": limit,
            "direction": direction,
        }

        try:
            response = await self.http_client.get(
                LOG_QUERY_ENDPOINT, params=params
            )
            response.raise_for_status()
            res = response.json()
            if "data" in res and "result" in res["data"]:
                logs = []
                for stream in res["data"]["result"]:
                    for entry in stream.get("values", []):
                        timestamp, log_line = entry
                        if isinstance(log_line, str):
                            logs.append(json.loads(log_line))
                        elif isinstance(log_line, dict):
                            logs.append(log_line)
                return Ok(logs)
            else:
                self.logger.error(
                    "Invalid response structure from Loki", response=res
                )
                return Err(InvalidLogQueryError())
        except httpx.HTTPStatusError as exc:
            # print(f"HTTP error occurred: {exc.response.status_code} - {exc.response.text}")
            self.logger.error(
                "HTTP error occurred while querying logs",
                status_code=exc.response.status_code,
                text=exc.response.text,
            )
            return Err(InvalidLogQueryError())
        except httpx.RequestError as exc:
            self.logger.error(
                "Request error occurred while querying logs", error=str(exc)
            )
            return Err(LogQueryServiceError())

    async def get_log_labels(
        self,
        start: int | float | datetime.datetime,
        end: int | float | datetime.datetime,
    ) -> Result[list[str], LogQueryServiceError | InvalidLogQueryError]:
        """Get log labels from Loki."""
        params = {
            "start": to_nanoseconds(start),
            "end": to_nanoseconds(end),
        }

        try:
            response = await self.http_client.get(
                LOG_LABEL_ENDPOINT, params=params
            )
            response.raise_for_status()
            res = response.json()
            if "data" in res and isinstance(res["data"], list):
                return Ok(res["data"])
            else:
                self.logger.error(
                    "Invalid response structure from Loki for labels",
                    response=res,
                )
                return Err(InvalidLogQueryError())
        except httpx.HTTPStatusError as exc:
            self.logger.error(
                "HTTP error occurred while getting log labels",
                status_code=exc.response.status_code,
                text=exc.response.text,
            )
            return Err(InvalidLogQueryError())
        except httpx.RequestError as exc:
            self.logger.error(
                "Request error occurred while getting log labels",
                error=str(exc),
            )
            return Err(LogQueryServiceError())

    async def get_log_label_values(
        self,
        label_name: str,
        start: int | float | datetime.datetime,
        end: int | float | datetime.datetime,
    ) -> Result[list[str], LogQueryServiceError | InvalidLogQueryError]:
        """Get log label values from Loki."""
        params = {
            "start": to_nanoseconds(start),
            "end": to_nanoseconds(end),
        }

        endpoint = LOG_LABEL_VALUE_ENDPOINT.replace("<name>", label_name)
        try:
            response = await self.http_client.get(endpoint, params=params)
            response.raise_for_status()
            res = response.json()
            if "data" in res and isinstance(res["data"], list):
                return Ok(res["data"])
            else:
                self.logger.error(
                    "Invalid response structure from Loki for label values",
                    response=res,
                )
                return Err(InvalidLogQueryError())
        except httpx.HTTPStatusError as exc:
            self.logger.error(
                "HTTP error occurred while getting log label values",
                status_code=exc.response.status_code,
                text=exc.response.text,
            )
            return Err(InvalidLogQueryError())
        except httpx.RequestError as exc:
            self.logger.error(
                "Request error occurred while getting log label values",
                error=str(exc),
            )
            return Err(LogQueryServiceError())


def to_nanoseconds(
    t: int  # nanoseconds since epoch
    | float  # seconds since epoch
    | datetime.datetime,
) -> str:
    """Convert a timestamp to nanoseconds since epoch. Accepts int, float (seconds), or datetime."""
    if isinstance(t, datetime.datetime):
        return str(int(t.timestamp() * 1e9))
    if isinstance(t, float):
        return str(int(t * 1e9))
    return str(int(t))


def keyword_pipeline(search_term: str | KeywordSearchQuery):
    """Convert a keyword search term to a Loki pipeline expression. Supports simple string search, equality, inequality, regex, and negative regex."""
    if isinstance(search_term, str):
        return f" |= {search_term}"
    elif isinstance(search_term, dict):
        if search_term["mode"] == "eq":
            return f" |= {search_term['value']}"
        elif search_term["mode"] == "ne":
            return f" != {search_term['value']}"
        elif search_term["mode"] == "regex":
            return f" |~ {search_term['value']}"
        elif search_term["mode"] == "ne_regex":
            return f" !~ {search_term['value']}"
        else:
            raise ValueError(f"Unknown search term mode: {search_term['mode']}")
    else:
        raise ValueError(f"Invalid search term type: {type(search_term)}")


def filter_pipeline(key: LogFilterKey, value: str | FilterQuery | list[str]):
    """Convert a filter term to a Loki label filter expression. Supports equality, inequality, regex, negative regex, greater than, less than, greater than or equal, and less than or equal."""
    if isinstance(value, str) or (isinstance(value, list) and len(value) == 1):
        return f'| {key}="{value}"'
    elif isinstance(value, list):
        combined_regex = "|".join(value)
        return f'{key} =~ "{combined_regex}"'
    elif isinstance(value, dict):
        if value["mode"] == "eq":
            return f'{key}="{value["value"]}"'
        elif value["mode"] == "ne":
            return f'{key}!="{value["value"]}"'
        elif value["mode"] == "regex":
            return f'{key}=~"{value["value"]}"'
        elif value["mode"] == "ne_regex":
            return f'{key}!~"{value["value"]}"'
        elif value["mode"] == "gt":
            return f'{key}>"{value["value"]}"'
        elif value["mode"] == "lt":
            return f'{key}<"{value["value"]}"'
        elif value["mode"] == "gte":
            return f'{key}>="{value["value"]}"'
        elif value["mode"] == "lte":
            return f'{key}<="{value["value"]}"'
        else:
            raise ValueError(f"Unknown filter mode: {value['mode']}")
    else:
        raise ValueError(f"Invalid filter value type: {type(value)}")
