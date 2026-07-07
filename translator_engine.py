"""
Translator Engine - handles translation from multiple sources.
Currently supports Google Translate (no API key required).
"""
import urllib.request
import urllib.parse
import json
import re


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


class GoogleTranslateEngine:
    """Google Translate engine - no API key required."""
    name = "Google Translate"

    def translate(self, text: str, src: str = "auto", dest: str = "en") -> dict:
        if not text.strip():
            return {"translated": "", "detected_lang": src, "source": self.name}

        try:
            # Use Google Translate internal API
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": src,
                "tl": dest,
                "dt": ["t", "bd", "ld"],
                "q": text,
            }
            query = urllib.parse.urlencode(params, doseq=True)
            full_url = f"{url}?{query}"

            req = urllib.request.Request(full_url)
            req.add_header("User-Agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36")

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

            # Parse translated text
            translated_parts = []
            if data and data[0]:
                for part in data[0]:
                    if part and part[0]:
                        translated_parts.append(part[0])
            translated = "".join(translated_parts)

            # Detect source language
            detected = src
            try:
                if data and len(data) > 2 and data[2]:
                    detected = data[2]
            except Exception:
                pass

            return {
                "translated": translated,
                "detected_lang": detected,
                "source": self.name,
            }

        except Exception as e:
            raise TranslationError(f"Google Translate error: {e}")


# Registry of available engines
ENGINES = {
    "Google Translate": GoogleTranslateEngine(),
}


def get_engine(name: str):
    return ENGINES.get(name, ENGINES["Google Translate"])
