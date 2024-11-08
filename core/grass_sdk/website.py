import json
import aiohttp
from tenacity import retry, stop_after_attempt, wait_random, retry_if_not_exception_type
from core.utils import logger
from core.utils.exception import LoginException, ProxyBlockedException
from core.utils.session import BaseClient

class GrassRest(BaseClient):
    def __init__(self, email: str, password: str, user_agent: str = None, proxy: str = None):
        super().__init__(user_agent, proxy)
        self.email = email
        self.password = password

        self.id = None

    async def enter_account(self):
        res_json = await self.handle_login()
        self.website_headers['Authorization'] = res_json['result']['data']['accessToken']

        return res_json['result']['data']['userId']

    async def get_points_handler(self):
        handler = retry(
            stop=stop_after_attempt(3),
            before_sleep=lambda retry_state, **kwargs: logger.info(f"{self.id} | Retrying to get points... "
                                                                   f"Continue..."),
            wait=wait_random(5, 7),
            reraise=True
        )

        return await handler(self.get_points)()

    async def get_points(self):
        url = 'https://api.getgrass.io/users/earnings/epochs'

        response = await self.session.get(url, headers=self.website_headers, proxy=self.proxy)

        logger.debug(f"{self.id} | Get Points response: {await response.text()}")

        res_json = await response.json()
        points = res_json.get('data', {}).get('epochEarnings', [{}])[0].get('totalCumulativePoints')

        if points is not None:
            return points
        elif points := res_json.get('error', {}).get('message'):
            return points
        else:
            return "Can't get points."

    async def handle_login(self):
        handler = retry(
            stop=stop_after_attempt(12),
            retry=retry_if_not_exception_type((LoginException, ProxyBlockedException)),
            before_sleep=lambda retry_state, **kwargs: logger.info(f"{self.id} | Login retrying... "
                                                                   f"{retry_state.outcome.exception()}"),
            wait=wait_random(8, 12),
            reraise=True
        )

        return await handler(self.login)()

    async def login(self):
        url = 'https://api.getgrass.io/login'

        json_data = {
            'password': self.password,
            'username': self.email,
        }

        response = await self.session.post(url, headers=self.website_headers, data=json.dumps(json_data),
                                           proxy=self.proxy)
        logger.debug(f"{self.id} | Login response: {await response.text()}")

        res_json = await response.json()
        if res_json.get("error") is not None:
            raise LoginException(f"Login stopped: {res_json['error']['message']}")

        if response.status == 403:
            raise ProxyBlockedException(f"Login response: {await response.text()}")
        if response.status != 200:
            raise aiohttp.ClientConnectionError(f"Login response: | {await response.text()}")

        return await response.json()

    async def get_devices_info(self):
        url = 'https://api.getgrass.io/extension/user-score'

        response = await self.session.get(url, headers=self.website_headers, proxy=self.proxy)
        return await response.json()

    async def get_proxy_score_by_device_id_handler(self):
        handler = retry(
            stop=stop_after_attempt(3),
            before_sleep=lambda retry_state, **kwargs: logger.info(f"{self.id} | Retrying to get proxy score... "
                                                                   f"Continue..."),
            reraise=True
        )

        return await handler(self.get_proxy_score_by_device_id)()

    async def get_proxy_score_by_device_id(self):
        res_json = await self.get_devices_info()

        if not (isinstance(res_json, dict) and res_json.get("data", None) is not None):
            return

        devices = res_json['data']['currentDeviceData']
        await self.update_ip()

        return next((device['final_score'] for device in devices
                     if device['device_ip'] == self.ip), None)

    async def update_ip(self):
        self.ip = await self.get_ip()

    async def get_ip(self):
        return await (await self.session.get('https://api.ipify.org', proxy=self.proxy)).text()
