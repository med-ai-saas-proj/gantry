from gantry.service.utils.rag.factories import getRagService


async def rag_embedding_proccess_loop():
    rag_service = getRagService()
    await rag_service.processEmbeddingTask()


async def startup():
    rag_service = getRagService()
    await rag_service.createBucket()
    pass


async def shutdown():
    # Cleanup code here
    pass
