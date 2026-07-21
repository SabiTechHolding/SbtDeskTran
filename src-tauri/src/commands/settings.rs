use serde_json::Value;
use std::sync::Mutex;
use tauri::State;

pub struct SettingsState(pub Mutex<serde_json::Map<String, Value>>);

#[tauri::command]
pub fn get_settings(state: State<SettingsState>) -> Result<Value, String> {
    let map = state.0.lock().map_err(|e| e.to_string())?;
    serde_json::to_value(&*map).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn save_setting(state: State<SettingsState>, key: String, value: Value) -> Result<(), String> {
    let mut map = state.0.lock().map_err(|e| e.to_string())?;
    map.insert(key, value);
    crate::save_settings_to_disk(&map);
    Ok(())
}

#[tauri::command]
pub fn save_settings_flush(state: State<SettingsState>) -> Result<(), String> {
    let map = state.0.lock().map_err(|e| e.to_string())?;
    crate::save_settings_to_disk(&map);
    Ok(())
}
