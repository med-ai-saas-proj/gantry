"""Web browsing tools for agents."""

from src.shared.utils.logger import LOGGER
from src.service.crawler.services import SearchTimeRange
from src.service.crawler.initialize import getCrawlerService
from src.shared.agents.agent_manager import (
    ToolsetConstructorContext,
)
from src.shared.agents.agent_manager_factories import getAgentManager

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


def make_web_search_tool(name: str, doc_string: str):
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


def make_visit_web_page_tool(name: str, doc_string: str):
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

def web_toolset_constructor(ctx: ToolsetConstructorContext) -> FunctionToolset:
    web_search_prompt = ctx.use_prompt(WEB_SEARCH_TOOL_PROMPT_ID)
    visit_web_page_prompt = ctx.use_prompt(VISIT_WEB_PAGE_TOOL_PROMPT_ID)
    return FunctionToolset(
        tools=[
            make_web_search_tool(
                name="web_search_tool",
                doc_string=web_search_prompt,
            ),
            make_visit_web_page_tool(
                name="visit_web_page_tool",
                doc_string=visit_web_page_prompt,
            ),
        ]
    )


agent_manager.register_toolset(WEB_TOOLSET_NAME, web_toolset_constructor)
