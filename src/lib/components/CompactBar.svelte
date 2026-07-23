<script lang="ts">
  import { LANGUAGES } from "../utils/languages";
  import AppIcon from "./AppIcon.svelte";

  type TabId = "tran" | "diff" | "note";

  const tabs: Array<{ id: TabId; icon: string; label: string }> = [
    { id: "diff", icon: "diff", label: "Diff" },
    { id: "tran", icon: "translate", label: "Translate" },
    { id: "note", icon: "notes", label: "Notes" },
  ];

  let {
    activeTab,
    layout,
    wordWraps,
    showWhitespaces,
    diffWordDiff,
    diffIgnoreWhitespace,
    diffAlgorithm,
    srcLang,
    destLang,
    onTop,
    notes,
    selectedNoteId,
    onSetLang,
    onSelectNote,
    onTabSwitch,
    onToggleCompact,
    onToggleOnTop,
    onToggleLayout,
    onToggleWrap,
    onToggleWhitespace,
    onSwapText,
    onToggleDiffWord,
    onToggleDiffIgnoreWhitespace,
    onSetDiffAlgorithm,
  }: {
    activeTab: TabId;
    layout: "horizontal" | "vertical";
    wordWraps: Record<TabId, boolean>;
    showWhitespaces: Record<TabId, boolean>;
    diffWordDiff: boolean;
    diffIgnoreWhitespace: boolean;
    diffAlgorithm: "legacy" | "advanced";
    srcLang: string;
    destLang: string;
    onTop: boolean;
    notes: Array<{ id: number; title: string }>;
    selectedNoteId: number | null;
    onSetLang: (field: "src_lang" | "dest_lang" | "engine", val: string) => void;
    onSelectNote: (id: number) => void;
    onTabSwitch: (tab: TabId) => void;
    onToggleCompact: () => void;
    onToggleOnTop: () => void;
    onToggleLayout: () => void;
    onToggleWrap: (tab: TabId) => void;
    onToggleWhitespace: (tab: TabId) => void;
    onSwapText?: () => void;
    onToggleDiffWord: () => void;
    onToggleDiffIgnoreWhitespace: () => void;
    onSetDiffAlgorithm: (algorithm: "legacy" | "advanced") => void;
  } = $props();

  let showSrcMenu = $state(false);
  let showDestMenu = $state(false);
  let srcFilter = $state("");
  let destFilter = $state("");

  function filterItems(items: { name: string; code: string }[], filter: string) {
    if (!filter) return items;
    return items.filter((item) => item.name.toLowerCase().includes(filter.toLowerCase()));
  }
</script>

