import asyncio
import ctypes
import random
import sys
import traceback

from art import text2art
from termcolor import colored, cprint

from better_proxy import Proxy

from core import Grass
from core.autoreger import AutoReger
from core.utils import logger, file_to_list
from core.utils.accounts_db import AccountsDB
from core.utils.exception import LoginException
from data.config import ACCOUNTS_FILE_PATH, PROXIES_FILE_PATH, WALLETS_FILE_PATH


def bot_info(name: str = ""):
    cprint(text2art(name), 'green')

    if sys.platform == 'win32':
        ctypes.windll.kernel32.SetConsoleTitleW(f"{name}")

    print(
        f"{colored('EnJoYeR <crypto/> moves:', color='light_yellow')} "
        f"{colored('https://t.me/+tdC-PXRzhnczNDli', color='light_green')}"
    )


async def worker_task(_id, account: str, proxy: str = None, wallet: str = None, db: AccountsDB = None):
    consumables = account.split(":")[:3]
    email, password = consumables
    grass = None

    try:
        grass = Grass(_id, email, password, proxy, db)
        await asyncio.sleep(random.uniform(1, 2) * _id)
        logger.info(f"Starting №{_id} | {email} | {password} | {proxy}")
        await grass.start()

        return True
    except LoginException as e:
        logger.warning(f"{_id} | {e}")
    # except NoProxiesException as e:
    #     logger.warning(e)
    except Exception as e:
        logger.error(f"{_id} | not handled exception | error: {e} {traceback.format_exc()}")
    finally:
        if grass:
            await grass.session.close()


async def main():
    ## Just add proxies to DB
    accounts = file_to_list(ACCOUNTS_FILE_PATH)

    if not accounts:
        logger.warning("No accounts found!")
        return

    proxies = [Proxy.from_str(proxy).as_url for proxy in file_to_list(PROXIES_FILE_PATH)]

    db = AccountsDB('data/proxies_stats.db')
    await db.connect()

    for i, account in enumerate(accounts):
        account = account.split(":")[0]
        proxy = proxies[i] if len(proxies) > i else None

        if await db.proxies_exist(proxy) or not proxy:
            continue

        await db.add_account(account, proxy)

    '''
    network_index = -1
    for i, account in enumerate(accounts):
        account_line = account.split(":")
        account = account_line[0]
        networks_limit = int(account_line[2]) if len(account_line) > 2 else 1

        logger.info(f"Start account: {account} | networks = {networks_limit}")

        for n in range(1, networks_limit + 1):
            network_index = network_index + 1
            proxy = proxies[network_index] if len(proxies) > i else None

            if await db.proxies_exist(proxy) or not proxy:
                continue

            await db.add_account(account, proxy)

    logger.info(f"network_index = {network_index}")

    threads_from_network_index = network_index + 1
    '''

    await db.delete_all_from_extra_proxies()
    await db.push_extra_proxies(proxies[len(accounts):])
    # await db.push_extra_proxies(proxies[threads_from_network_index:])

    ## Init AutoReger - some kind of accounts handler
    autoreger = AutoReger.get_accounts(
        (ACCOUNTS_FILE_PATH, PROXIES_FILE_PATH, WALLETS_FILE_PATH),
        with_id=True,
        static_extra=(db, )
    )
    threads = len(autoreger.accounts)

    logger.info("__MINING__ MODE")
    # logger.info(f"threads = {threads}")

    ## Init & start main work cycle
    await autoreger.start(worker_task, threads)

    await db.close_connection()


if __name__ == "__main__":
    bot_info("GRASS_AUTO")

    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    else:
        asyncio.run(main())
