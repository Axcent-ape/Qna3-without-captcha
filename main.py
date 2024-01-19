import random
from core.qna3 import Qna3
from core.utils import random_line, logger
import asyncio


async def QNA(thread):
    logger.info(f"Поток {thread} | Начал работу")
    while True:
        act = await random_line('data/private_keys.txt')
        if not act: break

        if '::' in act:
            private_key, proxy = act.split('::')
        else:
            private_key = act
            proxy = None

        qna = Qna3(key=private_key, proxy=proxy)

        if await qna.login():
            if await qna.check_today_claim():
                logger.warning(f"Поток {thread} | Поинты с андреса {qna.web3_utils.acct.address}:{qna.web3_utils.acct.key.hex()} уже собраны")
                await sleep(thread)
                continue

            await qna.claim_points(logger=logger, thread=thread)
        await qna.logout()
        await sleep(thread)


async def sleep(thread):
    rt = random.randint(50, 60)
    logger.info(f"Поток {thread} | Спит {rt} c.")

    await asyncio.sleep(rt)


async def main():
    print("Автор софта: https://t.me/ApeCryptor")

    thread_count = int(input("Введите кол-во потоков: "))
    # thread_count = 1
    tasks = []
    for thread in range(1, thread_count+1):
        tasks.append(asyncio.create_task(QNA(thread)))

    await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
