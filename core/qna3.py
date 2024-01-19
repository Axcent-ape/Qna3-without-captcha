import json
import aiohttp
from data import config
from core.utils import web3_utils
from fake_useragent import UserAgent


class Qna3:
    def __init__(self, key: str, proxy: str):
        self.auth_token = self.user_id = None
        self.web3_utils = web3_utils.Web3Utils(key=key, http_provider=config.OPBNB_RPC)
        self.proxy = f"http://{proxy}" if proxy is not None else None

        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'ua-UA,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Host': 'api.qna3.ai',
            'Origin': 'https://qna3.ai',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'TE': 'trailers',
            'User-Agent': UserAgent(os='windows').random,
            'x-lang': 'english',
        }

        self.session = aiohttp.ClientSession(headers=headers, trust_env=True)

    async def login(self):
        address = self.web3_utils.acct.address
        signature = self.web3_utils.get_signed_code("AI + DYOR = Ultimate Answer to Unlock Web3 Universe")

        params = {
            'invite_code': config.REF_CODE,
            'signature': signature,
            'wallet_address': address
        }

        resp = await self.session.post(url='https://api.qna3.ai/api/v2/auth/login?via=wallet', json=params, proxy=self.proxy)
        resp_txt = await resp.json()

        self.auth_token = 'Bearer ' + resp_txt.get('data').get('accessToken')
        self.user_id = resp_txt.get('data').get("user").get("id")

        self.session.headers['Authorization'] = self.auth_token
        self.session.headers['X-Id'] = self.user_id
        return True

    async def claim_points(self, logger, thread):
        if not await self.check_today_claim():
            status, tx_hash = await self.send_claim_tx()
            if status:
                resp_text = await self.send_claim_hash(tx_hash)
                if resp_text == '{"statusCode":422,"message":"user already signed in today"}':
                    logger.warning(
                        f"Поток {thread} | Поинты с андреса {self.web3_utils.acct.address}:{self.web3_utils.acct.key.hex()} уже собраны")
                elif json.loads(resp_text)['statusCode'] != 200:
                    logger.error(
                        f"Поток {thread} | Ошибка при отправке хэша на сайт с адреса {self.web3_utils.acct.address}:{self.web3_utils.acct.key.hex()}: {resp_text}")
                else:
                    logger.success(
                            f"Поток {thread} | Успешно собрал поинты с адреса: {self.web3_utils.acct.address}:{self.web3_utils.acct.key.hex()}")
            else:
                logger.error(f"Поток {thread} | Ошибка при клейме: {tx_hash}")
        else:
            logger.warning(
                f"Поток {thread} | Сегодня уже клеймил поинты: {self.web3_utils.acct.address}:{self.web3_utils.acct.key.hex()}")

    async def check_today_claim(self):
        params = {
            "query": "query loadUserDetail($cursored: CursoredRequestInput!) {\n  userDetail {\n    checkInStatus {\n      checkInDays\n      todayCount\n    }\n    credit\n    creditHistories(cursored: $cursored) {\n      cursorInfo {\n        endCursor\n        hasNextPage\n      }\n      items {\n        claimed\n        extra\n        id\n        score\n        signDay\n        signInId\n        txHash\n        typ\n      }\n      total\n    }\n    invitation {\n      code\n      inviteeCount\n      leftCount\n    }\n    origin {\n      email\n      id\n      internalAddress\n      userWalletAddress\n    }\n    externalCredit\n    voteHistoryOfCurrentActivity {\n      created_at\n      query\n    }\n    ambassadorProgram {\n      bonus\n      claimed\n      family {\n        checkedInUsers\n        totalUsers\n      }\n    }\n  }\n}",
            "variables": {
                "cursored": {
                    "after": "",
                    "first": 20
                },
                "headersMapping": {
                    "Authorization": self.auth_token,
                    "x-id": self.user_id,
                    "x-lang": "english",
                }
            }
        }

        resp = await self.session.post(url='https://api.qna3.ai/api/v2/graphql', json=params, proxy=self.proxy)
        resp_txt = await resp.json()

        return resp_txt.get('data').get('userDetail').get('checkInStatus').get('todayCount')

    async def send_claim_tx(self):
        to = "0xB342e7D33b806544609370271A8D074313B7bc30"
        from_ = self.web3_utils.acct.address
        data = '0xe95a644f0000000000000000000000000000000000000000000000000000000000000001'
        gas_price = self.web3_utils.w3.to_wei('0.00002', 'gwei')
        gas_limit = 35000
        chain_id = 204

        return self.web3_utils.send_data_tx(to=to, from_=from_, data=data, gas_price=gas_price, gas_limit=gas_limit, chain_id=chain_id)

    async def send_claim_hash(self, hash):
        params = {
            'hash': hash,
            'via': 'opbnb'
        }

        resp = await self.session.post(url='https://api.qna3.ai/api/v2/my/check-in', json=params, proxy=self.proxy)
        resp = await resp.text()
        return resp

    async def logout(self):
        await self.session.close()
