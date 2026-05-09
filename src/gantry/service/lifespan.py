from gantry.service.rag.factories import getRagService

import asyncio


async def rag_embedding_proccess_loop():
    rag_service = getRagService()
    await rag_service.processEmbeddingTask()


async def startup():
    rag_service = getRagService()
    await rag_service.createBucket()
    asyncio.create_task(rag_embedding_proccess_loop())
    pass


async def shutdown():
    # Cleanup code here
    pass
