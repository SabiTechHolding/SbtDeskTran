use crate::models::notes::Note;
use std::path::Path;

fn parse_notes(content: &str) -> Result<(Vec<Note>, bool), String> {
    let values: Vec<serde_json::Value> =
        serde_json::from_str(content).map_err(|e| e.to_string())?;
    let base_id = chrono::Utc::now().timestamp_millis();
    let mut migrated = false;
    let notes = values
        .into_iter()
        .enumerate()
        .map(|(index, value)| {
            let object = value.as_object().ok_or("Invalid note entry")?;
            let id = object
                .get("id")
                .and_then(|v| v.as_i64())
                .unwrap_or_else(|| {
                    migrated = true;
                    base_id + index as i64
                });
            let title = object
                .get("title")
                .and_then(|v| v.as_str())
                .unwrap_or("Untitled")
                .to_string();
            let body = object
                .get("body")
                .and_then(|v| v.as_str())
                .unwrap_or_default()
                .to_string();
            let created_at = object
                .get("created_at")
                .and_then(|v| v.as_str())
                .map(str::to_string)
                .unwrap_or_else(|| {
                    migrated = true;
                    now_iso()
                });
            let updated_at = object
                .get("updated_at")
                .and_then(|v| v.as_str())
                .map(str::to_string)
                .unwrap_or_else(|| {
                    migrated = true;
                    created_at.clone()
                });
            Ok(Note {
                id,
                title,
                body,
                created_at,
                updated_at,
            })
        })
        .collect::<Result<Vec<_>, String>>()?;
    Ok((notes, migrated))
}

fn read_notes(path: &Path) -> Result<Vec<Note>, String> {
    if !path.exists() {
        return Ok(Vec::new());
    }
    let content = std::fs::read_to_string(path).map_err(|e| e.to_string())?;
    let (notes, migrated) = parse_notes(&content)?;
    if migrated {
        write_notes(path, &notes)?;
    }
    Ok(notes)
}

fn write_notes(path: &Path, notes: &[Note]) -> Result<(), String> {
    let content = serde_json::to_string_pretty(notes).map_err(|e| e.to_string())?;
    std::fs::write(path, content).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn list_notes() -> Result<Vec<Note>, String> {
    read_notes(&crate::get_data_dir().join("notes.json"))
}

#[tauri::command]
pub fn save_note(note: Note) -> Result<(), String> {
    let path = crate::get_data_dir().join("notes.json");
    let mut notes = read_notes(&path)?;

    if let Some(existing) = notes.iter_mut().find(|entry| entry.id == note.id) {
        existing.title = note.title;
        existing.body = note.body;
        existing.updated_at = now_iso();
    } else {
        let mut new_note = note;
        new_note.created_at = now_iso();
        new_note.updated_at = now_iso();
        notes.push(new_note);
    }
    write_notes(&path, &notes)
}

#[tauri::command]
pub fn delete_note(id: i64) -> Result<(), String> {
    let path = crate::get_data_dir().join("notes.json");
    let mut notes = read_notes(&path)?;
    notes.retain(|note| note.id != id);
    write_notes(&path, &notes)
}

#[tauri::command]
pub async fn flush_notes() -> Result<(), String> {
    Ok(())
}

fn now_iso() -> String {
    chrono::Utc::now().to_rfc3339()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalizes_older_note_records() {
        let (notes, migrated) = parse_notes(r#"[{"title":"Legacy","body":"Text"}]"#).unwrap();
        assert!(migrated);
        assert_eq!(notes.len(), 1);
        assert_eq!(notes[0].title, "Legacy");
        assert!(notes[0].id > 0);
    }
}
