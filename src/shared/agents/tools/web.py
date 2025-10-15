from src.crawler.services import SearchTimeRange
from src.crawler.initialize import CRAWLER_SERVICE
from src.shared.utils.logger import LOGGER

from typing import Optional, TypedDict

from pydantic_ai import RunContext
from pydantic_ai.toolsets import FunctionToolset


class ViewedUrlsMixin(TypedDict):
    viewed_urls: list[str]


async def visit_web_page(ctx: RunContext, url: str):
    """Visit a webpage at the given url and reads its content as markdown string. Use this to browse webpages.

    Args:
        url (str): Url of the webpage to visit
    """
    try:
        crawled = await CRAWLER_SERVICE.crawl_one(url)
        return crawled[0]
    except Exception as e:
        return {"error": str(e)}


async def web_search(
    ctx: RunContext[ViewedUrlsMixin | None],
    query: str,
    date_restrict: Optional[SearchTimeRange] = None,
):
    """Perform a search through many medical sites for a query and return top search results with titles, url and snippet. Use this tool to access up-to-date information from the web or when responding to the user requires information about their location. Some examples of when to use the this tool include:

    - Local Information: weather, local businesses, events.
    - Freshness: if up-to-date information on a topic could change or enhance the answer.
    - Niche Information: detailed info not widely known or understood (found on the internet).
    - Accuracy: if the cost of outdated information is high, use web sources directly.

    This tool only return a snippet of the web page, to get the full content of the web page, use the visit-web-page tool

    Args:
        query (str): Search query to perform e.g. Lyme disease, Bệnh gút
        date_restrict (:obj:`TimeRange`, optional): Restrict the results to the last few days, week, month or year. Must contain the following key:
            - unit (str): one of day, week, month, year
            - num (int): the number of unit to restrict
    """
    try:
        results = await CRAWLER_SERVICE.discover(query, 5, date_restrict)
        if (
            ctx.deps
            and isinstance(ctx.deps, dict)
            and "viewed_urls" in ctx.deps
            and isinstance(ctx.deps["viewed_urls"], list)
        ):
            ctx.deps["viewed_urls"] = [it["url"] for it in results]
        else:
            LOGGER.warn("Wrong dependency type, please check")
        return results
    except Exception as e:
        return {"error": str(e)}


WEB_TOOLSET = FunctionToolset(tools=[web_search, visit_web_page])
