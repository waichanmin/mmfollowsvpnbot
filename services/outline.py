from __future__ import annotations

import hashlib
import logging
import ssl
from dataclasses import dataclass
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class OutlineAPIError(Exception):
    pass


@dataclass(slots=True)
class OutlineKey:
    key_id: str
    access_url: str
    name: str


class OutlineService:
    def __init__(self, api_url: str, cert_sha256: str) -> None:
        self.api_url = api_url.rstrip('/')
        self.cert_sha256 = cert_sha256.lower().replace(':', '')

    @property
    def enabled(self) -> bool:
        return bool(self.api_url and self.cert_sha256)

    def _ssl_context(self) -> ssl.SSLContext:
        context = ssl.create_default_context()

        def verify_cb(connection: ssl.SSLSocket, x509: Any, errno: int, depth: int, preverify_ok: bool) -> bool:
            return preverify_ok

        context.check_hostname = False
        context.verify_mode = ssl.CERT_REQUIRED
        return context

    async def _check_cert_fingerprint(self, response: aiohttp.ClientResponse) -> None:
        ssl_obj = response.connection.transport.get_extra_info('ssl_object')
        if ssl_obj is None:
            raise OutlineAPIError('Missing SSL object while validating Outline certificate')
        der_cert = ssl_obj.getpeercert(binary_form=True)
        fingerprint = hashlib.sha256(der_cert).hexdigest().lower()
        if fingerprint != self.cert_sha256:
            raise OutlineAPIError('Outline certificate fingerprint mismatch')

    async def create_access_key(self, key_name: str) -> OutlineKey:
        if not self.enabled:
            raise OutlineAPIError('Outline integration is not configured')

        create_url = f'{self.api_url}/access-keys'
        rename_url_template = f'{self.api_url}/access-keys/{{key_id}}/name'

        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.post(create_url, ssl=self._ssl_context()) as response:
                    await self._check_cert_fingerprint(response)
                    if response.status >= 400:
                        text = await response.text()
                        raise OutlineAPIError(f'Outline create key failed: {response.status} {text}')
                    payload = await response.json()

                key_id = str(payload['id'])
                access_url = str(payload['accessUrl'])

                async with session.put(
                    rename_url_template.format(key_id=key_id),
                    json={'name': key_name},
                    ssl=self._ssl_context(),
                ) as response:
                    await self._check_cert_fingerprint(response)
                    if response.status >= 400:
                        text = await response.text()
                        logger.warning('Outline key created but rename failed: %s %s', response.status, text)

                return OutlineKey(key_id=key_id, access_url=access_url, name=key_name)
            except aiohttp.ClientError as exc:
                logger.exception('Network error while creating Outline key')
                raise OutlineAPIError('Network error while talking to Outline server') from exc

    async def delete_access_key(self, key_id: str) -> None:
        if not self.enabled:
            return
        delete_url = f'{self.api_url}/access-keys/{key_id}'
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.delete(delete_url, ssl=self._ssl_context()) as response:
                    await self._check_cert_fingerprint(response)
                    if response.status >= 400:
                        text = await response.text()
                        logger.warning('Failed to delete Outline key %s: %s %s', key_id, response.status, text)
            except Exception:
                logger.exception('Failed to cleanup Outline key %s', key_id)
