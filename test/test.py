import asyncio
import time

async def task(name, delay):
    t0 = time.perf_counter()
    await asyncio.sleep(delay)
    t1 = time.perf_counter()
    print(f"{name} 自身耗时: {t1 - t0:.3f} 秒")

async def main():
    start = time.perf_counter()
    await asyncio.gather(
        task("A", 2),
        task("B", 1),
        task("C", 3),
    )
    end = time.perf_counter()
    print(f"总耗时: {end - start:.3f} 秒")

# async def main():
#     start = time.perf_counter()
#     await task("A", 2)
#     await task("B", 1)
#     await task("C", 3)
#     print(f"总耗时: {time.perf_counter() - start:.3f} 秒")

asyncio.run(main())