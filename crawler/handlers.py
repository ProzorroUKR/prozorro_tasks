import asyncio


async def data_handler(session, items, handlers=None):
    await asyncio.gather(*(
        handler(item)
        for handler in handlers
        for item in items
    ))
