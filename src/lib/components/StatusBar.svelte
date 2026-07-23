<script lang="ts">
  let {
    statusText = "Ready",
    statusKind = "normal",
    activeTab = "tran",
    charCount = 0,
    lineCount = 0,
    colCount = 0,
    selLength = 0,
    diffLeftChars = 0,
    diffRightChars = 0,
    translationTime = 0,
    translationChars = 0,
    panelName = "",
    diffStatsText = "",
  }: {
    statusText?: string;
    statusKind?: "normal" | "success" | "warning" | "error";
    activeTab?: string;
    charCount?: number;
    lineCount?: number;
    colCount?: number;
    selLength?: number;
    diffLeftChars?: number;
    diffRightChars?: number;
    translationTime?: number;
    translationChars?: number;
    panelName?: string;
    diffStatsText?: string;
  } = $props();

  const TAB_NAMES: Record<string, string> = { tran: "Translate", diff: "Diff", note: "Notes" };
  const STATUS_COLORS: Record<string, string> = {
    normal: "var(--status-fg)",
    success: "var(--success)",
    warning: "var(--warning)",
    error: "var(--error)",
  };

  let speed = $derived(
    translationTime > 0 && translationChars > 0
      ? `${(translationChars / (translationTime / 1000)).toFixed(0)} cps`
      : ""
  );
</script>

<div class="statusbar">
  <span class="status" style="color: {STATUS_COLORS[statusKind]}">
    {statusText}
    {#if activeTab !== "note" && panelName}
      <span class="panel-name">| {panelName}</span>
    {/if}
  </span>
  {#if activeTab === "diff" && diffStatsText}
    <span class="diff-stats">{diffStatsText}</span>
  {/if}
  <span class="metrics">
    {#if activeTab === "diff"}
      <span class="metric">Left {diffLeftChars} | Right {diffRightChars}</span>
    {:else}
      <span class="metric">{charCount} chars</span>
    {/if}
    <span class="metric">{panelName || TAB_NAMES[activeTab]}: Ln {lineCount}, Ch {colCount}</span>
    {#if selLength > 0}
      <span class="metric">| Sel {selLength}</span>
    {/if}
    {#if activeTab === "tran" && speed}
      <span class="metric">| {speed}</span>
    {/if}
    <span class="metric">{TAB_NAMES[activeTab] ?? activeTab}</span>
  </span>
</div>

<style>
  .statusbar {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
    align-items: center;
    height: 22px;
    padding: 0 8px;
    background: var(--status-bg);
    color: var(--status-fg);
    font-size: 11px;
    flex-shrink: 0;
    user-select: none;
  }

  .status {
    grid-column: 1;
    display: flex;
    align-items: center;
    gap: 4px;
    min-width: 0;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }

  .diff-stats {
    grid-column: 2;
    color: var(--accent2);
    font-weight: 600;
    white-space: nowrap;
  }

  .panel-name {
    color: var(--fg2);
  }

  .metrics {
    grid-column: 3;
    display: flex;
    align-items: center;
    gap: 8px;
    justify-self: end;
  }

  .metric {
    white-space: nowrap;
  }
</style>
