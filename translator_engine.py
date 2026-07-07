"""
Translator Engine - handles translation from multiple sources.
Currently supports Google Translate (no API key required).

Network strategy (for corporate/VPN/proxy environments):
  1. Try with Windows system proxy (auto-detected via urllib)
  2. Retry with SSL verification disabled (corporate MITM certs)
  3. Retry via alternative translate endpoint
  4. Raise TranslationError with detailed diagnostics
"""
import urllib.request
import urllib.parse
import urllib.error
import json
import ssl
import socket

try:
    from logger import log
except Exception:
    import logging
    log = logging.getLogger("SbtDeskTran")


LANGUAGES = {
    "Auto Detect": "auto",
    "Afrikaans": "af", "Albanian": "sq", "Amharic": "am",
    "Arabic": "ar", "Armenian": "hy", "Azerbaijani": "az",
    "Basque": "eu", "Belarusian": "be", "Bengali": "bn",
    "Bosnian": "bs", "Bulgarian": "bg", "Catalan": "ca",
    "Cebuano": "ceb", "Chinese (Simplified)": "zh-CN",
    "Chinese (Traditional)": "zh-TW", "Corsican": "co",
    "Croatian": "hr", "Czech": "cs", "Danish": "da",
    "Dutch": "nl", "English": "en", "Esperanto": "eo",
    "Estonian": "et", "Finnish": "fi", "French": "fr",
    "Frisian": "fy", "Galician": "gl", "Georgian": "ka",
    "German": "de", "Greek": "el", "Gujarati": "gu",
    "Haitian Creole": "ht", "Hausa": "ha", "Hawaiian": "haw",
    "Hebrew": "he", "Hindi": "hi", "Hmong": "hmn",
    "Hungarian": "hu", "Icelandic": "is", "Igbo": "ig",
    "Indonesian": "id", "Irish": "ga", "Italian": "it",
    "Japanese": "ja", "Javanese": "jv", "Kannada": "kn",
    "Kazakh": "kk", "Khmer": "km", "Kinyarwanda": "rw",
    "Korean": "ko", "Kurdish": "ku", "Kyrgyz": "ky",
    "Lao": "lo", "Latin": "la", "Latvian": "lv",
    "Lithuanian": "lt", "Luxembourgish": "lb", "Macedonian": "mk",
    "Malagasy": "mg", "Malay": "ms", "Malayalam": "ml",
    "Maltese": "mt", "Maori": "mi", "Marathi": "mr",
    "Mongolian": "mn", "Myanmar": "my", "Nepali": "ne",
    "Norwegian": "no", "Nyanja": "ny", "Odia": "or",
    "Pashto": "ps", "Persian": "fa", "Polish": "pl",
    "Portuguese": "pt", "Punjabi": "pa", "Romanian": "ro",
    "Russian": "ru", "Samoan": "sm", "Scots Gaelic": "gd",
    "Serbian": "sr", "Sesotho": "st", "Shona": "sn",
    "Sindhi": "sd", "Sinhala": "si", "Slovak": "sk",
    "Slovenian": "sl", "Somali": "so", "Spanish": "es",
    "Sundanese": "su", "Swahili": "sw", "Swedish": "sv",
    "Tagalog": "tl", "Tajik": "tg", "Tamil": "ta",
    "Tatar": "tt", "Telugu": "te", "Thai": "th",
    "Turkish": "tr", "Turkmen": "tk", "Ukrainian": "uk",
    "Urdu": "ur", "Uyghur": "ug", "Uzbek": "uz",
    "Vietnamese": "vi", "Welsh": "cy", "Xhosa": "xh",
    "Yiddish": "yi", "Yoruba": "yo", "Zulu": "zu",
}

LANG_CODE_TO_NAME = {v: k for k, v in LANGUAGES.items()}


class TranslationError(Exception):
    pass


def _get_system_proxy() -> dict:
    """Read Windows system proxy settings from registry."""
    proxy = {}
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        )
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


def _build_opener(proxy: dict = None, ssl_verify: bool = True) -> urllib.request.OpenerDirector:
    """Build urllib opener with optional proxy and SSL settings."""
    handlers = []

    # Proxy handler
    if proxy:
        handlers.append(urllib.request.ProxyHandler(proxy))
    else:
        # Use system proxy (default urllib behavior on Windows reads IE settings)
        handlers.append(urllib.request.ProxyHandler())

    # SSL context
    if not ssl_verify:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        handlers.append(urllib.request.HTTPSHandler(context=ctx))
        log.debug("SSL verification disabled for this attempt")

    return urllib.request.build_opener(*handlers)


def _do_request(full_url: str, timeout: int, opener) -> bytes:
    req = urllib.request.Request(full_url)
    req.add_header("User-Agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36")
    req.add_header("Accept", "application/json, text/plain, */*")
    req.add_header("Accept-Language", "en-US,en;q=0.9")
    with opener.open(req, timeout=timeout) as resp:
        return resp.read()


