<script lang="ts">
  import { onMount } from "svelte";
  import { loadSettings, saveSetting, type AppSettings } from "../stores/settings";
  import { installFindTooltip } from "../utils/monacoFindTooltip";

  let {
    value = "",
    settingsPrefix,
    onSearch,
    onClose,
  }: {
    value?: string;
    settingsPrefix: "tran" | "diff";
    onSearch?: (
      query: string,
      flags: { caseSensitive: boolean; wholeWord: boolean; regex: boolean },
      direction: "next" | "prev" | "refresh",
    ) => { count: number; index: number } | void;
    onClose?: () => void;
  } = $props();

  let query = $state.raw("");

  $effect(() => {
    query = value;
  });
  let caseSensitive = $state(false);
  let wholeWord = $state(false);
  let regex = $state(false);
  let matchCount = $state(0);
  let currentIndex = $state(0);

  let inputEl: HTMLInputElement;
  let container: HTMLDivElement;

  onMount(async () => {
    const settings = await loadSettings();
    caseSensitive = settings[`${settingsPrefix}_find_case`];
    wholeWord = settings[`${settingsPrefix}_find_word`];
    regex = settings[`${settingsPrefix}_find_regex`];
  });

  onMount(() => installFindTooltip(container, "[data-find-tooltip]"));

  export function focus() {
    queueMicrotask(() => {
      inputEl?.focus();
      inputEl?.select();
    });
  }

  export function refresh() {
    const result = onSearch?.(query, { caseSensitive, wholeWord, regex }, "refresh");
    matchCount = result?.count ?? 0;
    currentIndex = result?.index ?? 0;
  }

  function doSearch(dir: "next" | "prev" = "next") {
    const result = onSearch?.(query, { caseSensitive, wholeWord, regex }, dir);
    matchCount = result?.count ?? 0;
    currentIndex = result?.index ?? 0;
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      doSearch(e.shiftKey ? "prev" : "next");
    } else if (e.key === "Escape") {
      e.preventDefault();
      close();
    }
  }

  function saveOption(option: "case" | "word" | "regex", enabled: boolean) {
    const key = `${settingsPrefix}_find_${option}` as keyof AppSettings;
    void saveSetting(key, enabled as AppSettings[typeof key]);
    refresh();
  }

  function toggleOption(option: "case" | "word" | "regex") {
    if (option === "case") {
      caseSensitive = !caseSensitive;
      saveOption(option, caseSensitive);
    } else if (option === "word") {
      wholeWord = !wholeWord;
      saveOption(option, wholeWord);
    } else {
      regex = !regex;
      saveOption(option, regex);
    }
  }

  function close() {
    query = "";
    onSearch?.("", { caseSensitive, wholeWord, regex }, "next");
    matchCount = 0;
    currentIndex = 0;
    onClose?.();
  }

</script>

