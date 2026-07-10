#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lark_common.py — 飞书 Lark Open API 的共享凭证与请求内核。

read_doc.py（读)与 publish_to_lark_doc.py（写)共用同一套凭证与请求逻辑,
避免两份拷贝漂移("读能用、写坏了"的老病根,见 DESIGN §11.2)。

凭证优先级:环境变量 LARK_APP_ID / LARK_APP_SECRET / LARK_DOMAIN
          → 缺失则拉公司 config 服务 skill-config.giggletools.com(需 VPN)。
不依赖 giggle-common gateway / CF Access 登录。

注意:config 返回的 LARK_DOMAIN 是 open.feishu.cn(国内站),与目标 larksuite.com
(国际站)是同一租户的两个接入域名、数据互通(见 references/lark-output.md)。
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

CONFIG_URL = "https://skill-config.giggletools.com/api/config"
DEFAULT_DOMAIN = "https://open.feishu.cn"


def load_credentials() -> tuple[str, str, str]:
    """返回 (app_id, app_secret, domain)。环境变量优先,否则拉 config 服务。"""
    app_id = os.environ.get("LARK_APP_ID", "").strip()
    app_secret = os.environ.get("LARK_APP_SECRET", "").strip()
    domain = os.environ.get("LARK_DOMAIN", "").strip()
    if app_id and app_secret:
        return app_id, app_secret, domain or DEFAULT_DOMAIN
    cfg = None
    for attempt in range(3):  # config 服务同样受 DNS 瞬断影响,重试 3 次
        try:
            req = urllib.request.Request(CONFIG_URL, headers={"User-Agent": "curl/8.4.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                cfg = json.loads(r.read().decode("utf-8"))
            break
        except (urllib.error.URLError, OSError):
            if attempt == 2:
                raise
            time.sleep(1.5 * (attempt + 1))
    return (
        cfg.get("LARK_APP_ID", ""),
        cfg.get("LARK_APP_SECRET", ""),
        cfg.get("LARK_DOMAIN", DEFAULT_DOMAIN),
    )


def http(url, method="GET", payload=None, headers=None, raw=False, timeout=60,
         retries=3, retry_wait=1.5):
    """底层 HTTP:返回 (status, body_or_json, headers)。raw=True 返回 bytes(下载图片用)。
    非 200 与网络错误都不抛,交调用方判 code / status。

    网络层错误(DNS 抖动/连接失败/读超时,即 URLError/OSError)自动重试 retries 次,
    间隔 retry_wait 秒递增退避——实测 DNS 瞬断会打断 token/blocks/发布任一环节,
    统一在这里兜底,所有调用方(read_doc / publish / tenant_token)自动受益。
    HTTP 状态错误(4xx/5xx,服务端已应答)不在此重试,语义交调用方处理。"""
    h = {"Content-Type": "application/json; charset=utf-8"}
    if headers:
        h.update(headers)
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    attempts = max(1, int(retries))
    for attempt in range(attempts):
        req = urllib.request.Request(url, data=data, headers=h, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                if raw:
                    return r.status, body, dict(r.headers)
                return r.status, json.loads(body.decode("utf-8")), None
        except urllib.error.HTTPError as e:
            b = e.read()
            if raw:
                return e.code, b, dict(e.headers)
            try:
                return e.code, json.loads(b.decode("utf-8")), None
            except Exception:
                return e.code, {"_raw": b.decode("utf-8", "replace")[:300]}, None
        except (urllib.error.URLError, OSError) as e:
            if attempt < attempts - 1:
                time.sleep(retry_wait * (attempt + 1))
                continue
            if raw:
                return 0, b"", None
            return 0, {"_neterr": f"{e}(已重试 {attempts} 次)"}, None


def tenant_token(domain: str, app_id: str, app_secret: str) -> str:
    """换 tenant_access_token;失败抛 RuntimeError(带 Lark 响应便于定位)。"""
    _, res, _ = http(
        f"{domain.rstrip('/')}/open-apis/auth/v3/tenant_access_token/internal",
        "POST",
        {"app_id": app_id, "app_secret": app_secret},
    )
    tok = res.get("tenant_access_token") if isinstance(res, dict) else None
    if not tok:
        raise RuntimeError(f"获取 tenant_access_token 失败:{res}")
    return tok
