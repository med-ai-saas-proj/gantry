from src.shared.custom_types.error_exception import RecoverableError

import datetime
from typing import Any, Literal, TypedDict

import httpx
from safe_result import Ok, Err, Result


LOG_QUERY_ENDPOINT = "/loki/api/v1/query_range"

LOG_LABEL_ENDPOINT = "/loki/api/v1/labels"

LOG_LABEL_VALUE_ENDPOINT = "/loki/api/v1/label/<name>/values"

type LogFilterKey = Literal["orgId", "projectId"] | str


class SearchPipeline(TypedDict):
    """Represents a search term in the log query pipeline."""

    mode: Literal["eq", "ne", "regex", "ne_regex"]
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
    def __init__(self, http_client: httpx.Client):
        self.http_client = http_client

    def search_logs(
        self,
        org_id: str,
        service_name: str,
        start: int | float | datetime.datetime,
        end: int | float | datetime.datetime,
        limit: int = 1000,
        direction: Literal["forward", "backward"] = "forward",
        level: Literal["debug", "info", "warn", "error"] | None = None,
        search_term: str
        | list[SearchPipeline | str]
        | SearchPipeline
        | None = None,
        filter: dict[LogFilterKey, str] | None = None,
    ):
        """Search logs from Loki with optional filters."""
        labels = []
        if service_name:
            labels.append(f'service_name="{service_name}"')
        selector = "{" + ", ".join(labels) + "}" if labels else "{}"

        pipeline = []

        if search_term:
            if isinstance(search_term, list):
                for term in search_term:
                    pipeline.append(search_pipeline(term))
            else:
                pipeline.append(search_pipeline(search_term))

        pipeline.append("| json")

        pipeline.append(f'| level="{level}"') if level else None
        pipeline.append(f'| orgId="{org_id}"')

        if filter:
            for key, value in filter.items():
                pipeline.append(f'| {key}="{value}"')

        query = f"{selector} {' '.join(pipeline)}".strip()

        return self.query_logs(
            query=query, start=start, end=end, limit=limit, direction=direction
        )

    def query_logs(
        self,
        query: str,
        start: int | float | datetime.datetime,
        end: int  # nanoseconds since epoch, or datetime object
        | float  # seconds since epoch
        | datetime.datetime,
        limit: int = 1000,
        direction: Literal["forward", "backward"] = "forward",
    ) -> Result[
        list[dict | str | Any], InvalidLogQueryError | LogQueryServiceError
    ]:
        """Query logs from Loki."""
        params = {
            "query": query,
            "start": to_nanoseconds(start),
            "end": to_nanoseconds(end),
            "limit": limit,
            "direction": direction,
        }

        try:
            response = self.http_client.get(LOG_QUERY_ENDPOINT, params=params)
            response.raise_for_status()
            res = response.json()
            if "data" in res and "result" in res["data"]:
                logs = []
                for stream in res["data"]["result"]:
                    for entry in stream.get("values", []):
                        timestamp, log_line = entry
                        logs.append(log_line)
                return Ok(logs)
            else:
                return Err(InvalidLogQueryError())
        except httpx.HTTPStatusError as exc:
            return Err(InvalidLogQueryError())
        except httpx.RequestError as exc:
            return Err(LogQueryServiceError())

    def get_log_labels(
        self,
        start: int | float | datetime.datetime,
        end: int | float | datetime.datetime,
    ):
        """Get log labels from Loki."""
        params = {
            "start": to_nanoseconds(start),
            "end": to_nanoseconds(end),
        }

        try:
            response = self.http_client.get(LOG_LABEL_ENDPOINT, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            print(
                f"HTTP error occurred: {exc.response.status_code} - {exc.response.text}"
            )
        except httpx.RequestError as exc:
            print(f"An error occurred while requesting: {exc}")
        except Exception as exc:
            print(f"An unexpected error occurred: {exc}")

    def get_log_label_values(
        self,
        label_name: str,
        start: int | float | datetime.datetime,
        end: int | float | datetime.datetime,
    ):
        """Get log label values from Loki."""
        params = {
            "start": to_nanoseconds(start),
            "end": to_nanoseconds(end),
        }

        endpoint = LOG_LABEL_VALUE_ENDPOINT.replace("<name>", label_name)
        try:
            response = self.http_client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            print(
                f"HTTP error occurred: {exc.response.status_code} - {exc.response.text}"
            )
        except httpx.RequestError as exc:
            print(f"An error occurred while requesting: {exc}")
        except Exception as exc:
            print(f"An unexpected error occurred: {exc}")


def to_nanoseconds(
    t: int  # nanoseconds since epoch
    | float  # seconds since epoch
    | datetime.datetime,
) -> int:
    """Convert a timestamp to nanoseconds since epoch. Accepts int, float (seconds), or datetime."""
    if isinstance(t, datetime.datetime):
        return str(int(t.timestamp() * 1e9))
    if isinstance(t, float):
        return str(int(t * 1e9))
    return str(int(t))


def search_pipeline(search_term: str | SearchPipeline):
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


if __name__ == "__main__":
    # Example usage
    http_client = httpx.Client(base_url="http://localhost:3100")
    log_query_service = LogQueryService(http_client)

    # Query logs
    logs = log_query_service.search_logs(
        org_id="test_org1",
        service_name="Med-AI-SaaS",
        start=datetime.datetime.now() - datetime.timedelta(hours=1),
        end=datetime.datetime.now(),
        limit=10,
    )
    data = logs.unwrap()
    for log_line in data:
        print(log_line)

    # # Get log labels
    labels = log_query_service.get_log_labels(
        start=datetime.datetime.now() - datetime.timedelta(hours=1),
        end=datetime.datetime.now(),
    )
    print(labels)
    #
    # Get log label values
    label_values = log_query_service.get_log_label_values(
        label_name="service_name",
        start=datetime.datetime.now() - datetime.timedelta(hours=1),
        end=datetime.datetime.now(),
    )
    print(label_values)
