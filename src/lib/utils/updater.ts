import { invoke } from "@tauri-apps/api/core";
import { formatAppVersion } from "./version";

export interface DialogRequest {
  title: string;
  message: string;
  details?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  showCancel?: boolean;
  tone?: "normal" | "warning" | "error";
}

export type ShowDialog = (request: DialogRequest) => Promise<boolean>;

interface UpdateMetadata {
  rid: number;
  currentVersion: string;
  version: string;
  date?: string;
  body?: string;
  rawJson: Record<string, unknown>;
}

const UPDATE_ENDPOINT =
  "https://github.com/SabiTechHolding/SbtDeskTool/releases/latest/download/latest.json";

function errorMessage(error: unknown) {
  if (error instanceof Error) return `${error.name}: ${error.message}`;
  return String(error);
}

export async function checkForUpdates(
  force: boolean,
  onProgress?: (message: string) => void,
  showDialog?: ShowDialog,
) {
  try {
    onProgress?.("Checking...");
    const metadata = await invoke<UpdateMetadata | null>("check_for_update", {
      timeout: 20000,
    });
    if (!metadata) {
      if (force) await showDialog?.({ title: "Check Update", message: "You are up to date." });
      return;
    }
    if (!showDialog) return;
    const accepted = await showDialog({
      title: `Update ${formatAppVersion(metadata.version)}`,
      message: "A new version is available. Download and install now?",
      details: metadata.body,
      confirmLabel: "Install",
      cancelLabel: "Later",
      showCancel: true,
    });
    if (!accepted) {
      return;
    }
    onProgress?.("Downloading update...");
    await invoke("download_and_install_update", { rid: metadata.rid });
    await invoke("restart_app");
  } catch (error) {
    const detail = `${UPDATE_ENDPOINT} - ${errorMessage(error)}`;
    console.error("Update check failed", error);
    await invoke("record_update_error", { message: detail }).catch(() => undefined);
    if (force) {
      await showDialog?.({
        title: "Check Update",
        message: "Unable to check for updates. Please try again later.",
        tone: "error",
      });
    }
  } finally {
    onProgress?.("");
  }
}