def _parse_gtx_response(data) -> tuple:
    """Parse gtx API response. Returns (translated_text, detected_lang)."""
    translated_parts = []
    if data and data[0]:
        for part in data[0]:
            if part and part[0]:
                translated_parts.append(part[0])
    translated = "".join(translated_parts)
    detected = ""
    try:
        if data and len(data) > 2 and data[2]:
            detected = data[2]
    except Exception:
        pass
    return translated, detected


class GoogleTranslateEngine:
    """
    Google Translate engine — no API key required.
    Tries multiple network strategies to work through corporate proxies/firewalls.
    Caches the working strategy index so subsequent calls skip retries.
    """
    name = "Google Translate"

    # Two endpoints — primary and fallback
    _ENDPOINTS = [
        "https://translate.googleapis.com/translate_a/single",
        "https://translate.google.com/translate_a/single",
    ]

    def __init__(self):
        # Index of the last working strategy (-1 = not yet found)
        self._working_strategy: int = -1

    def _make_strategies(self, query: str) -> list:
        """Return list of (url, proxy, ssl_verify, timeout) tuples."""
        sys_proxy = _get_system_proxy()
        strategies = []
        for endpoint in self._ENDPOINTS:
            url = f"{endpoint}?{query}"
            strategies += [
                (url, sys_proxy, True,  12),   # system proxy, SSL on
                (url, sys_proxy, False, 12),   # system proxy, SSL off (MITM bypass)
                (url, {},        True,  15),   # direct, SSL on
                (url, {},        False, 15),   # direct, SSL off
            ]
        return strategies

    def translate(self, text: str, src: str = "auto", dest: str = "en") -> dict:
        if not text.strip():
            return {"translated": "", "detected_lang": src, "source": self.name}

        log.debug(f"Translate request: src={src} dest={dest} chars={len(text)}")

        params = {
            "client": "gtx",
            "sl": src,
            "tl": dest,
            "dt": ["t", "bd", "ld"],
            "q": text,
        }
        query = urllib.parse.urlencode(params, doseq=True)
        strategies = self._make_strategies(query)

        # If we have a cached working strategy, try it first
        if self._working_strategy >= 0:
            idx = self._working_strategy
            url, proxy, ssl_verify, timeout = strategies[idx]
            proxy_label = "sys-proxy" if proxy else "direct"
            ssl_label = "ssl-on" if ssl_verify else "ssl-off"
            log.debug(f"Using cached strategy {idx} ({proxy_label}, {ssl_label})")
            try:
                opener = _build_opener(proxy, ssl_verify)
                raw = _do_request(url, timeout, opener)
                data = json.loads(raw.decode("utf-8"))
                translated, detected = _parse_gtx_response(data)
                if not detected:
                    detected = src
                log.debug(f"Cached strategy {idx} succeeded: {len(translated)} chars")
                return {
                    "translated": translated,
                    "detected_lang": detected,
                    "source": self.name,
                }
            except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as e:
                # Network error — reset cache and fall through to full retry
                log.warning(f"Cached strategy {idx} failed ({type(e).__name__}: {e}), resetting cache")
                self._working_strategy = -1
            except Exception as e:
                log.error(f"Cached strategy {idx} unexpected error: {e}", exc_info=True)
                self._working_strategy = -1

        # Full retry — try all strategies in order
        last_error = None
        for i, (url, proxy, ssl_verify, timeout) in enumerate(strategies):
            proxy_label = "sys-proxy" if proxy else "direct"
            ssl_label = "ssl-on" if ssl_verify else "ssl-off"
            log.debug(f"Attempt {i+1}/{len(strategies)}: {proxy_label} {ssl_label}")
            try:
                opener = _build_opener(proxy, ssl_verify)
                raw = _do_request(url, timeout, opener)
                data = json.loads(raw.decode("utf-8"))
                translated, detected = _parse_gtx_response(data)
                if not detected:
                    detected = src
                # Cache this working strategy
                self._working_strategy = i
                log.info(f"Translate OK via strategy {i} ({proxy_label}, {ssl_label}): "
                         f"detected={detected} out={len(translated)} chars — strategy cached")
                return {
                    "translated": translated,
                    "detected_lang": detected,
                    "source": self.name,
                }
            except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as e:
                log.warning(f"Attempt {i+1} network error: {type(e).__name__}: {e}")
                last_error = e
            except Exception as e:
                log.error(f"Attempt {i+1} unexpected error: {e}", exc_info=True)
                last_error = e

        # All strategies failed
        log.error(f"All {len(strategies)} translation attempts failed. Last: {last_error}")
        if isinstance(last_error, (socket.timeout, TimeoutError)):
            hint = "Network timeout — check if translate.googleapis.com is accessible"
        elif isinstance(last_error, urllib.error.URLError):
            hint = f"Network error — {last_error.reason}"
        else:
            hint = str(last_error)
        raise TranslationError(f"Translation failed: {hint}")


# Registry of available engines
ENGINES = {
    "Google Translate": GoogleTranslateEngine(),
}


def get_engine(name: str):
    return ENGINES.get(name, ENGINES["Google Translate"])
