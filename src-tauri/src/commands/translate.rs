use crate::commands::settings::SettingsState;
use crate::engine::translator::TranslateResult;
use tauri::State;

#[tauri::command]
pub async fn translate(
    text: String,
    src: String,
    dest: String,
    state: State<'_, SettingsState>,
) -> Result<TranslateResult, String> {
    let strategy = state
        .0
        .lock()
        .ok()
        .and_then(|m| m.get("network_strategy").and_then(|v| v.as_u64()))
        .unwrap_or(0) as u8;
    let result = crate::engine::translator::translate(&text, &src, &dest, strategy)
        .await
        .map_err(|e| e.to_string())?;
    persist_strategy(&state, result.strategy)?;
    Ok(result)
}

/// Translate multiple text units sequentially.
/// Returns results in the same order as input.
#[tauri::command]
pub async fn translate_units(
    texts: Vec<String>,
    src: String,
    dest: String,
    state: State<'_, SettingsState>,
) -> Result<Vec<TranslateResult>, String> {
    let strategy = state
        .0
        .lock()
        .ok()
        .and_then(|m| m.get("network_strategy").and_then(|v| v.as_u64()))
        .unwrap_or(0) as u8;
    let mut results = Vec::with_capacity(texts.len());
    let mut working_strategy = strategy;
    for text in &texts {
        let r = crate::engine::translator::translate(text, &src, &dest, working_strategy)
            .await
            .map_err(|e| e.to_string())?;
        working_strategy = r.strategy;
        results.push(r);
    }
    persist_strategy(&state, working_strategy)?;
    Ok(results)
}

fn persist_strategy(state: &State<'_, SettingsState>, strategy: u8) -> Result<(), String> {
    let mut settings = state.0.lock().map_err(|error| error.to_string())?;
    settings.insert(
        "network_strategy".into(),
        serde_json::Value::Number(strategy.into()),
    );
    crate::save_settings_to_disk(&settings);
    Ok(())
}
