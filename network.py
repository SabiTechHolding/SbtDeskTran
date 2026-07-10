"""
Shared network utilities: proxy detection, SSL configuration, HTTP requests,
WinINet fallback, and error diagnostics for corporate/VPN/proxy environments.
"""
import ctypes
import socket
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from ctypes import wintypes

try:
    from logger import log
except Exception:
    import logging
    log = logging.getLogger("SbtDeskTran")


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# ── Proxy detection ─────────────────────────────────────────────

def get_system_proxy() -> dict:
    """Read Windows system proxy settings from registry."""
    proxy = {}
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        )
        try:
            auto_config, _ = winreg.QueryValueEx(key, "AutoConfigURL")
            log.debug(f"WinINet proxy PAC detected: {auto_config}")
        except Exception:
            pass
        try:
            auto_detect, _ = winreg.QueryValueEx(key, "AutoDetect")
            log.debug(f"WinINet proxy auto-detect: {auto_detect}")
        except Exception:
            pass
        enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
        if enabled:
            server, _ = winreg.QueryValueEx(key, "ProxyServer")
            if server:
                if "://" not in server:
                    server = "http://" + server
                proxy = {"http": server, "https": server}
                log.debug(f"System proxy detected: {server}")
    except Exception as e:
        log.debug(f"No system proxy or registry read failed: {e}")
    return proxy


# ── Opener builder ──────────────────────────────────────────────

def build_opener(proxy: dict = None, ssl_verify: bool = True) -> urllib.request.OpenerDirector:
    """Build urllib opener with optional proxy and SSL settings.

    * proxy=None  — use urllib default system/env proxy lookup
    * proxy={}    — explicitly direct (no proxy)
    * proxy=dict  — configured proxy
    """
    handlers = []

    if proxy is None:
        handlers.append(urllib.request.ProxyHandler())
    else:
        handlers.append(urllib.request.ProxyHandler(proxy))

    if not ssl_verify:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        handlers.append(urllib.request.HTTPSHandler(context=ctx))

    return urllib.request.build_opener(*handlers)


def proxy_label(proxy) -> str:
    if proxy == "windows":
        return "windows-proxy"
    if proxy is None:
        return "system-proxy"
    if proxy:
        return "configured-proxy"
    return "direct"


# ── HTTP requests ───────────────────────────────────────────────

def do_request(url: str, timeout: int, opener: urllib.request.OpenerDirector,
               user_agent: str = DEFAULT_USER_AGENT) -> bytes:
    """Perform an HTTP GET via *opener* with standard headers."""
    req = urllib.request.Request(url)
    req.add_header("User-Agent", user_agent)
    req.add_header("Accept", "application/json, text/plain, */*")
    req.add_header("Accept-Language", "en-US,en;q=0.9")
    with opener.open(req, timeout=timeout) as resp:
        return resp.read()


def do_request_wininet(url: str, timeout: int,
                       user_agent: str = DEFAULT_USER_AGENT) -> bytes:
    """Use WinINet in-process as the Windows proxy/PAC fallback."""
    if sys.platform != "win32":
        raise OSError("WinINet fallback is only available on Windows")

    wininet = ctypes.WinDLL("wininet", use_last_error=True)
    internet_open = wininet.InternetOpenW
    internet_open.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.LPCWSTR,
        wintypes.LPCWSTR, wintypes.DWORD,
    ]
    internet_open.restype = wintypes.HANDLE

    internet_open_url = wininet.InternetOpenUrlW
    internet_open_url.argtypes = [
        wintypes.HANDLE, wintypes.LPCWSTR, wintypes.LPCWSTR,
        wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t,
    ]
    internet_open_url.restype = wintypes.HANDLE

    internet_read_file = wininet.InternetReadFile
    internet_read_file.argtypes = [
        wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    internet_read_file.restype = wintypes.BOOL

    internet_set_option = wininet.InternetSetOptionW
    internet_set_option.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
    ]
    internet_set_option.restype = wintypes.BOOL

    internet_close_handle = wininet.InternetCloseHandle
    internet_close_handle.argtypes = [wintypes.HANDLE]
    internet_close_handle.restype = wintypes.BOOL

    INTERNET_OPEN_TYPE_PRECONFIG = 0
    INTERNET_FLAG_RELOAD = 0x80000000
    INTERNET_FLAG_NO_CACHE_WRITE = 0x04000000
    INTERNET_FLAG_NO_UI = 0x00000200
    INTERNET_OPTION_CONNECT_TIMEOUT = 2
    INTERNET_OPTION_SEND_TIMEOUT = 5
    INTERNET_OPTION_RECEIVE_TIMEOUT = 6

    handle = internet_open(user_agent, INTERNET_OPEN_TYPE_PRECONFIG, None, None, 0)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())

    request = None
    try:
        timeout_ms = wintypes.DWORD(int(timeout * 1000))
        for option in (
            INTERNET_OPTION_CONNECT_TIMEOUT,
            INTERNET_OPTION_SEND_TIMEOUT,
            INTERNET_OPTION_RECEIVE_TIMEOUT,
        ):
            internet_set_option(
                handle, option, ctypes.byref(timeout_ms), ctypes.sizeof(timeout_ms)
            )

        headers = (
            "Accept: application/json, text/plain, */*\r\n"
            "Accept-Language: en-US,en;q=0.9\r\n"
        )
        flags = INTERNET_FLAG_RELOAD | INTERNET_FLAG_NO_CACHE_WRITE | INTERNET_FLAG_NO_UI
        request = internet_open_url(handle, url, headers, len(headers), flags, 0)
        if not request:
            raise ctypes.WinError(ctypes.get_last_error())

        chunks = []
        buf_size = 64 * 1024
        while True:
            buffer = ctypes.create_string_buffer(buf_size)
            read = wintypes.DWORD(0)
            if not internet_read_file(request, buffer, buf_size, ctypes.byref(read)):
                raise ctypes.WinError(ctypes.get_last_error())
            if read.value == 0:
                break
            chunks.append(buffer.raw[:read.value])
        return b"".join(chunks)
    finally:
        if request:
            internet_close_handle(request)
        internet_close_handle(handle)


