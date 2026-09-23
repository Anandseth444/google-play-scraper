import time
from typing import Optional, Union

import requests
import urllib3
from requests.adapters import HTTPAdapter

from google_play_scraper.exceptions import ExtraHTTPError, NotFoundError

MAX_RETRIES = 3
RATE_LIMIT_DELAY = 5
POOL_SIZE = 16

# The store is reached through a TLS-intercepting proxy, so certificates do not verify.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def new_session(proxies: Optional[dict] = None) -> requests.Session:
    """A connection-pooling session. Keep one per proxy and pass it to the scraper
    functions so sockets are reused instead of opened per request."""
    session = requests.Session()
    session.verify = False
    session.proxies = proxies or {}
    adapter = HTTPAdapter(pool_connections=POOL_SIZE, pool_maxsize=POOL_SIZE)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


# Used when the caller supplies no session, so the default path pools too.
_default_session = new_session()


def _send(method: str, url: str, session: Optional[requests.Session], **kwargs) -> str:
    resp = (session or _default_session).request(method, url, **kwargs)

    if resp.status_code == 404:
        raise NotFoundError("App not found(404).")
    if not resp.ok:
        raise ExtraHTTPError(
            "App not found. Status code {} returned.".format(resp.status_code)
        )

    return resp.content.decode("UTF-8")


def post(
    url: str,
    data: Union[str, bytes],
    headers: dict,
    session: Optional[requests.Session] = None,
) -> str:
    last_exception = None
    rate_exceeded_count = 0
    for _ in range(MAX_RETRIES):
        try:
            resp = _send("POST", url, session, data=data, headers=headers)
        except Exception as e:
            last_exception = e
            continue
        if "com.google.play.gateway.proto.PlayGatewayError" in resp:
            rate_exceeded_count += 1
            last_exception = Exception("com.google.play.gateway.proto.PlayGatewayError")
            time.sleep(RATE_LIMIT_DELAY * rate_exceeded_count)
            continue
        return resp
    raise last_exception


def get(
    url: str, timeout: int = None, session: Optional[requests.Session] = None
) -> str:
    return _send("GET", url, session, timeout=timeout)