<div class="find-bar" bind:this={container} role="search" aria-label="Search current tab">
  <div class="find-input-row">
    <svg class="find-icon" viewBox="0 0 24 24" width="14" height="14">
      <path fill="currentColor" d="M15.5 14h-.79l-.28-.27A6.47 6.47 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
    </svg>
    <div class="find-input-shell">
      <input
        bind:this={inputEl}
        class="find-input"
        type="text"
        bind:value={query}
        placeholder="Find"
        aria-label="Find"
        onkeydown={handleKeyDown}
        oninput={refresh}
      />
      <div class="find-options" aria-label="Search options">
        <button
          type="button"
          class="find-option"
          class:checked={caseSensitive}
          aria-pressed={caseSensitive}
          aria-label="Match Case"
          data-find-tooltip
          onclick={() => toggleOption("case")}
        >Aa</button>
        <button
          type="button"
          class="find-option whole-word"
          class:checked={wholeWord}
          aria-pressed={wholeWord}
          aria-label="Match Whole Word"
          data-find-tooltip
          onclick={() => toggleOption("word")}
        >ab</button>
        <button
          type="button"
          class="find-option regex"
          class:checked={regex}
          aria-pressed={regex}
          aria-label="Use Regular Expression"
          data-find-tooltip
          onclick={() => toggleOption("regex")}
        >.*</button>
      </div>
    </div>
    <span class="match-info" class:no-results={matchCount === 0 && !!query}>
      {#if matchCount > 0}
        {currentIndex} of {matchCount}
      {:else}
        No results
      {/if}
    </span>
    <button type="button" class="find-action" onclick={() => doSearch("prev")} disabled={matchCount === 0} aria-label="Previous Match (Shift+Enter)" data-find-tooltip>
      <svg viewBox="0 0 16 16" aria-hidden="true"><path d="m3.7 9.7 4.3-4.3 4.3 4.3-.7.7L8 6.8l-3.6 3.6-.7-.7Z" /></svg>
    </button>
    <button type="button" class="find-action" onclick={() => doSearch("next")} disabled={matchCount === 0} aria-label="Next Match (Enter)" data-find-tooltip>
      <svg viewBox="0 0 16 16" aria-hidden="true"><path d="m3.7 6.3.7-.7L8 9.2l3.6-3.6.7.7L8 10.6 3.7 6.3Z" /></svg>
    </button>
    <button type="button" class="find-action find-close" onclick={close} aria-label="Close (Escape)" data-find-tooltip>
      <svg viewBox="0 0 16 16" aria-hidden="true"><path d="m8 8.7 3.15 3.15.7-.7L8.7 8l3.15-3.15-.7-.7L8 7.3 4.85 4.15l-.7.7L7.3 8l-3.15 3.15.7.7L8 8.7Z" /></svg>
    </button>
  </div>
</div>

<style>
  .find-bar {
    display: flex;
    align-items: center;
    min-width: 0;
    height: 33px;
    padding: 3px 6px;
    background: var(--bg3);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  .find-input-row {
    display: flex;
    align-items: center;
    gap: 0;
    width: 100%;
    min-width: 0;
  }

  .find-icon {
    color: var(--fg2);
    flex-shrink: 0;
    margin-right: 2px;
  }

  .find-input-shell {
    display: flex;
    align-items: center;
    flex: 1;
    min-width: 80px;
    height: 25px;
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 2px;
    overflow: hidden;
  }

  .find-input-shell:focus-within { border-color: var(--accent); }

  .find-input {
    flex: 1;
    min-width: 30px;
    height: 23px;
    padding: 2px 5px;
    background: transparent;
    color: var(--fg);
    border: 0;
    font-family: inherit;
    font-size: 12px;
    outline: none;
  }

  .match-info {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: none;
    height: 25px;
    margin-left: 3px;
    padding: 2px 0 0 2px;
    font-size: 12px;
    line-height: 23px;
    color: var(--find-control-fg);
    white-space: nowrap;
    min-width: 69px;
    text-align: center;
  }

  .match-info.no-results { color: var(--find-no-results); }

  .find-action,
  .find-option {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    margin-left: 3px;
    padding: 3px;
    background: transparent;
    border: 0;
    color: var(--find-control-fg);
    font-family: inherit;
    cursor: pointer;
    border-radius: 5px;
  }

  .find-action svg { width: 16px; height: 16px; min-width: 16px; fill: currentColor; overflow: visible; }
  .find-action:hover:not(:disabled),
  .find-option:hover { background: var(--find-control-hover); color: var(--find-control-fg); }
  .find-action:focus-visible,
  .find-option:focus-visible { outline: 1px solid var(--accent); outline-offset: -1px; }
  .find-action:disabled { color: var(--find-control-disabled); opacity: 1; cursor: default; }

  .find-options {
    display: flex;
    align-items: center;
    gap: 0;
    padding-right: 2px;
    flex-shrink: 0;
  }

  .find-option {
    width: 21px;
    height: 21px;
    margin-left: 0;
    padding: 0;
    font-size: 11px;
  }

  .find-option.checked {
    color: var(--accent);
    background: color-mix(in srgb, var(--accent) 18%, transparent);
    outline: 1px solid color-mix(in srgb, var(--accent) 58%, transparent);
    outline-offset: -1px;
  }

  .whole-word { text-decoration: underline; text-underline-offset: 2px; }
  .regex { font-weight: 600; letter-spacing: -0.5px; }

  @media (max-width: 520px) {
    .find-bar { padding-inline: 4px; }
    .find-input-row { gap: 1px; }
    .find-icon { display: none; }
    .match-info { min-width: 42px; padding-inline: 2px; }
  }
</style>