# ── Multi-strategy retry ────────────────────────────────────────

def build_strategies(url: str, user_agent: str = DEFAULT_USER_AGENT) -> list:
    """Return list of (url, proxy, ssl_verify, timeout, transport) tuples."""
    configured_proxy = get_system_proxy()
    system_proxy = configured_proxy or None
    return [
        (url, system_proxy, True,  12, "urllib"),      # system proxy
        (url, "windows",    True,  25, "wininet"),     # Windows proxy/PAC
        (url, system_proxy, False, 12, "urllib"),      # SSL off
        (url, {},           True,  15, "urllib"),      # direct
        (url, {},           False, 15, "urllib"),      # direct, SSL off
    ]


def request_with_strategies(
    url: str,
    user_agent: str = DEFAULT_USER_AGENT,
    working_strategy: int = -1,
    settings: dict = None,
    strategy_key: str = "network_strategy",
) -> tuple[bytes, int]:
    """Try network strategies in order, return (response_body, strategy_index).

    If *working_strategy* >= 0, that strategy is attempted first as a cache.
    When *settings* is provided, the working strategy is persisted to
    ``settings[strategy_key]`` after a successful attempt.
    """
    if working_strategy < 0 and settings is not None:
        working_strategy = settings.get(strategy_key, -1)

    strategies = build_strategies(url, user_agent)

    # Try cached strategy first
    if 0 <= working_strategy < len(strategies):
        url_s, proxy, ssl_verify, timeout, transport = strategies[working_strategy]
        log.debug(f"Using cached strategy {working_strategy} ({proxy_label(proxy)})")
        try:
            if transport == "wininet":
                data = do_request_wininet(url_s, timeout, user_agent=user_agent)
            else:
                opener = build_opener(proxy, ssl_verify)
                data = do_request(url_s, timeout, opener, user_agent=user_agent)
            return data, working_strategy
        except (urllib.error.URLError, socket.timeout, TimeoutError,
                OSError) as e:
            log.warning(f"Cached strategy {working_strategy} failed: {e}")

    # Full retry
    last_error = None
    for i, (url_s, proxy, ssl_verify, timeout, transport) in enumerate(strategies):
        pl = proxy_label(proxy)
        ssl_l = "ssl-on" if ssl_verify else "ssl-off"
        log.debug(f"Attempt {i+1}/{len(strategies)}: {pl} {ssl_l} {transport}")
        try:
            if transport == "wininet":
                data = do_request_wininet(url_s, timeout, user_agent=user_agent)
            else:
                opener = build_opener(proxy, ssl_verify)
                data = do_request(url_s, timeout, opener, user_agent=user_agent)
            log.info(f"Strategy {i} ({pl}, {ssl_l}) succeeded — cached")
            if settings is not None:
                settings[strategy_key] = i
            return data, i
        except (urllib.error.URLError, socket.timeout, TimeoutError,
                OSError) as e:
            log.warning(f"Attempt {i+1} failed: {type(e).__name__}: {e}")
            last_error = e

    raise last_error or ConnectionError("All network strategies failed")


# ── Error diagnostics ───────────────────────────────────────────

def network_hint(error) -> str:
    """Return a user-friendly diagnostic message for a network error."""
    reason = getattr(error, "reason", error)
    winerror = getattr(reason, "winerror", None) or getattr(error, "winerror", None)
    if winerror == 10013:
        return (
            "Socket permission denied (WinError 10013). Windows Firewall, "
            "endpoint security, AppLocker, or policy for apps launched from a "
            "network share is blocking outbound HTTPS."
        )
    if isinstance(reason, socket.gaierror):
        return ("DNS lookup failed. Check DNS, VPN, proxy, "
                "or remote-session network settings.")
    if isinstance(reason, ssl.SSLError):
        return ("SSL certificate/inspection error. "
                "Check corporate proxy or certificate trust.")
    return str(reason)
