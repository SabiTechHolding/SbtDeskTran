<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import * as monaco from "monaco-editor/esm/vs/editor/editor.api.js";
  import "monaco-editor/esm/vs/basic-languages/rust/rust.contribution.js";
  import "monaco-editor/esm/vs/basic-languages/python/python.contribution.js";
  import "monaco-editor/esm/vs/basic-languages/javascript/javascript.contribution.js";
  import "monaco-editor/esm/vs/basic-languages/typescript/typescript.contribution.js";
  import "monaco-editor/esm/vs/basic-languages/html/html.contribution.js";
  import "monaco-editor/esm/vs/basic-languages/css/css.contribution.js";
  import "monaco-editor/esm/vs/basic-languages/markdown/markdown.contribution.js";
  import EditorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker";
  import { saveSetting } from "../stores/settings";
  import { installMonacoFindTooltip } from "../utils/monacoFindTooltip";

  interface InlineToken {
    text: string;
    kind: "equal" | "insert" | "delete";
  }

  interface DiffLine {
    kind: string;
    left_text: string;
    right_text: string;
    left_present: boolean;
    right_present: boolean;
    left_tokens: InlineToken[];
    right_tokens: InlineToken[];
  }

  type SearchFlags = {
    caseSensitive: boolean;
    wholeWord: boolean;
    regex: boolean;
  };

  type SearchEntry = {
    side: "left" | "right";
    range: monaco.Range;
  };

  type InlineSpan = {
    text: string;
    start: number;
    end: number;
  };

  type MonacoFindState = {
    readonly isRevealed: boolean;
    onFindReplaceStateChange: (listener: (event: { isRevealed?: boolean }) => void) => monaco.IDisposable;
  };

  type MonacoFindController = {
    getState: () => MonacoFindState;
    closeFindWidget: () => void;
  };

  let {
    leftValue = "",
    rightValue = "",
    fontSize = 11,
    wordWrap = true,
    theme = "dark",
    wordDiff = true,
    ignoreWhitespace = false,
    showWhitespace = false,
    diffAlgorithm = "legacy",
    showCenterControls = false,
    sashRatio = 0.5,
    diffData = [] as DiffLine[],
    onChangeLeft,
    onChangeRight,
    onCursorChange,
    onFindVisibilityChange,
    onDetailChange,
    onZoom,
  }: {
    leftValue?: string;
    rightValue?: string;
    fontSize?: number;
    wordWrap?: boolean;
    theme?: "dark" | "light";
    wordDiff?: boolean;
    ignoreWhitespace?: boolean;
    showWhitespace?: boolean;
    diffAlgorithm?: "legacy" | "advanced";
    showCenterControls?: boolean;
    sashRatio?: number;
    diffData?: DiffLine[];
    onChangeLeft?: (text: string) => void;
    onChangeRight?: (text: string) => void;
    onCursorChange?: (side: string, line: number, col: number, selLen: number, chars: number) => void;
    onFindVisibilityChange?: (side: "left" | "right", visible: boolean) => void;
    onDetailChange?: (
      left: string,
      right: string,
      kind: string,
      leftTokens: InlineToken[],
      rightTokens: InlineToken[],
    ) => void;
    onZoom?: (delta: number) => void;
  } = $props();

  let container: HTMLDivElement;
  let diffEditor: monaco.editor.IStandaloneDiffEditor | undefined;
  let leftModel: monaco.editor.ITextModel | undefined;
  let rightModel: monaco.editor.ITextModel | undefined;
  let leftSearchDecorations: monaco.editor.IEditorDecorationsCollection | undefined;
  let rightSearchDecorations: monaco.editor.IEditorDecorationsCollection | undefined;
  let leftFocusDecorations: monaco.editor.IEditorDecorationsCollection | undefined;
  let rightFocusDecorations: monaco.editor.IEditorDecorationsCollection | undefined;
  let leftWhitespaceDecorations: monaco.editor.IEditorDecorationsCollection | undefined;
  let rightWhitespaceDecorations: monaco.editor.IEditorDecorationsCollection | undefined;
  let leftInlineDecorations: monaco.editor.IEditorDecorationsCollection | undefined;
  let rightInlineDecorations: monaco.editor.IEditorDecorationsCollection | undefined;
  let mounted = $state(false);
  let applyingExternalLeft = false;
  let applyingExternalRight = false;
  let activeSide: "left" | "right" = "left";
  let focusedLine: { side: "left" | "right"; lineNumber: number } | null = null;
  let searchEntries: SearchEntry[] = [];
  let findIndex = -1;
  let lastFindSignature = "";
  let layoutSaveTimer: ReturnType<typeof setTimeout> | null = null;
  let themeObserver: MutationObserver | undefined;
  let whitespaceObserver: MutationObserver | undefined;
  let disposeFindTooltip: (() => void) | undefined;
  let whitespaceFrame = 0;
  let inlineHighlightFrame = 0;
  const disposables: monaco.IDisposable[] = [];

  const WORD_SEPARATORS = "`~!@#$%^&*()-=+[{]}\\|;:'\",.<>/?";

  function configureWorker() {
    const scope = self as typeof self & {
      MonacoEnvironment?: {
        getWorker: (_moduleId: string, _label: string) => Worker;
      };
    };
    scope.MonacoEnvironment = {
      getWorker: () => new EditorWorker(),
    };
  }

  function withAlpha(color: string, alpha: string) {
    if (/^#[0-9a-f]{3}$/i.test(color)) {
      const [r, g, b] = color.slice(1).split("");
      return `#${r}${r}${g}${g}${b}${b}${alpha}`;
    }
    if (/^#[0-9a-f]{6}$/i.test(color)) return `${color}${alpha}`;
    return color;
  }

  function applyTheme() {
    const light = theme === "light";
    const themeName = light ? "sbt-diff-light" : "sbt-diff-dark";
    const palette = light
      ? {
          background: "#ffffff",
          foreground: "#1e1e1e",
          gutter: "#f6f8fa",
          lineNumber: "#a0a0a0",
          lineHighlight: "#e8e8e8",
          selection: "#cce8ff",
          warning: "#b8860b",
          addInline: "#34a853",
          addForeground: "#1a4a2a",
          deleteInline: "#d93025",
          deleteForeground: "#5c1010",
          border: "#d1d1d1",
          secondary: "#5a5a5a",
        }
      : {
          background: "#1a1a1a",
          foreground: "#e8e8e8",
          gutter: "#141414",
          lineNumber: "#555555",
          lineHighlight: "#252525",
          selection: "#3a3a3a",
          warning: "#c8963e",
          addInline: "#1a6b1a",
          addForeground: "#87d987",
          deleteInline: "#8b1a1a",
          deleteForeground: "#f08080",
          border: "#333333",
          secondary: "#909090",
        };
    monaco.editor.defineTheme(themeName, {
      base: light ? "vs" : "vs-dark",
      inherit: true,
      rules: [],
      colors: {
        "editor.background": palette.background,
        "editor.foreground": palette.foreground,
        "editorGutter.background": palette.gutter,
        "editorLineNumber.foreground": palette.lineNumber,
        "editorLineNumber.activeForeground": palette.foreground,
        "editor.lineHighlightBackground": palette.lineHighlight,
        "editor.selectionBackground": palette.selection,
        "editorCursor.foreground": palette.foreground,
        "editor.findMatchBackground": palette.warning,
        "editor.findMatchHighlightBackground": withAlpha(palette.warning, "88"),
        "diffEditor.insertedTextBackground": withAlpha(palette.addInline, "55"),
        "diffEditor.removedTextBackground": withAlpha(palette.deleteInline, "55"),
        "diffEditor.insertedLineBackground": withAlpha(palette.addInline, "20"),
        "diffEditor.removedLineBackground": withAlpha(palette.deleteInline, "20"),
        "diffEditorGutter.insertedLineBackground": withAlpha(palette.addInline, "28"),
        "diffEditorGutter.removedLineBackground": withAlpha(palette.deleteInline, "28"),
        "diffEditorOverview.insertedForeground": palette.addForeground,
        "diffEditorOverview.removedForeground": palette.deleteForeground,
        "diffEditor.diagonalFill": withAlpha(palette.secondary, "33"),
        "diffEditor.border": palette.border,
        "diffEditor.unchangedRegionBackground": palette.gutter,
        "diffEditor.unchangedCodeBackground": withAlpha(palette.lineHighlight, "66"),
        "scrollbarSlider.background": withAlpha(palette.secondary, "44"),
        "scrollbarSlider.hoverBackground": withAlpha(palette.secondary, "77"),
        "scrollbarSlider.activeBackground": withAlpha(palette.secondary, "99"),
      },
    });
    monaco.editor.setTheme(themeName);
  }

  function detectLanguage(text: string) {
    const sample = text.trimStart();
    if (/^(use|mod|pub|fn|impl|struct|enum|trait)\b/m.test(sample) || /\blet\s+mut\b/.test(sample)) return "rust";
    if (/^(from\s+\S+\s+import|import\s+\S+|def\s+\w+|class\s+\w+):?/m.test(sample)) return "python";
    if (/^\s*[{[]/.test(sample)) {
      try {
        JSON.parse(text);
        return "json";
      } catch {
        // Keep detecting below.
      }
    }
    if (/^<(!doctype|html|[A-Za-z][\w:-]*[\s>])/i.test(sample)) return "html";
    if (/^(#\s|##\s|```|---\s*$)/m.test(sample)) return "markdown";
    if (/\b(interface|type|const|let|function|export|import)\b/.test(sample)) return "typescript";
    if (/[.#][\w-]+\s*\{[^}]*:[^}]*\}/s.test(sample)) return "css";
    return "plaintext";
  }

  function updateModelLanguage() {
    if (!leftModel || !rightModel) return;
    const language = detectLanguage(`${leftModel.getValue()}\n${rightModel.getValue()}`);
    monaco.editor.setModelLanguage(leftModel, language);
    monaco.editor.setModelLanguage(rightModel, language);
  }

  function editorOptions(): monaco.editor.IDiffEditorOptions {
    return {
      automaticLayout: true,
      originalEditable: true,
      readOnly: false,
      renderSideBySide: true,
      useInlineViewWhenSpaceIsLimited: false,
      enableSplitViewResizing: true,
      splitViewDefaultRatio: Math.max(0.1, Math.min(0.9, sashRatio)),
      diffAlgorithm,
      maxComputationTime: 0,
      ignoreTrimWhitespace: ignoreWhitespace,
      diffWordWrap: wordWrap ? "on" : "off",
      wordWrap: wordWrap ? "on" : "off",
      renderWhitespace: showWhitespace ? "all" : "none",
      renderIndicators: showCenterControls,
      renderMarginRevertIcon: showCenterControls,
      renderGutterMenu: showCenterControls,
      renderOverviewRuler: true,
      glyphMargin: false,
      lineNumbers: "on",
      lineNumbersMinChars: 3,
      minimap: { enabled: false },
      overviewRulerLanes: 2,
      scrollBeyondLastLine: false,
      roundedSelection: false,
      smoothScrolling: false,
      mouseWheelZoom: false,
      fontFamily: "Consolas, 'JetBrains Mono', monospace",
      fontWeight: "400",
      fontSize,
      lineHeight: 0,
      padding: { top: 6, bottom: 6 },
      renderLineHighlight: "all",
      renderLineHighlightOnlyWhenFocus: true,
      contextmenu: true,
      fixedOverflowWidgets: true,
      stickyScroll: { enabled: false },
      bracketPairColorization: { enabled: false },
      guides: { indentation: false, bracketPairs: false },
      hideUnchangedRegions: {
        enabled: true,
        contextLineCount: 3,
        minimumLineCount: 8,
        revealLineCount: 20,
      },
    };
  }

  function collectMatches(model: monaco.editor.ITextModel | undefined, query: string, flags: SearchFlags) {
    if (!model || !query) return [] as monaco.editor.FindMatch[];
    try {
      return model.findMatches(
        query,
        false,
        flags.regex,
        flags.caseSensitive,
        flags.wholeWord ? WORD_SEPARATORS : null,
        false,
        10000,
      );
    } catch {
      return [];
    }
  }

  function refreshSearchDecorations(query: string, flags: SearchFlags) {
    const leftMatches = collectMatches(leftModel, query, flags);
    const rightMatches = collectMatches(rightModel, query, flags);
    leftSearchDecorations?.set(leftMatches.map((match) => ({
      range: match.range,
      options: { inlineClassName: "sbt-diff-find-match" },
    })));
    rightSearchDecorations?.set(rightMatches.map((match) => ({
      range: match.range,
      options: { inlineClassName: "sbt-diff-find-match" },
    })));
    searchEntries = [
      ...leftMatches.map((match) => ({ side: "left" as const, range: match.range })),
      ...rightMatches.map((match) => ({ side: "right" as const, range: match.range })),
    ];
  }

  export function search(query: string, flags: SearchFlags, direction: "next" | "prev" | "refresh") {
    refreshSearchDecorations(query, flags);
    const count = searchEntries.length;
    const signature = `${query}|${flags.caseSensitive}|${flags.wholeWord}|${flags.regex}`;
    if (!count) {
      findIndex = -1;
      lastFindSignature = signature;
      return { count: 0, index: 0 };
    }
    if (direction === "refresh") {
      findIndex = signature === lastFindSignature && findIndex >= 0 ? Math.min(findIndex, count - 1) : 0;
      lastFindSignature = signature;
      return { count, index: findIndex + 1 };
    }
    if (signature !== lastFindSignature) findIndex = direction === "next" ? -1 : 0;
    findIndex = (findIndex + (direction === "next" ? 1 : -1) + count) % count;
    lastFindSignature = signature;
    const entry = searchEntries[findIndex];
    const editor = entry.side === "left" ? diffEditor?.getOriginalEditor() : diffEditor?.getModifiedEditor();
    if (editor) {
      activeSide = entry.side;
      editor.setSelection(entry.range);
      editor.revealRangeInCenter(entry.range);
      editor.focus();
    }
    return { count, index: findIndex + 1 };
  }

  export function focusActive() {
    const editor = activeSide === "left" ? diffEditor?.getOriginalEditor() : diffEditor?.getModifiedEditor();
    editor?.focus();
  }

  function findController(editor: monaco.editor.ICodeEditor | undefined) {
    return editor?.getContribution("editor.contrib.findController") as unknown as MonacoFindController | null | undefined;
  }

  function findWidgetVisible(editor: monaco.editor.ICodeEditor | undefined) {
    return findController(editor)?.getState().isRevealed ?? false;
  }

  function syncFindVisibility() {
    if (!diffEditor) return;
    onFindVisibilityChange?.("left", findWidgetVisible(diffEditor.getOriginalEditor()));
    onFindVisibilityChange?.("right", findWidgetVisible(diffEditor.getModifiedEditor()));
  }

  export async function toggleEditorFind(side: "left" | "right") {
    const editor = side === "left" ? diffEditor?.getOriginalEditor() : diffEditor?.getModifiedEditor();
    if (!editor) return false;
    activeSide = side;
    const controller = findController(editor);
    if (controller?.getState().isRevealed) {
      controller.closeFindWidget();
      editor.focus();
      syncFindVisibility();
      return false;
    }
    editor.focus();
    await editor.getAction("actions.find")?.run();
    syncFindVisibility();
    return findWidgetVisible(editor);
  }

  export async function hideEditorFind(side?: "left" | "right") {
    const editors = side === "left"
      ? [diffEditor?.getOriginalEditor()]
      : side === "right"
        ? [diffEditor?.getModifiedEditor()]
        : [diffEditor?.getOriginalEditor(), diffEditor?.getModifiedEditor()];
    for (const editor of editors) findController(editor)?.closeFindWidget();
    syncFindVisibility();
  }

  async function showActiveEditorFind() {
    const editor = activeSide === "left" ? diffEditor?.getOriginalEditor() : diffEditor?.getModifiedEditor();
    if (!editor) return;
    editor.focus();
    await editor.getAction("actions.find")?.run();
    syncFindVisibility();
  }

  function handleFindShortcut(event: KeyboardEvent) {
    if (!(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== "f") return;
    event.preventDefault();
    event.stopPropagation();
    void showActiveEditorFind();
  }

  function diffIndexForRawLine(side: "left" | "right", targetLine: number) {
    let rawLine = 0;
    for (let index = 0; index < diffData.length; index++) {
      const line = diffData[index];
      const present = side === "left" ? line.left_present : line.right_present;
      if (present) rawLine++;
      if (present && rawLine === targetLine) return index;
    }
    return -1;
  }

  function rawLineForDiff(side: "left" | "right", diffIndex: number) {
    if (diffIndex < 0 || diffIndex >= diffData.length) return undefined;
    let rawLine = 0;
    for (let index = 0; index <= diffIndex; index++) {
      const line = diffData[index];
      if (side === "left" ? line.left_present : line.right_present) rawLine++;
    }
    const line = diffData[diffIndex];
    return (side === "left" ? line.left_present : line.right_present) ? rawLine : undefined;
  }

  function focusDecoration(lineNumber: number | undefined): monaco.editor.IModelDeltaDecoration[] {
    if (lineNumber === undefined) return [];
    return [{
      range: new monaco.Range(lineNumber, 1, lineNumber, 1),
      options: {
        isWholeLine: true,
        lineNumberClassName: "sbt-diff-focused-line-number",
        marginClassName: "sbt-diff-focused-margin",
      },
    }];
  }

  function whitespaceEqualDecorations(side: "left" | "right") {
    if (!ignoreWhitespace) return [];
    const decorations: monaco.editor.IModelDeltaDecoration[] = [];
    let rawLine = 0;
    for (const line of diffData) {
      const present = side === "left" ? line.left_present : line.right_present;
      if (!present) continue;
      rawLine++;
      if (line.kind === "equal" && line.left_text !== line.right_text) {
        decorations.push({
          range: new monaco.Range(rawLine, 1, rawLine, 1),
          options: {
            isWholeLine: true,
            className: "sbt-ignore-ws-equal-line",
            marginClassName: "sbt-ignore-ws-equal-margin",
          },
        });
      }
    }
    return decorations;
  }

  function applyWhitespaceDecorations() {
    leftWhitespaceDecorations?.set(whitespaceEqualDecorations("left"));
    rightWhitespaceDecorations?.set(whitespaceEqualDecorations("right"));
  }

  function markWhitespaceChanges() {
    whitespaceFrame = 0;
    if (!container) return;
    for (const element of container.querySelectorAll<HTMLElement>(".char-insert, .char-delete")) {
      element.classList.toggle(
        "sbt-ignore-ws-inline",
        ignoreWhitespace && /^\s+$/u.test(element.textContent ?? ""),
      );
    }
  }

  function scheduleWhitespaceScan() {
    if (whitespaceFrame) return;
    whitespaceFrame = requestAnimationFrame(markWhitespaceChanges);
  }

  function isCjkCharacter(character: string) {
    const codePoint = character.codePointAt(0) ?? 0;
    return (
      (codePoint >= 0x3000 && codePoint <= 0x303f) ||
      (codePoint >= 0x3040 && codePoint <= 0x30ff) ||
      (codePoint >= 0x31f0 && codePoint <= 0x31ff) ||
      (codePoint >= 0x3400 && codePoint <= 0x4dbf) ||
      (codePoint >= 0x4e00 && codePoint <= 0x9fff) ||
      (codePoint >= 0xac00 && codePoint <= 0xd7af) ||
      (codePoint >= 0xff00 && codePoint <= 0xffef) ||
      (codePoint >= 0x20000 && codePoint <= 0x2a6df)
    );
  }

  function tokenizeInline(text: string): InlineSpan[] {
    const spans: InlineSpan[] = [];
    let offset = 0;
    let groupedStart = -1;
    let groupedText = "";

    const flushGrouped = () => {
      if (groupedStart < 0) return;
      spans.push({ text: groupedText, start: groupedStart, end: groupedStart + groupedText.length });
      groupedStart = -1;
      groupedText = "";
    };

    for (const character of text) {
      const length = character.length;
      if (!wordDiff) {
        spans.push({ text: character, start: offset, end: offset + length });
      } else if (!isCjkCharacter(character) && /[\p{L}\p{N}_]/u.test(character)) {
        if (groupedStart < 0) groupedStart = offset;
        groupedText += character;
      } else {
        flushGrouped();
        spans.push({ text: character, start: offset, end: offset + length });
      }
      offset += length;
    }
    flushGrouped();
    return spans;
  }

  function comparableSpans(text: string) {
    return tokenizeInline(text).filter((span) => !(ignoreWhitespace && /^\s+$/u.test(span.text)));
  }

  function changedSpanIndexes(left: InlineSpan[], right: InlineSpan[]) {
    const leftChanged = new Set<number>();
    const rightChanged = new Set<number>();
    const cells = (left.length + 1) * (right.length + 1);

    if (cells > 1_000_000) {
      let prefix = 0;
      while (
        prefix < left.length &&
        prefix < right.length &&
        left[prefix].text === right[prefix].text
      ) prefix++;
      let leftSuffix = left.length - 1;
      let rightSuffix = right.length - 1;
      while (
        leftSuffix >= prefix &&
        rightSuffix >= prefix &&
        left[leftSuffix].text === right[rightSuffix].text
      ) {
        leftSuffix--;
        rightSuffix--;
      }
      for (let index = prefix; index <= leftSuffix; index++) leftChanged.add(index);
      for (let index = prefix; index <= rightSuffix; index++) rightChanged.add(index);
      return { leftChanged, rightChanged };
    }

    const width = right.length + 1;
    const lcs = new Uint32Array(cells);
    for (let leftIndex = left.length - 1; leftIndex >= 0; leftIndex--) {
      for (let rightIndex = right.length - 1; rightIndex >= 0; rightIndex--) {
        const cell = leftIndex * width + rightIndex;
        lcs[cell] = left[leftIndex].text === right[rightIndex].text
          ? lcs[(leftIndex + 1) * width + rightIndex + 1] + 1
          : Math.max(lcs[(leftIndex + 1) * width + rightIndex], lcs[cell + 1]);
      }
    }

    const leftMatched = new Set<number>();
    const rightMatched = new Set<number>();
    let leftIndex = 0;
    let rightIndex = 0;
    while (leftIndex < left.length && rightIndex < right.length) {
      if (left[leftIndex].text === right[rightIndex].text) {
        leftMatched.add(leftIndex++);
        rightMatched.add(rightIndex++);
      } else if (
        lcs[(leftIndex + 1) * width + rightIndex] >=
        lcs[leftIndex * width + rightIndex + 1]
      ) {
        leftIndex++;
      } else {
        rightIndex++;
      }
    }
    for (let index = 0; index < left.length; index++) {
      if (!leftMatched.has(index)) leftChanged.add(index);
    }
    for (let index = 0; index < right.length; index++) {
      if (!rightMatched.has(index)) rightChanged.add(index);
    }
    return { leftChanged, rightChanged };
  }

  function inlineRanges(spans: InlineSpan[], changed: Set<number>) {
    const ranges: Array<{ start: number; end: number }> = [];
    for (let index = 0; index < spans.length; index++) {
      if (!changed.has(index)) continue;
      const span = spans[index];
      const previous = ranges.at(-1);
      if (previous && previous.end === span.start) {
        previous.end = span.end;
      } else {
        ranges.push({ start: span.start, end: span.end });
      }
    }
    return ranges;
  }

  function applyLegacyInlineHighlights() {
    inlineHighlightFrame = 0;
    if (
      diffAlgorithm !== "legacy" ||
      !diffEditor ||
      !leftModel ||
      !rightModel
    ) {
      leftInlineDecorations?.clear();
      rightInlineDecorations?.clear();
      return;
    }

    const leftDecorations: monaco.editor.IModelDeltaDecoration[] = [];
    const rightDecorations: monaco.editor.IModelDeltaDecoration[] = [];
    for (const change of diffEditor.getLineChanges() ?? []) {
      if (change.originalEndLineNumber === 0 || change.modifiedEndLineNumber === 0) continue;
      const originalCount = change.originalEndLineNumber - change.originalStartLineNumber + 1;
      const modifiedCount = change.modifiedEndLineNumber - change.modifiedStartLineNumber + 1;
      const pairCount = Math.min(originalCount, modifiedCount);
      for (let offset = 0; offset < pairCount; offset++) {
        const originalLine = change.originalStartLineNumber + offset;
        const modifiedLine = change.modifiedStartLineNumber + offset;
        const originalText = leftModel.getLineContent(originalLine);
        const modifiedText = rightModel.getLineContent(modifiedLine);
        if (
          ignoreWhitespace &&
          originalText.split(/\s+/u).filter(Boolean).join(" ") ===
            modifiedText.split(/\s+/u).filter(Boolean).join(" ")
        ) continue;

        const leftSpans = comparableSpans(originalText);
        const rightSpans = comparableSpans(modifiedText);
        const { leftChanged, rightChanged } = changedSpanIndexes(leftSpans, rightSpans);
        for (const range of inlineRanges(leftSpans, leftChanged)) {
          leftDecorations.push({
            range: new monaco.Range(originalLine, range.start + 1, originalLine, range.end + 1),
            options: { inlineClassName: "sbt-diff-inline-delete" },
          });
        }
        for (const range of inlineRanges(rightSpans, rightChanged)) {
          rightDecorations.push({
            range: new monaco.Range(modifiedLine, range.start + 1, modifiedLine, range.end + 1),
            options: { inlineClassName: "sbt-diff-inline-insert" },
          });
        }
      }
    }
    leftInlineDecorations?.set(leftDecorations);
    rightInlineDecorations?.set(rightDecorations);
  }

  function scheduleLegacyInlineHighlights() {
    if (inlineHighlightFrame) cancelAnimationFrame(inlineHighlightFrame);
    inlineHighlightFrame = requestAnimationFrame(applyLegacyInlineHighlights);
  }

  function appendDetailToken(tokens: InlineToken[], text: string, kind: InlineToken["kind"]) {
    if (!text) return;
    const previous = tokens.at(-1);
    if (previous?.kind === kind) {
      previous.text += text;
    } else {
      tokens.push({ text, kind });
    }
  }

  function detailTokensForRanges(
    text: string,
    ranges: Array<{ start: number; end: number }>,
    changedKind: "delete" | "insert",
  ) {
    const tokens: InlineToken[] = [];
    let cursor = 0;
    for (const range of ranges) {
      appendDetailToken(tokens, text.slice(cursor, range.start), "equal");
      appendDetailToken(tokens, text.slice(range.start, range.end), changedKind);
      cursor = range.end;
    }
    appendDetailToken(tokens, text.slice(cursor), "equal");
    return tokens;
  }

  function detailTokens(leftText: string, rightText: string, kind: string) {
    if (kind === "delete") {
      return {
        leftTokens: leftText ? [{ text: leftText, kind: "delete" as const }] : [],
        rightTokens: [] as InlineToken[],
      };
    }
    if (kind === "insert") {
      return {
        leftTokens: [] as InlineToken[],
        rightTokens: rightText ? [{ text: rightText, kind: "insert" as const }] : [],
      };
    }
    if (kind !== "replace") {
      return {
        leftTokens: leftText ? [{ text: leftText, kind: "equal" as const }] : [],
        rightTokens: rightText ? [{ text: rightText, kind: "equal" as const }] : [],
      };
    }

    const leftSpans = comparableSpans(leftText);
    const rightSpans = comparableSpans(rightText);
    const { leftChanged, rightChanged } = changedSpanIndexes(leftSpans, rightSpans);
    return {
      leftTokens: detailTokensForRanges(leftText, inlineRanges(leftSpans, leftChanged), "delete"),
      rightTokens: detailTokensForRanges(rightText, inlineRanges(rightSpans, rightChanged), "insert"),
    };
  }

  function linePairForSelection(side: "left" | "right", targetLine: number) {
    if (!diffEditor || !leftModel || !rightModel) return undefined;
    let leftCursor = 1;
    let rightCursor = 1;

    for (const change of diffEditor.getLineChanges() ?? []) {
      const leftCount = change.originalEndLineNumber === 0
        ? 0
        : change.originalEndLineNumber - change.originalStartLineNumber + 1;
      const rightCount = change.modifiedEndLineNumber === 0
        ? 0
        : change.modifiedEndLineNumber - change.modifiedStartLineNumber + 1;
      const leftStart = change.originalEndLineNumber === 0
        ? change.originalStartLineNumber + 1
        : change.originalStartLineNumber;
      const rightStart = change.modifiedEndLineNumber === 0
        ? change.modifiedStartLineNumber + 1
        : change.modifiedStartLineNumber;
      const equalCount = Math.min(leftStart - leftCursor, rightStart - rightCursor);

      if (side === "left" && targetLine >= leftCursor && targetLine < leftCursor + equalCount) {
        return { leftLine: targetLine, rightLine: rightCursor + targetLine - leftCursor, kind: "equal" };
      }
      if (side === "right" && targetLine >= rightCursor && targetLine < rightCursor + equalCount) {
        return { leftLine: leftCursor + targetLine - rightCursor, rightLine: targetLine, kind: "equal" };
      }

      if (side === "left" && leftCount > 0 && targetLine >= leftStart && targetLine < leftStart + leftCount) {
        const offset = targetLine - leftStart;
        return {
          leftLine: targetLine,
          rightLine: offset < rightCount ? rightStart + offset : undefined,
          kind: offset < rightCount ? "replace" : "delete",
        };
      }
      if (side === "right" && rightCount > 0 && targetLine >= rightStart && targetLine < rightStart + rightCount) {
        const offset = targetLine - rightStart;
        return {
          leftLine: offset < leftCount ? leftStart + offset : undefined,
          rightLine: targetLine,
          kind: offset < leftCount ? "replace" : "insert",
        };
      }

      leftCursor = leftStart + leftCount;
      rightCursor = rightStart + rightCount;
    }

    if (side === "left" && targetLine >= leftCursor) {
      const rightLine = rightCursor + targetLine - leftCursor;
      if (rightLine <= rightModel.getLineCount()) {
        return { leftLine: targetLine, rightLine, kind: "equal" };
      }
    }
    if (side === "right" && targetLine >= rightCursor) {
      const leftLine = leftCursor + targetLine - rightCursor;
      if (leftLine <= leftModel.getLineCount()) {
        return { leftLine, rightLine: targetLine, kind: "equal" };
      }
    }
    return undefined;
  }

  function focusDiffLine(side: "left" | "right", lineNumber: number) {
    if (!leftModel || !rightModel) return;
    const model = side === "left" ? leftModel : rightModel;
    const clampedLine = Math.max(1, Math.min(lineNumber, model.getLineCount()));
    activeSide = side;
    focusedLine = { side, lineNumber: clampedLine };
    const pair = linePairForSelection(side, clampedLine);
    if (!pair) return;
    const leftText = pair.leftLine ? leftModel.getLineContent(pair.leftLine) : "";
    const rightText = pair.rightLine ? rightModel.getLineContent(pair.rightLine) : "";
    const kind = pair.kind === "equal" && leftText !== rightText ? "replace" : pair.kind;
    const { leftTokens, rightTokens } = detailTokens(leftText, rightText, kind);
    leftFocusDecorations?.set(focusDecoration(pair.leftLine));
    rightFocusDecorations?.set(focusDecoration(pair.rightLine));
    onDetailChange?.(leftText, rightText, kind, leftTokens, rightTokens);
  }

  function clearFocusDecorations() {
    leftFocusDecorations?.clear();
    rightFocusDecorations?.clear();
  }

  function restoreFocusedDetail() {
    if (!focusedLine) return;
    focusDiffLine(focusedLine.side, focusedLine.lineNumber);
  }

  function scheduleFocusedDetailRestore() {
    requestAnimationFrame(() => restoreFocusedDetail());
  }

  export function refreshFocusedDetail() {
    restoreFocusedDetail();
  }

  export function recompute() {
    if (!diffEditor || !leftModel || !rightModel) return;
    clearFocusDecorations();
    leftInlineDecorations?.clear();
    rightInlineDecorations?.clear();
    diffEditor.updateOptions({
      diffAlgorithm,
      ignoreTrimWhitespace: ignoreWhitespace,
      renderWhitespace: showWhitespace ? "all" : "none",
      maxComputationTime: 0,
      renderIndicators: showCenterControls,
      renderMarginRevertIcon: showCenterControls,
      renderGutterMenu: showCenterControls,
    });
    diffEditor.setModel(null);
    diffEditor.setModel({ original: leftModel, modified: rightModel });
    scheduleFocusedDetailRestore();
  }

  function handleZoomWheel(event: WheelEvent) {
    if (!event.ctrlKey) return;
    event.preventDefault();
    event.stopPropagation();
    onZoom?.(event.deltaY < 0 ? 1 : -1);
  }

  function emitCursor(side: "left" | "right", editor: monaco.editor.ICodeEditor) {
    const position = editor.getPosition();
    const selection = editor.getSelection();
    const model = editor.getModel();
    if (!position || !model) return;
    const selectionLength = selection ? model.getValueInRange(selection).length : 0;
    onCursorChange?.(side, position.lineNumber, position.column, selectionLength, model.getValueLength());
    focusDiffLine(side, position.lineNumber);
  }

  function saveSplitRatio() {
    if (!container || !diffEditor || container.clientWidth < 220) return;
    const originalWidth = diffEditor.getOriginalEditor().getLayoutInfo().width;
    const ratio = originalWidth / container.clientWidth;
    if (ratio > 0.1 && ratio < 0.9) void saveSetting("diff_left_ratio", ratio);
  }

  onMount(() => {
    configureWorker();
    applyTheme();

    leftModel = monaco.editor.createModel(leftValue, detectLanguage(leftValue), monaco.Uri.parse("inmemory://sbt-diff/original"));
    rightModel = monaco.editor.createModel(rightValue, detectLanguage(rightValue), monaco.Uri.parse("inmemory://sbt-diff/modified"));
    diffEditor = monaco.editor.createDiffEditor(container, editorOptions());
    diffEditor.setModel({ original: leftModel, modified: rightModel });

    const leftEditor = diffEditor.getOriginalEditor();
    const rightEditor = diffEditor.getModifiedEditor();
    leftSearchDecorations = leftEditor.createDecorationsCollection();
    rightSearchDecorations = rightEditor.createDecorationsCollection();
    leftFocusDecorations = leftEditor.createDecorationsCollection();
    rightFocusDecorations = rightEditor.createDecorationsCollection();
    leftWhitespaceDecorations = leftEditor.createDecorationsCollection();
    rightWhitespaceDecorations = rightEditor.createDecorationsCollection();
    leftInlineDecorations = leftEditor.createDecorationsCollection();
    rightInlineDecorations = rightEditor.createDecorationsCollection();

    disposables.push(
      diffEditor.onDidUpdateDiff(() => {
        scheduleLegacyInlineHighlights();
        scheduleFocusedDetailRestore();
      }),
      leftModel.onDidChangeContent(() => {
        if (!applyingExternalLeft) onChangeLeft?.(leftModel?.getValue() ?? "");
        scheduleFocusedDetailRestore();
      }),
      rightModel.onDidChangeContent(() => {
        if (!applyingExternalRight) onChangeRight?.(rightModel?.getValue() ?? "");
        scheduleFocusedDetailRestore();
      }),
      leftEditor.onDidFocusEditorText(() => {
        activeSide = "left";
        emitCursor("left", leftEditor);
      }),
      rightEditor.onDidFocusEditorText(() => {
        activeSide = "right";
        emitCursor("right", rightEditor);
      }),
      leftEditor.onDidChangeCursorPosition(() => {
        if (leftEditor.hasTextFocus()) emitCursor("left", leftEditor);
      }),
      rightEditor.onDidChangeCursorPosition(() => {
        if (rightEditor.hasTextFocus()) emitCursor("right", rightEditor);
      }),
      leftEditor.onMouseDown((event) => {
        if (event.target.position) focusDiffLine("left", event.target.position.lineNumber);
      }),
      rightEditor.onMouseDown((event) => {
        if (event.target.position) focusDiffLine("right", event.target.position.lineNumber);
      }),
      leftEditor.onDidLayoutChange(() => {
        if (layoutSaveTimer) clearTimeout(layoutSaveTimer);
        layoutSaveTimer = setTimeout(saveSplitRatio, 500);
      }),
    );
    for (const [side, editor] of [["left", leftEditor], ["right", rightEditor]] as const) {
      const state = findController(editor)?.getState();
      if (state) {
        disposables.push(state.onFindReplaceStateChange((event) => {
          if (event.isRevealed) onFindVisibilityChange?.(side, state.isRevealed);
        }));
      }
    }

    themeObserver = new MutationObserver(() => {
      applyTheme();
      diffEditor?.layout();
    });
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    whitespaceObserver = new MutationObserver(scheduleWhitespaceScan);
    whitespaceObserver.observe(container, { childList: true, subtree: true, characterData: true });
    container.addEventListener("wheel", handleZoomWheel, { capture: true, passive: false });
    container.addEventListener("keydown", handleFindShortcut, { capture: true });
    disposeFindTooltip = installMonacoFindTooltip(container);
    updateModelLanguage();
    scheduleWhitespaceScan();
    scheduleLegacyInlineHighlights();
    mounted = true;
    syncFindVisibility();
  });

  $effect(() => {
    if (!mounted || !leftModel) return;
    const value = leftValue;
    if (leftModel.getValue() !== value) {
      applyingExternalLeft = true;
      leftModel.setValue(value);
      applyingExternalLeft = false;
      updateModelLanguage();
    }
  });

  $effect(() => {
    if (!mounted || !rightModel) return;
    const value = rightValue;
    if (rightModel.getValue() !== value) {
      applyingExternalRight = true;
      rightModel.setValue(value);
      applyingExternalRight = false;
      updateModelLanguage();
    }
  });

  $effect(() => {
    if (!mounted || !diffEditor) return;
    theme;
    applyTheme();
    diffEditor.layout();
  });

  $effect(() => {
    if (!mounted || !diffEditor) return;
    diffEditor.updateOptions({
      fontSize,
      fontWeight: "400",
      wordWrap: wordWrap ? "on" : "off",
      diffWordWrap: wordWrap ? "on" : "off",
      ignoreTrimWhitespace: ignoreWhitespace,
      renderWhitespace: showWhitespace ? "all" : "none",
      diffAlgorithm,
      maxComputationTime: 0,
      renderIndicators: showCenterControls,
      renderMarginRevertIcon: showCenterControls,
      renderGutterMenu: showCenterControls,
    });
  });

  $effect(() => {
    if (!mounted) return;
    diffData;
    wordDiff;
    ignoreWhitespace;
    showWhitespace;
    diffAlgorithm;
    showCenterControls;
    applyWhitespaceDecorations();
    scheduleWhitespaceScan();
    scheduleLegacyInlineHighlights();
    scheduleFocusedDetailRestore();
  });

  onDestroy(() => {
    if (layoutSaveTimer) clearTimeout(layoutSaveTimer);
    if (whitespaceFrame) cancelAnimationFrame(whitespaceFrame);
    if (inlineHighlightFrame) cancelAnimationFrame(inlineHighlightFrame);
    themeObserver?.disconnect();
    whitespaceObserver?.disconnect();
    disposeFindTooltip?.();
    container?.removeEventListener("wheel", handleZoomWheel, { capture: true });
    container?.removeEventListener("keydown", handleFindShortcut, { capture: true });
    for (const disposable of disposables) disposable.dispose();
    leftSearchDecorations?.clear();
    rightSearchDecorations?.clear();
    leftFocusDecorations?.clear();
    rightFocusDecorations?.clear();
    leftWhitespaceDecorations?.clear();
    rightWhitespaceDecorations?.clear();
    leftInlineDecorations?.clear();
    rightInlineDecorations?.clear();
    diffEditor?.setModel(null);
    diffEditor?.dispose();
    leftModel?.dispose();
    rightModel?.dispose();
  });
</script>

<div
  bind:this={container}
  class="monaco-diff-root"
  class:center-controls={showCenterControls}
  class:ignore-whitespace={ignoreWhitespace}
  class:legacy-algorithm={diffAlgorithm === "legacy"}
></div>

<style>
  .monaco-diff-root {
    flex: 1;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
  }

  .monaco-diff-root :global(.sbt-diff-find-match) {
    background: color-mix(in srgb, var(--warning) 45%, transparent);
    border-radius: 2px;
  }

  .monaco-diff-root :global(.find-widget) {
    z-index: 40 !important;
  }

  .monaco-diff-root :global(.monaco-hover),
  .monaco-diff-root :global(.context-view) {
    z-index: 80 !important;
  }

  /* Monaco may leave an existing revert-arrow view zone mounted after
     renderMarginRevertIcon is changed at runtime. Keep the DOM strictly in
     sync with the Actions toggle (and always hidden in compact mode). */
  .monaco-diff-root:not(.center-controls) :global(.arrow-revert-change),
  .monaco-diff-root:not(.center-controls) :global(.insert-sign),
  .monaco-diff-root:not(.center-controls) :global(.delete-sign) {
    display: none !important;
  }

  .monaco-diff-root :global(.sbt-diff-focused-line-number) {
    background: var(--accent) !important;
    color: var(--bg) !important;
    font-weight: 700 !important;
  }

  .monaco-diff-root :global(.sbt-diff-focused-margin) {
    background: color-mix(in srgb, var(--accent) 24%, transparent) !important;
  }

  .monaco-diff-root :global(.sbt-ignore-ws-inline) {
    background: transparent !important;
    border-color: transparent !important;
  }

  .monaco-diff-root :global(.sbt-ignore-ws-equal-line) {
    background: var(--bg) !important;
    color: inherit !important;
  }

  .monaco-diff-root :global(.sbt-ignore-ws-equal-margin) {
    background: var(--diff-line-num-bg) !important;
  }

  .monaco-diff-root.legacy-algorithm :global(.char-delete),
  .monaco-diff-root.legacy-algorithm :global(.char-insert) {
    background: transparent !important;
    border-color: transparent !important;
  }

  .monaco-diff-root.legacy-algorithm :global(.sbt-diff-inline-delete) {
    background: color-mix(in srgb, var(--diff-del-inline) 58%, transparent);
    border-radius: 2px;
  }

  .monaco-diff-root.legacy-algorithm :global(.sbt-diff-inline-insert) {
    background: color-mix(in srgb, var(--diff-add-inline) 58%, transparent);
    border-radius: 2px;
  }
</style>
