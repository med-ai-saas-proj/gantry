from src.services.postgres import PostgresService

import asyncio
import requests
from typing import (
    Callable,
    TypedDict,
    Literal,
    Optional,
    NotRequired,
    AsyncGenerator,
    Iterable,
)
from contextlib import _GeneratorContextManager

from structlog.stdlib import BoundLogger
from pydantic_ai import Agent
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_filter_strategy import (
    PruningContentFilter,
    BM25ContentFilter,
)
from crawl4ai.deep_crawling import DeepCrawlStrategy
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator


class SearchTimeRange(BaseModel):
    num: int
    unit: Literal["day", "week", "month", "year"]


class SearchResult(TypedDict):
    title: str
    link: str
    snippet: str


class CrawlResult(TypedDict):
    url: str
    title: str
    description: str
    content: str
    thumbnail_url: str
    metadata: dict


class DiscoverResult(TypedDict):
    url: str
    title: str
    description: str
    content: str
    thumbnail_url: str


class CrawlerService:
    def __init__(
        self,
        session_scope: Callable[..., _GeneratorContextManager],
        logger: BoundLogger,
        google_search_api_key: str,
        google_search_cx: str,
        max_concurrent_crawler: int = 8,
    ):
        self.logger = logger
        self.postgres_service = PostgresService(session_scope)
        self._search_lock = asyncio.Lock()
        self.google_search_api_key = google_search_api_key
        self.google_search_cx = google_search_cx
        self.max_conncurrent_crawler = max_concurrent_crawler
        self._crawler_semaphore = asyncio.Semaphore(max_concurrent_crawler)

    async def search_google(
        self,
        query: str,
        limit: int = 5,
        time_range: Optional[SearchTimeRange] = None,
    ):
        params = {
            "key": self.google_search_api_key,
            "cx": self.google_search_cx,
            "q": query,
            "num": limit,
        }

        if time_range:
            # Google Custom Search supports dateRestrict in the format: d[number], w[number], m[number], y[number]
            unit_map = {"day": "d", "week": "w", "month": "m", "year": "y"}
            params["dateRestrict"] = (
                f"{unit_map[time_range.unit]}{time_range.num}"
            )

        await self._throttle_search_api()
        response = requests.get(
            "https://www.googleapis.com/customsearch/v1", params=params
        )
        response.raise_for_status()
        items = response.json().get("items", [])

        results: list[SearchResult] = []
        for item in items:
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    link=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                )
            )
        return results

    async def crawl_one(
        self,
        url: str,
        query: Optional[str] = None,
        ignore_links: bool = True,
        ignore_images: bool = True,
        escape_html: bool = False,
        pruned: bool = True,
        deep_crawl_strategy: Optional[DeepCrawlStrategy] = None,
        # BFSDeepCrawlStrategy(max_depth=1, include_external=False, max_pages=50),
        crawler: Optional[AsyncWebCrawler] = None,
    ):
        if pruned:
            if query:
                prune_filter = BM25ContentFilter(
                    user_query=query,
                    bm25_threshold=1.2,
                    language="english",  # use for stemming
                    use_stemming=True,
                )
            else:
                prune_filter = PruningContentFilter(
                    threshold=1.0,
                    threshold_type="fixed",
                    min_word_threshold=10,
                )
        else:
            prune_filter = None
        self.logger.debug("Filter", prune_filter)

        md_generator = DefaultMarkdownGenerator(
            options={
                "ignore_links": ignore_links,
                "ignore_images": ignore_images,
                "escape_html": escape_html,
            },
            content_filter=prune_filter,
        )
        config = CrawlerRunConfig(
            markdown_generator=md_generator,
            exclude_external_links=True,
            exclude_internal_links=True,
            exclude_social_media_links=True,
            deep_crawl_strategy=deep_crawl_strategy,
        )

        if crawler is None:
            async with AsyncWebCrawler() as crawler:
                return await self._run_with_crawler(url, config, crawler)
        return await self._run_with_crawler(url, config, crawler)

    async def crawl_many(
        self,
        urls: Iterable[str],
        query: Optional[str] = None,
        ignore_links: bool = True,
        ignore_images: bool = False,
        escape_html: bool = False,
        pruned: bool = True,
        deep_crawl_strategy: Optional[DeepCrawlStrategy] = None,
    ) -> list[CrawlResult]:
        """Crawl a list of URLs and extract markdown and a preview image.

        Applies the same configuration to all URLs. Internally delegates
        each URL to ``crawl_one`` and reuses a single crawler for efficiency.

        Args:
            urls: Iterable of absolute URLs to crawl.
            query: User's query, used for pruning.
            ignore_links: Whether to omit links in generated markdown.
            ignore_images: Whether to omit images in generated markdown.
            escape_html: Whether to escape HTML in generated markdown.
            pruned: Whether to enable the pruning content filter.
            deep_crawl_strategy: Strategy to use when deep crawling.

        Returns:
            List of dicts (one per URL) with keys: 'url', 'title',
            'description', 'content', and 'image_url'.
        """
        async with AsyncWebCrawler() as crawler:
            tasks = [
                self.crawl_one(
                    url=url,
                    query=query,
                    ignore_links=ignore_links,
                    ignore_images=ignore_images,
                    escape_html=escape_html,
                    pruned=pruned,
                    deep_crawl_strategy=deep_crawl_strategy,
                    crawler=crawler,
                )
                for url in urls
            ]
            per_url_lists = await asyncio.gather(*tasks)
            # Flatten list[list[CrawlResult]] -> list[CrawlResult]
            flattened: list[CrawlResult] = [
                item for sublist in per_url_lists for item in sublist
            ]
            return flattened

    async def discover(
        self,
        query: str,
        limit: int = 5,
        time_range: Optional[SearchTimeRange] = None,
        pruned: bool = True,
        ignore_links: bool = True,
        ignore_images: bool = False,
        escape_html: bool = False,
    ) -> list[DiscoverResult]:
        """Search the web, then crawl results to enrich content.

        Args:
            query: Search query string.
            count: Max number of results to return.
        """
        search_results = await self.search_google(
            query=query, limit=limit, time_range=time_range
        )
        # Crawl URLs and merge content into results by URL
        crawled = await self.crawl_many(
            (r["link"] for r in search_results),
            pruned=pruned,
            ignore_links=ignore_links,
            ignore_images=ignore_images,
            escape_html=escape_html,
        )
        data_by_url = {item.get("url"): item for item in crawled}
        results: list[DiscoverResult] = []
        for r in search_results:
            data = data_by_url.get(r["link"]) or {}
            results.append(
                {
                    "url": data.get("url", ""),
                    "title": data.get("title", ""),
                    "description": data.get("description", ""),
                    "content": data.get("content", ""),
                    "thumbnail_url": data.get("thumbnail_url", ""),
                }
            )

        return results

    async def _run_with_crawler(
        self,
        url: str,
        crawler_config: CrawlerRunConfig,
        active_crawler: AsyncWebCrawler,
    ) -> list[CrawlResult]:
        async with self._crawler_semaphore:
            crawl_result = await active_crawler.arun(
                url=url,
                crawler_config=crawler_config,
            )
            # Normalize to a list of underlying results when deep crawl
            if isinstance(crawl_result, AsyncGenerator):
                underlying_results = []
                async for i in crawl_result:
                    underlying_results.append(i)
            else:
                underlying_results = crawl_result

            normalized: list[CrawlResult] = []
            for r in underlying_results:
                if getattr(r, "success", False):
                    fit_markdown = str(r.markdown.fit_markdown)
                    content = (
                        fit_markdown
                        if len(fit_markdown.replace("\n", "").strip()) > 1
                        else str(r.markdown.raw_markdown)
                    )
                    metadata = getattr(r, "metadata", {}) or {}
                    thumbnail_url = (
                        metadata.get(
                            "og:image",
                            metadata.get("twitter:image", ""),
                        )
                        or ""
                    )
                    title = (
                        metadata.get(
                            "title",
                            metadata.get(
                                "og:title",
                                metadata.get("twitter:title", ""),
                            ),
                        )
                        or ""
                    )
                    description = (
                        metadata.get(
                            "description",
                            metadata.get(
                                "og:description",
                                metadata.get("twitter:description", ""),
                            ),
                        )
                        or ""
                    )
                    page_url = getattr(r, "url") or url
                    self.logger.debug(
                        "Crawl success",
                        url=page_url,
                        title=title,
                        description=description,
                    )

                    normalized.append(
                        {
                            "url": page_url,
                            "title": title,
                            "description": description,
                            "content": content,
                            "thumbnail_url": thumbnail_url,
                            "metadata": metadata,
                        }
                    )

        return normalized

    async def _throttle_search_api(self):
        pass
