use serde::Serialize;

#[derive(Debug, Serialize)]
pub struct TranslateResult {
    pub translated: String,
    pub detected_lang: Option<String>,
    pub source: String,
    pub strategy: u8,
}

const MAX_CHARS: usize = 700;

pub async fn translate(
    text: &str,
    src: &str,
    dest: &str,
    strategy: u8,
) -> Result<TranslateResult, String> {
    // An empty/whitespace-only edit is a local no-op and must not produce a
    // network request.
    if text.trim().is_empty() {
        return Ok(TranslateResult {
            translated: String::new(),
            detected_lang: Some(src.to_string()),
            source: "Google Translate".into(),
            strategy,
        });
    }
    let chunks = split_text(text, MAX_CHARS);
    let mut translated = String::new();
    let mut detected_lang = None;
    let mut working_strategy = strategy;
    for chunk in chunks {
        let result = translate_single(&chunk, src, dest, working_strategy).await?;
        translated.push_str(&result.translated);
        working_strategy = result.strategy;
        if let Some(detected) = result.detected_lang {
            if detected != "auto" {
                detected_lang = Some(detected);
            }
        }
    }
    Ok(TranslateResult {
        translated,
        detected_lang,
        source: "Google Translate".into(),
        strategy: working_strategy,
    })
}

async fn translate_single(
    text: &str,
    src: &str,
    dest: &str,
    strategy: u8,
) -> Result<TranslateResult, String> {
    let src_param = if src == "auto" { "auto" } else { src };
    let url = format!(
        "https://translate.googleapis.com/translate_a/single?client=gtx&sl={}&tl={}&dt=t&q={}",
        src_param,
        dest,
        urlencoding(text)
    );

    let primary = crate::engine::network::request_with_strategies(&url, strategy).await;
    let (body, working_strategy) = match primary {
        Ok(response) => response,
        Err(primary_error) => {
            let fallback_url = url.replace("translate.googleapis.com", "translate.google.com");
            crate::engine::network::request_with_strategies(&fallback_url, strategy)
                .await
                .map_err(|fallback_error| {
                    format!("{}; fallback: {}", primary_error, fallback_error)
                })?
        }
    };
    let mut result = parse_google_response(&body)?;
    if result.detected_lang.is_none() {
        result.detected_lang = Some(src.to_string());
    }
    result.strategy = working_strategy;
    Ok(result)
}

fn split_text(text: &str, max_chars: usize) -> Vec<String> {
    if text.chars().count() <= max_chars {
        return vec![text.to_string()];
    }

    fn split_segment(mut text: &str, max_chars: usize) -> Vec<String> {
        let separators = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "];
        let mut chunks = Vec::new();
        while text.chars().count() > max_chars {
            let prefix: String = text.chars().take(max_chars).collect();
            let mut best = 0usize;
            for separator in separators {
                if let Some(position) = prefix.rfind(separator) {
                    best = best.max(position + separator.len());
                }
            }
            if best < max_chars / 3 {
                best = prefix.len();
            }
            let (head, tail) = text.split_at(best);
            chunks.push(head.to_string());
            text = tail;
        }
        if !text.is_empty() {
            chunks.push(text.to_string());
        }
        chunks
    }

    let mut chunks = Vec::new();
    let mut current = String::new();
    for line in text.split_inclusive('\n') {
        for part in split_segment(line, max_chars) {
            if !current.is_empty() && current.chars().count() + part.chars().count() > max_chars {
                chunks.push(std::mem::take(&mut current));
            }
            current.push_str(&part);
            if current.chars().count() >= max_chars {
                chunks.push(std::mem::take(&mut current));
            }
        }
    }
    if !current.is_empty() {
        chunks.push(current);
    }
    chunks
}

fn urlencoding(text: &str) -> String {
    text.bytes()
        .map(|byte| match byte {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' => {
                (byte as char).to_string()
            }
            b' ' => "%20".into(),
            _ => format!("%{:02X}", byte),
        })
        .collect()
}

fn parse_google_response(body: &str) -> Result<TranslateResult, String> {
    let json: serde_json::Value =
        serde_json::from_str(body).map_err(|e| format!("JSON parse error: {}", e))?;

    let mut translated = String::new();
    if let Some(arr) = json.as_array() {
        if let Some(sentences) = arr.first().and_then(|v| v.as_array()) {
            for sentence in sentences {
                if let Some(parts) = sentence.as_array() {
                    if let Some(text) = parts.first().and_then(|v| v.as_str()) {
                        translated.push_str(text);
                    }
                }
            }
        }
    }

    let detected_lang = json
        .as_array()
        .and_then(|arr| arr.get(2))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());

    Ok(TranslateResult {
        translated,
        detected_lang,
        source: "Google Translate".into(),
        strategy: 0,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_google_response() {
        let body = r#"[[["Hello","Hola",null,null,1]],null,"es",null,null,null,1,null,null,[["es"],null,[1],["es"]]]"#;
        let result = parse_google_response(body).unwrap();
        assert_eq!(result.translated, "Hello");
        assert_eq!(result.detected_lang, Some("es".into()));
    }

    #[test]
    fn test_split_text_preserves_content() {
        let text = "one. two. three. four.";
        assert_eq!(split_text(text, 7).concat(), text);
    }

    #[tokio::test]
    #[ignore = "requires live Google Translate access"]
    async fn live_translation_smoke() {
        let strategies: &[u8] = if cfg!(target_os = "windows") {
            &[0, 1]
        } else {
            &[0]
        };
        for &strategy in strategies {
            let result = translate("hello", "en", "vi", strategy).await.unwrap();
            assert!(!result.translated.trim().is_empty());
        }
    }
}
