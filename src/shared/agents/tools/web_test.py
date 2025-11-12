from . import web

import unittest

from pydantic_ai import RunUsage, RunContext, ModelResponse
from pydantic_ai.models.function import FunctionModel


def create_run_context[T](deps: T) -> RunContext[T]:
    return RunContext[T](
        deps=deps,
        model=FunctionModel(lambda *args, **kwargs: ModelResponse([])),
        usage=RunUsage(),
    )


class TestVisitWebPageTool(unittest.IsolatedAsyncioTestCase):
    async def test_0(self):
        result = await web.visit_web_page(
            create_run_context(None),
            "https://www.sciencedirect.com/science/article/pii/S2452109425001204",
            "bladder stone",
        )
        print(result)

    async def test_1(self):
        result = await web.visit_web_page(
            create_run_context(None),
            "https://www.sciencedirect.com/science/article/pii/S2452109425001204",
        )
        print(result)


class TestVisitWebSearchTool(unittest.IsolatedAsyncioTestCase):
    async def test_0(self):
        result = await web.web_search(create_run_context(None), "bladder stone")
        print(result)


if __name__ == "__main__":
    unittest.main()
