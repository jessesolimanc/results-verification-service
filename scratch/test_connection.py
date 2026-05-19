import asyncio
import asyncpg

async def test():
    conn = await asyncpg.connect("postgresql://postgres:FiLh4iAV8OWc7w5e+YvNvK3uhIWdN6cCce2oRjAxbE8=@localhost:5432/countablelabs")
    print("Connected successfully")
    await conn.close()

asyncio.run(test())