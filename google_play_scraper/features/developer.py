import json
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests

from google_play_scraper.constants.element import ElementSpecs
from google_play_scraper.constants.regex import Regex
from google_play_scraper.constants.request import Formats, PLAY_STORE_BASE_URL
from google_play_scraper.utils.request import get, post
from google_play_scraper.exceptions import NotFoundError

# A developer page embeds only its first ~20 apps; the rest load from the batchexecute RPC
# the store UI calls on scroll, one token-linked page at a time. Request shape follows
# facundoolano/google-play-scraper (lib/utils/processPages.js).
CLUSTER_URL = PLAY_STORE_BASE_URL + "/_/PlayStoreUi/data/batchexecute?rpcids=qnKhOb&hl={lang}&gl={country}"  # noqa: E501
CLUSTER_RPC_ID = "qnKhOb"
CLUSTER_PAGE_SIZE = 100
# Opaque field mask the store UI sends with every cluster request.
CLUSTER_FIELD_MASK = [96, 27, 4, 8, 57, 30, 110, 79, 11, 16, 49, 1, 3, 9, 12, 104, 55, 56, 51, 10, 34, 77]  # noqa: E501
# Only reached if Google ever hands back an endless token chain.
MAX_CLUSTER_PAGES = 50


def _cluster_body(token: str) -> bytes:
    inner = [[None, [[10, [10, CLUSTER_PAGE_SIZE]], True, None, CLUSTER_FIELD_MASK], None, token]]
    payload = [[[CLUSTER_RPC_ID, json.dumps(inner, separators=(",", ":")), None, "generic"]]]
    return ("f.req=" + quote(json.dumps(payload, separators=(",", ":")), safe="")).encode()


def _cluster_page(
    token: str, lang: str, country: str, session: Optional[requests.Session]
) -> Tuple[List[str], Optional[str]]:
    """One continuation page of a developer's apps, as (app_ids, next_token)."""
    dom = post(
        CLUSTER_URL.format(lang=lang, country=country),
        _cluster_body(token),
        {"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
        session=session,
    )
    cluster = json.loads(Regex.REVIEWS.findall(dom)[0])[0][2]
    if not cluster:
        return [], None

    cluster = json.loads(cluster)[0][0]
    app_ids = [entry[12][0] for entry in cluster[0]]
    next_token = cluster[7][1] if len(cluster) > 7 and cluster[7] else None
    return app_ids, next_token


def _all_apps(
    first_page: List[str],
    token: Optional[str],
    lang: str,
    country: str,
    session: Optional[requests.Session],
) -> List[str]:
    apps = list(first_page)
    for _ in range(MAX_CLUSTER_PAGES):
        if not token:
            break
        try:
            page, token = _cluster_page(token, lang, country, session)
        except Exception:
            # A changed payload shape should cost us the extra pages, not the whole listing.
            break
        if not page:
            break
        apps.extend(page)
    return list(dict.fromkeys(apps))


def developer(
    developer_token: str,
    lang: str = "en",
    country: str = "us",
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    url = Formats.Developer.build(developer_token, lang=lang, country=country)

    try:
        dom = get(url, session=session)
    except NotFoundError:
        url = Formats.Developer.fallback_build(developer_token, lang=lang)
        dom = get(url, session=session)

    matches = Regex.SCRIPT.findall(dom)

    dataset = {}

    for match in matches:
        key_match = Regex.KEY.findall(match)
        value_match = Regex.VALUE.findall(match)

        if key_match and value_match:
            key = key_match[0]
            value = json.loads(value_match[0])

            dataset[key] = value

    result = {}

    for k, spec in ElementSpecs.Developer.items():
        if isinstance(spec, list):
            for sub_spec in spec:
                content = sub_spec.extract_content(dataset)

                if content is not None:
                    result[k] = content
                    break
        else:
            result[k] = spec.extract_content(dataset)

    first_page = (result["apps"] or []) + (result.pop("apps2") or [])

    result["apps"] = _all_apps(
        first_page, result.pop("token", None), lang, country, session
    )
    result["url"] = url

    return result
