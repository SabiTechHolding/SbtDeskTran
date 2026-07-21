use crate::engine::diff::DiffResult;

#[tauri::command]
pub async fn compute_diff(
    left: String,
    right: String,
    ignore_whitespace: bool,
    word_diff: bool,
) -> Result<DiffResult, String> {
    let result = crate::engine::diff::compute_diff(&left, &right, ignore_whitespace, word_diff)
        .map_err(|e| e.to_string())?;
    Ok(result)
}
