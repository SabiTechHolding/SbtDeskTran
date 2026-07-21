<script lang="ts">
  import { onMount } from "svelte";

  let {
    text = "",
    x = 0,
    y = 0,
    onClose,
  }: {
    text: string;
    x: number;
    y: number;
    onClose: () => void;
  } = $props();

  let translation = $state("");
  let loading = $state(true);

  onMount(async () => {
    try {
      const { invoke } = await import("@tauri-apps/api/core");
      const result = await invoke<{ translated: string }>("translate", {
        text: text.trim().slice(0, 200),
        src: "auto",
        dest: "vi",
      });
      translation = result.translated;
    } catch (e) {
      translation = `Error: ${e}`;
    } finally {
      loading = false;
    }
  });
</script>

<svelte:window onclick={onClose} onkeydown={(e) => { if (e.key === "Escape") onClose(); }} />

<div class="popup-dict" style="left: {Math.min(x, window.innerWidth - 280)}px; top: {Math.min(y, window.innerHeight - 120)}px;">
  <div class="pd-header">
    <span class="pd-title">Dictionary</span>
    <button class="pd-close" onclick={onClose}>✕</button>
  </div>
  <div class="pd-word">{text.slice(0, 100)}</div>
  <div class="pd-divider"></div>
  <div class="pd-result">
    {#if loading}
      <span class="pd-loading">Translating...</span>
    {:else}
      {translation}
    {/if}
  </div>
</div>

<style>
  .popup-dict {
    position: fixed;
    z-index: 1001;
    width: 260px;
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 6px;
    box-shadow: 0 6px 20px rgba(0,0,0,0.4);
    overflow: hidden;
  }

  .pd-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 4px 8px;
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
  }

  .pd-title {
    font-size: 11px;
    font-weight: 600;
    color: var(--accent);
  }

  .pd-close {
    background: none;
    border: none;
    color: var(--fg2);
    cursor: pointer;
    font-size: 12px;
    padding: 0 2px;
  }

  .pd-close:hover { color: var(--fg); }

  .pd-word {
    padding: 6px 8px 2px;
    font-size: 13px;
    font-weight: 600;
    color: var(--fg);
    font-family: 'JetBrains Mono', 'Consolas', monospace;
  }

  .pd-divider {
    height: 1px;
    background: var(--border);
    margin: 4px 8px;
  }

  .pd-result {
    padding: 2px 8px 8px;
    font-size: 12px;
    color: var(--fg2);
    line-height: 1.4;
  }

  .pd-loading {
    color: var(--fg2);
    font-style: italic;
  }
</style>
