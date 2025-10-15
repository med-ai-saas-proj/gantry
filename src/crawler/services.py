from src.db.postgres.service import PostgresService

import asyncio
from typing import (
    Literal,
    Callable,
    Iterable,
    Optional,
    TypedDict,
    AsyncGenerator,
)
from contextlib import _GeneratorContextManager

import requests
from crawl4ai import BrowserConfig, AsyncWebCrawler, CrawlerRunConfig
from pydantic import BaseModel
from structlog.stdlib import BoundLogger
from crawl4ai.deep_crawling import DeepCrawlStrategy, BFSDeepCrawlStrategy
from crawl4ai.content_filter_strategy import (
    BM25ContentFilter,
    PruningContentFilter,
)
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
        self.excluded_selector = ",".join(
            [
                "footer",
                '[role="banner"]',
                '[role="navigation"]',
                '[role="complementary"]',
                ".nav",
                ".navbar",
                ".navigation",
                ".sidebar",
                ".footer",
                ".header",
                ".advertisement",
                ".ads",
                ".social-share",
                ".cookie-notice",
            ]
        )

    async def search_google(
        self,
        query: str,
        limit: int = 5,
        time_restrict: Optional[SearchTimeRange] = None,
    ):
        if limit > 10 or limit < 1:
            self.logger.error(
                "Search limit out of range", query=query, limit=limit
            )
            raise RuntimeError(
                f"Failed to search for {query}, limit should be < 10 and > 0"
            )

        params = {
            "key": self.google_search_api_key,
            "cx": self.google_search_cx,
            "q": query,
            "num": limit,
        }

        if time_restrict:
            # Google Custom Search supports dateRestrict in the format: d[number], w[number], m[number], y[number]
            unit_map = {"day": "d", "week": "w", "month": "m", "year": "y"}
            params["dateRestrict"] = (
                f"{unit_map[time_restrict.unit]}{time_restrict.num}"
            )

        await self._throttle_search_api()
        response = requests.get(
            "https://www.googleapis.com/customsearch/v1", params=params
        )
        if not response.ok:
            self.logger.error(
                "Failed to search",
                query=query,
            )
            raise RuntimeError(f"Failed to search for {query}")

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
                    bm25_threshold=1.4,
                    language="english",  # use for stemming
                    use_stemming=True,
                )
            else:
                prune_filter = PruningContentFilter(
                    threshold=0.4,
                    threshold_type="fixed",
                    min_word_threshold=10,
                )
        else:
            prune_filter = None
        self.logger.debug("Filter", filter=prune_filter)

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
            excluded_selector=self.excluded_selector,
            remove_forms=True,
            deep_crawl_strategy=deep_crawl_strategy,
        )

        try:
            if crawler is None:
                async with AsyncWebCrawler(
                    config=BrowserConfig(
                        enable_stealth=True,  # Simple flag to enable
                        headless=False,  # Better for avoiding detection
                    )
                ) as crawler:
                    return await self._run_with_crawler(url, config, crawler)
            return await self._run_with_crawler(url, config, crawler)
        except Exception as e:
            self.logger.error("Crawl error", url=url, error=str(e))

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
                item for sublist in per_url_lists for item in (sublist or [])
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
            query=query, limit=limit, time_restrict=time_range
        )
        # Crawl URLs and merge content into results by URL
        crawled = await self.crawl_many(
            (r["link"] for r in search_results),
            query=query,
            pruned=pruned,
            ignore_links=ignore_links,
            ignore_images=ignore_images,
            escape_html=escape_html,
            deep_crawl_strategy=BFSDeepCrawlStrategy(max_depth=1, max_pages=20),
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
                    page_url = r.url or url
                    self.logger.debug(
                        "Crawl success",
                        url=page_url,
                        title=title,
                        description=description,
                    )

                    fit_markdown = str(r.markdown.fit_markdown)
                    if fit_markdown.replace("\n", "").strip():
                        content = fit_markdown
                    else:
                        self.logger.info(
                            f"Cannot generate fit markdown for {page_url}, used raw_markdown"
                        )
                        content = str(r.markdown.raw_markdown)

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
        # Acquire the lock to ensure only one search API call at a time
        async with self._search_lock:
            # Optionally, add a delay here if stricter rate limiting is needed
            await asyncio.sleep(0.02)  # 20ms delay between requests
