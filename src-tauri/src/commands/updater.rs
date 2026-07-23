use crate::commands::settings::SettingsState;
use serde::Serialize;
use std::time::Duration;
use tauri::{Manager, ResourceId, State, Webview};
use tauri_plugin_updater::{Update, UpdaterExt};
use tokio::io::{AsyncReadExt, AsyncWriteExt};

const UPDATE_ENDPOINT: &str =
    "https://github.com/SabiTechHolding/SbtDeskTool/releases/latest/download/latest.json";

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct UpdateMetadata {
    rid: ResourceId,
    current_version: String,
    version: String,
    date: Option<String>,
    body: Option<String>,
    raw_json: serde_json::Value,
}

fn network_strategy(state: &State<'_, SettingsState>) -> u8 {
    state
        .0
        .lock()
        .ok()
        .and_then(|settings| {
            settings
                .get("network_strategy")
                .and_then(|value| value.as_u64())
        })
        .unwrap_or(0) as u8
}

fn persist_network_strategy(state: &State<'_, SettingsState>, strategy: u8) -> Result<(), String> {
    let mut settings = state.0.lock().map_err(|error| error.to_string())?;
    settings.insert(
        "network_strategy".into(),
        serde_json::Value::Number(strategy.into()),
    );
    crate::save_settings_to_disk(&settings);
    Ok(())
}

async fn serve_once(
    body: Vec<u8>,
    content_type: &'static str,
) -> Result<(url::Url, tokio::task::JoinHandle<Result<(), String>>), String> {
    let listener = tokio::net::TcpListener::bind(("127.0.0.1", 0))
        .await
        .map_err(|error| format!("Unable to open local update bridge: {error}"))?;
    let address = listener
        .local_addr()
        .map_err(|error| format!("Unable to read local update bridge address: {error}"))?;
    let url = url::Url::parse(&format!("http://{address}/update"))
        .map_err(|error| format!("Invalid local update bridge URL: {error}"))?;

    let task = tokio::spawn(async move {
        let (mut stream, _) = listener
            .accept()
            .await
            .map_err(|error| format!("Local update bridge accept error: {error}"))?;
        let mut request = [0_u8; 8192];
        let _ = stream
            .read(&mut request)
            .await
            .map_err(|error| format!("Local update bridge read error: {error}"))?;
        let headers = format!(
            "HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
            body.len()
        );
        stream
            .write_all(headers.as_bytes())
            .await
            .map_err(|error| format!("Local update bridge header error: {error}"))?;
        stream
            .write_all(&body)
            .await
            .map_err(|error| format!("Local update bridge response error: {error}"))?;
        stream
            .shutdown()
            .await
            .map_err(|error| format!("Local update bridge shutdown error: {error}"))
    });

    Ok((url, task))
}

#[tauri::command]
pub async fn check_for_update(
    webview: Webview,
    state: State<'_, SettingsState>,
    timeout: Option<u64>,
) -> Result<Option<UpdateMetadata>, String> {
    let preferred = network_strategy(&state);
    let (body, strategy) =
        crate::engine::network::request_with_strategies(UPDATE_ENDPOINT, preferred).await?;
    persist_network_strategy(&state, strategy)?;
    serde_json::from_str::<serde_json::Value>(&body)
        .map_err(|error| format!("Invalid update metadata: {error}"))?;

    // The updater parser and signature verifier remain authoritative, but all
    // external traffic is completed first by the same core network as Translate.
    let (endpoint, bridge) = serve_once(body.into_bytes(), "application/json").await?;
    let mut builder = webview
        .updater_builder()
        .endpoints(vec![endpoint])
        .map_err(|error| error.to_string())?
        .no_proxy();
    if let Some(timeout) = timeout {
        builder = builder.timeout(Duration::from_millis(timeout));
    }

    let result = async {
        let updater = builder.build().map_err(|error| error.to_string())?;
        updater.check().await.map_err(|error| error.to_string())
    }
    .await;
    bridge.abort();
    let Some(update) = result? else {
        return Ok(None);
    };

    Ok(Some(UpdateMetadata {
        current_version: update.current_version.clone(),
        version: update.version.clone(),
        date: update.date.map(|date| date.to_string()),
        body: update.body.clone(),
        raw_json: update.raw_json.clone(),
        rid: webview.resources_table().add(update),
    }))
}

#[tauri::command]
pub async fn download_and_install_update(
    webview: Webview,
    state: State<'_, SettingsState>,
    rid: ResourceId,
) -> Result<(), String> {
    let update = webview
        .resources_table()
        .get::<Update>(rid)
        .map_err(|error| error.to_string())?;
    let preferred = network_strategy(&state);
    let (bytes, strategy) = crate::engine::network::request_bytes_with_strategies(
        update.download_url.as_str(),
        preferred,
    )
    .await?;
    persist_network_strategy(&state, strategy)?;

    // Feed the core-downloaded bytes back through the updater's verifier and
    // installer. The release signature is checked before anything is executed.
    let (download_url, bridge) = serve_once(bytes, "application/octet-stream").await?;
    let mut local_update = (*update).clone();
    local_update.download_url = download_url;
    local_update.no_proxy = true;
    local_update.proxy = None;
    local_update.timeout = Some(Duration::from_secs(60));
    let result = local_update
        .download_and_install(|_, _| {}, || {})
        .await
        .map_err(|error| error.to_string());
    bridge.abort();
    result
}
