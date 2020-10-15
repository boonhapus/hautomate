import asyncio
import logging
import json

import websockets
import httpx


_log = logging.getLogger(__name__)


class HassWebConnector:

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop=None,
        host: str=None,
        port: int=None,
        access_token: str=None,
    ):
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        self.loop = loop
        self._host = host
        self._port = port
        self._access_token = access_token
        self._ws = None
        self._ws_interaction_id = 0
        self._ws_responses = {}
        self._http = httpx.AsyncClient(headers=headers)

    @property
    def ws_uri(self) -> str:
        """
        """
        return f'ws://{self._host}:{self._port}/api/websocket'

    @property
    def base_url(self) -> str:
        """
        """
        return f'http://{self._host}:{self._port}/api'

    def _next_ws_interaction_id(self):
        """
        Increment the interaction ID.

        Further reading:
            /docs/external_api_websocket/#message-format
        """
        self._ws_interaction_id += 1
        return self._ws_interaction_id

    async def _ws_auth_flow(self):
        """
        Go through the authorization flow.

        Further reading:
          /docs/external_api_websocket/#authentication-phase
        """
        self._ws = await websockets.connect(self.ws_uri)
        await self._ws_auth_flow()

        _log.info('authenticating with Home Assistant')
        msg = await self._ws.recv()
        msg = json.loads(msg)

        if msg['type'] == 'auth_required':
            await self._ws.send(json.dumps({
                'type': 'auth',
                'access_token': self._access_token
            }))
            msg = await self._ws.recv()
            msg = json.loads(msg)

        if msg['type'] == 'auth_ok':
            _log.info('authenticated with Home Assistant')

        if msg['type'] == 'auth_invalid':
            err = msg['message']
            raise ValueError(f'AUTHORIZATION INVALID: {err}')

    async def call_service(
        self,
        domain,
        service,
        service_data,
        # blocking=False,
        # limit=10
    ):
        interaction_id = self._next_ws_interaction_id()

        await self._ws.send(json.dumps({
            'id': interaction_id,
            'type': 'call_service',
            'domain': domain,
            'service': service,
            'service_data': service_data
        }))

        # if not blocking:
        #     return None

        # self._ws_responses[interaction_id] = fut = self.loop.create_future()

        # try:
        #     await asyncio.wait({fut}, timeout=limit)
        # except asyncio.TimeoutError:
        #     r = False

        # return r

    async def fire_event(self, event_type, event_data):
        """
        """
        await self._http.post(f'/api/events/{event_type}', json=event_data)
