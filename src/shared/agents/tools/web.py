"""Web browsing tools for agents."""
from src.shared.utils.logger import LOGGER
from src.shared.agents.factories import getAgentManager
from src.service.crawler.services import SearchTimeRange
from src.service.crawler.initialize import getCrawlerService
from src.shared.agents.agent_manager import (
    ToolsetConstructorContext,
)

from typing import Optional, TypedDict

from pydantic_ai import RunContext
from pydantic_ai.toolsets import FunctionToolset


crawler_service = getCrawlerService()

class ViewedUrlsMixin(TypedDict):
    viewed_urls: list[str]


async def visit_web_page(ctx: RunContext, url: str, query: str | None = None):
    try:
        crawled = await crawler_service.crawl_one(url, query=query)
        return crawled[0]
    except Exception as e:
        return {"error": str(e)}


async def web_search(
    ctx: RunContext[ViewedUrlsMixin | None],
    query: str,
    date_restrict: Optional[SearchTimeRange] = None,
):
    """Perform a web search using the given query and optional date restriction."""
    try:
        results = await crawler_service.discover(query, 5, date_restrict)
        LOGGER.debug("Done crawling")
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

def make_web_search_tool(
    name: str,
    doc_string: str
):
    """Creates a web search tool with the given name and documentation string."""
    async def tool(
        ctx: RunContext[ViewedUrlsMixin | None],
        query: str,
        date_restrict: Optional[SearchTimeRange] = None,
    ):
        return await web_search(ctx, query, date_restrict)

    tool.__name__ = name
    tool.__doc__ = doc_string
    return tool

def make_visit_web_page_tool(
    name: str,
    doc_string: str
):
    """Creates a visit web page tool with the given name and documentation string."""
    async def tool(
        ctx: RunContext,
        url: str,
        query: str | None = None,
    ):
        return await visit_web_page(ctx, url, query)

    tool.__name__ = name
    tool.__doc__ = doc_string
    return tool

WEB_TOOLSET_NAME = "web_tool"

WEB_SEARCH_TOOL_PROMPT_ID = "toolset_web_search_tool_prompt"
VISIT_WEB_PAGE_TOOL_PROMPT_ID = "toolset_visit_web_page_tool_prompt"

agent_manager = getAgentManager()

agent_manager.register_prompt(
    WEB_SEARCH_TOOL_PROMPT_ID,
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
)

agent_manager.register_prompt(
    VISIT_WEB_PAGE_TOOL_PROMPT_ID,
"""Visit a webpage at the given url and reads its content.

Use this to browse webpages.

Args:
    url (str): Url of the webpage to visit
    query (str, optional): Optional search query to provide context for the visit. When provided, the crawler may prioritize or extract content related to this query. Defaults to None.
"""
)

def web_toolset_constructor(
    ctx: ToolsetConstructorContext
) -> FunctionToolset:
    web_search_prompt = ctx.use_prompt(WEB_SEARCH_TOOL_PROMPT_ID)
    visit_web_page_prompt = ctx.use_prompt(VISIT_WEB_PAGE_TOOL_PROMPT_ID)
    return FunctionToolset(tools=[
        make_web_search_tool(
            name="web_search_tool",
            doc_string=web_search_prompt,
        ),
        make_visit_web_page_tool(
            name="visit_web_page_tool",
            doc_string=visit_web_page_prompt,
        )
    ])

agent_manager.register_toolset(
    WEB_TOOLSET_NAME,
    web_toolset_constructor
)