<div class="compact-bar">
  <nav class="compact-tabs" aria-label="Tools">
    {#each tabs as tab}
      <button
        class="icon-btn tab-btn"
        class:active={activeTab === tab.id}
        onclick={() => onTabSwitch(tab.id)}
        title={tab.label}
        aria-label={tab.label}
      ><AppIcon name={tab.icon} /></button>
    {/each}
  </nav>

  {#if activeTab === "diff"}
    <span class="separator"></span>
    <div class="control-group" aria-label="Diff display controls">
      <button class="icon-btn" class:active={diffWordDiff} onclick={onToggleDiffWord} title="Highlight changed words and characters" aria-label="Highlight changed words and characters"><AppIcon name="word" /></button>
      <button class="icon-btn" class:active={diffIgnoreWhitespace} onclick={onToggleDiffIgnoreWhitespace} title="Ignore whitespace-only changes" aria-label="Ignore whitespace-only changes"><AppIcon name="ignore-whitespace" /></button>
      <button class="icon-btn" class:active={wordWraps.diff} onclick={() => onToggleWrap("diff")} title="Toggle word wrap for Diff" aria-label="Toggle word wrap for Diff"><AppIcon name="wrap" /></button>
      <button class="icon-btn" class:active={showWhitespaces.diff} onclick={() => onToggleWhitespace("diff")} title="Show or hide whitespace characters" aria-label="Show or hide whitespace characters"><AppIcon name="whitespace" /></button>
    </div>
    <div class="control-group" aria-label="Diff algorithm">
      <button class="icon-btn" class:active={diffAlgorithm === "legacy"} onclick={() => onSetDiffAlgorithm("legacy")} title="Use legacy diff alignment" aria-label="Use legacy diff alignment"><AppIcon name="legacy" /></button>
      <button class="icon-btn" class:active={diffAlgorithm === "advanced"} onclick={() => onSetDiffAlgorithm("advanced")} title="Use advanced diff alignment" aria-label="Use advanced diff alignment"><AppIcon name="advanced" /></button>
    </div>
  {:else if activeTab === "tran"}
    <span class="separator"></span>
    <div class="dropdown-wrapper" onmouseleave={() => (showSrcMenu = false)} role="presentation">
      <button class="dropdown-trigger" onclick={() => (showSrcMenu = !showSrcMenu)} title={`From: ${srcLang}`}>
        {srcLang}
      </button>
      {#if showSrcMenu}
        <div class="dropdown-menu">
          <input class="dropdown-filter" type="text" placeholder="Filter..." bind:value={srcFilter} />
          {#each filterItems(LANGUAGES, srcFilter) as item}
            <button
              class="dropdown-item"
              onclick={() => { onSetLang("src_lang", item.name); showSrcMenu = false; srcFilter = ""; }}
            >{item.name}</button>
          {/each}
        </div>
      {/if}
    </div>

    <span class="arrow">↔</span>

    <div class="dropdown-wrapper" onmouseleave={() => (showDestMenu = false)} role="presentation">
      <button class="dropdown-trigger" onclick={() => (showDestMenu = !showDestMenu)} title={`To: ${destLang}`}>
        {destLang}
      </button>
      {#if showDestMenu}
        <div class="dropdown-menu right-menu">
          <input class="dropdown-filter" type="text" placeholder="Filter..." bind:value={destFilter} />
          {#each filterItems(LANGUAGES.filter((item) => item.code !== "auto"), destFilter) as item}
            <button
              class="dropdown-item"
              onclick={() => { onSetLang("dest_lang", item.name); showDestMenu = false; destFilter = ""; }}
            >{item.name}</button>
          {/each}
        </div>
      {/if}
    </div>

    <div class="control-group" aria-label="Translate language and layout">
      <button class="icon-btn" onclick={onSwapText} title="Swap From and To languages" aria-label="Swap From and To languages"><AppIcon name="swap" /></button>
      <button class="icon-btn" class:active={layout === "vertical"} onclick={onToggleLayout} title={layout === "horizontal" ? "Switch to Vertical" : "Switch to Horizontal"} aria-label={layout === "horizontal" ? "Switch to Vertical" : "Switch to Horizontal"}><AppIcon name="layout" /></button>
    </div>
    <span class="separator"></span>
    <div class="control-group" aria-label="Translate display controls">
      <button class="icon-btn" class:active={wordWraps.tran} onclick={() => onToggleWrap("tran")} title="Toggle word wrap for Translate" aria-label="Toggle word wrap for Translate"><AppIcon name="wrap" /></button>
      <button class="icon-btn" class:active={showWhitespaces.tran} onclick={() => onToggleWhitespace("tran")} title="Show or hide whitespace characters" aria-label="Show or hide whitespace characters"><AppIcon name="whitespace" /></button>
    </div>
  {:else if activeTab === "note"}
    <span class="separator"></span>
    <label class="note-select-wrap" title="Select note">
      <AppIcon name="notes" size={14} />
      <select
        class="note-select"
        aria-label="Select note"
        value={selectedNoteId ?? ""}
        onchange={(event) => {
          const id = Number(event.currentTarget.value);
          if (Number.isFinite(id)) onSelectNote(id);
        }}
      >
        {#if notes.length === 0}<option value="">No notes</option>{/if}
        {#each notes as note (note.id)}
          <option value={note.id}>{note.title || "Untitled"}</option>
        {/each}
      </select>
    </label>

    <span class="separator"></span>
    <div class="control-group" aria-label="Notes display controls">
      <button class="icon-btn" class:active={wordWraps.note} onclick={() => onToggleWrap("note")} title="Toggle word wrap for Notes" aria-label="Toggle word wrap for Notes"><AppIcon name="wrap" /></button>
      <button class="icon-btn" class:active={showWhitespaces.note} onclick={() => onToggleWhitespace("note")} title="Show or hide whitespace characters" aria-label="Show or hide whitespace characters"><AppIcon name="whitespace" /></button>
    </div>
  {/if}

  <div class="spacer"></div>
  <button class="icon-btn" class:active={onTop} onclick={onToggleOnTop} title="Always on top" aria-label="Always on top">
    <AppIcon name="pin" />
  </button>
  <button class="full-btn" onclick={onToggleCompact} title="Exit compact mode" aria-label="Exit compact mode"><AppIcon name="expand" /></button>
</div>

<style>
  .compact-bar {
    display: flex;
    align-items: center;
    min-width: 0;
    overflow: visible;
    position: relative;
    z-index: 200;
    height: 26px;
    padding: 0 3px;
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
    gap: 2px;
    flex-shrink: 0;
  }
  .compact-tabs { display: flex; align-items: stretch; height: 100%; gap: 1px; }
  .icon-btn, .full-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 3px;
    height: 22px;
    border: 0;
    border-radius: 3px;
    background: transparent;
    color: var(--fg2);
    font: inherit;
    font-size: 10px;
    cursor: pointer;
    white-space: nowrap;
    line-height: 1;
  }
  .icon-btn { display: grid; place-items: center; width: 24px; padding: 0; }
  .full-btn { width: 24px; padding: 0; }
  .icon-btn:hover, .full-btn:hover { background: var(--btn-hover); color: var(--fg); }
  .icon-btn:disabled { opacity: 0.35; cursor: default; }
  .icon-btn.active { background: color-mix(in srgb, var(--accent) 20%, transparent); color: var(--accent); }
  .control-group { display: inline-flex; align-items: center; overflow: hidden; border: 1px solid var(--border); border-radius: 4px; flex: 0 0 auto; }
  .control-group .icon-btn { width: 23px; border-right: 1px solid var(--border); border-radius: 0; }
  .control-group .icon-btn:last-child { border-right: 0; }
  .tab-btn.active { box-shadow: inset 0 -2px var(--accent); }
  .separator { width: 1px; height: 16px; margin: 0 2px; background: var(--border); }
  .dropdown-wrapper { position: relative; min-width: 0; }
  .dropdown-trigger {
    display: block;
    max-width: 100px;
    height: 20px;
    padding: 0 5px;
    overflow: hidden;
    border: 1px solid var(--border);
    border-radius: 3px;
    background: var(--combo-bg);
    color: var(--combo-fg);
    font: inherit;
    font-size: 10px;
    text-overflow: ellipsis;
    white-space: nowrap;
    cursor: pointer;
  }
  .dropdown-menu {
    position: absolute;
    top: calc(100% + 2px);
    left: 0;
    z-index: 100;
    min-width: 180px;
    max-height: 250px;
    overflow-y: auto;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--bg3);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  }
  .right-menu { right: 0; left: auto; }
  .dropdown-filter {
    width: 100%;
    padding: 4px 6px;
    border: 0;
    border-bottom: 1px solid var(--border);
    outline: 0;
    background: var(--bg2);
    color: var(--fg);
    font: inherit;
    font-size: 11px;
  }
  .dropdown-item {
    display: block;
    width: 100%;
    padding: 4px 8px;
    border: 0;
    background: transparent;
    color: var(--fg);
    font: inherit;
    font-size: 11px;
    text-align: left;
    cursor: pointer;
  }
  .dropdown-item:hover { background: var(--btn-hover); }
  .arrow { color: var(--fg2); font-size: 11px; }
  .note-select-wrap { display: flex; align-items: center; gap: 4px; min-width: 0; max-width: 190px; color: var(--fg2); }
  .note-select {
    min-width: 70px;
    max-width: 165px;
    height: 20px;
    padding: 0 20px 0 5px;
    border: 1px solid var(--border);
    border-radius: 3px;
    background: var(--combo-bg);
    color: var(--combo-fg);
    font: inherit;
    font-size: 10px;
  }
  .spacer { flex: 1; min-width: 2px; }

  @media (max-width: 420px) {
    .dropdown-trigger { max-width: 74px; }
    .control-group .icon-btn { width: 22px; }
  }
</style>
