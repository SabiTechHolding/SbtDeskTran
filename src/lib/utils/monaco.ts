import * as monaco from "monaco-editor/esm/vs/editor/editor.api.js";
import "monaco-editor/esm/vs/basic-languages/rust/rust.contribution.js";
import "monaco-editor/esm/vs/basic-languages/python/python.contribution.js";
import "monaco-editor/esm/vs/basic-languages/javascript/javascript.contribution.js";
import "monaco-editor/esm/vs/basic-languages/typescript/typescript.contribution.js";
import "monaco-editor/esm/vs/basic-languages/html/html.contribution.js";
import "monaco-editor/esm/vs/basic-languages/css/css.contribution.js";
import "monaco-editor/esm/vs/basic-languages/markdown/markdown.contribution.js";
import EditorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker";

let configured = false;
let themesDefined = false;

function alpha(color: string, value: string) {
  return `${color}${value}`;
}

export function configureMonaco() {
  if (configured) return;
  configured = true;
  const scope = self as typeof self & {
    MonacoEnvironment?: { getWorker: (_moduleId: string, _label: string) => Worker };
  };
  scope.MonacoEnvironment = { getWorker: () => new EditorWorker() };
}

export function applyMonacoTheme(theme: "dark" | "light") {
  if (!themesDefined) {
    themesDefined = true;
    defineTheme("sbt-app-light", true);
    defineTheme("sbt-app-dark", false);
  }
  monaco.editor.setTheme(theme === "light" ? "sbt-app-light" : "sbt-app-dark");
}

function defineTheme(name: string, light: boolean) {
  const palette = light
    ? {
        background: "#ffffff", foreground: "#1f2328", gutter: "#f6f8fa",
        lineNumber: "#8c959f", lineHighlight: "#eaeef2", selection: "#b6d7ff",
        warning: "#bf8700", add: "#2da44e", addText: "#1a7f37",
        del: "#cf222e", delText: "#a40e26", border: "#d0d7de", secondary: "#656d76",
      }
    : {
        background: "#1a1a1a", foreground: "#e6edf3", gutter: "#141414",
        lineNumber: "#6e7681", lineHighlight: "#242424", selection: "#264f78",
        warning: "#d29922", add: "#238636", addText: "#56d364",
        del: "#da3633", delText: "#ff7b72", border: "#30363d", secondary: "#8b949e",
      };
  monaco.editor.defineTheme(name, {
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
      "editor.findMatchBackground": alpha(palette.warning, "99"),
      "editor.findMatchHighlightBackground": alpha(palette.warning, "55"),
      "editorWidget.background": palette.background,
      "editorWidget.foreground": palette.foreground,
      "editorWidget.border": palette.border,
      "input.background": palette.gutter,
      "input.foreground": palette.foreground,
      "input.border": palette.border,
      "focusBorder": palette.warning,
      "diffEditor.insertedTextBackground": alpha(palette.add, "66"),
      "diffEditor.removedTextBackground": alpha(palette.del, "66"),
      "diffEditor.insertedLineBackground": alpha(palette.add, "22"),
      "diffEditor.removedLineBackground": alpha(palette.del, "22"),
      "diffEditorGutter.insertedLineBackground": alpha(palette.add, "33"),
      "diffEditorGutter.removedLineBackground": alpha(palette.del, "33"),
      "diffEditorOverview.insertedForeground": palette.addText,
      "diffEditorOverview.removedForeground": palette.delText,
      "diffEditor.diagonalFill": alpha(palette.secondary, "33"),
      "diffEditor.border": palette.border,
      "diffEditor.unchangedRegionBackground": palette.gutter,
      "diffEditor.unchangedCodeBackground": alpha(palette.lineHighlight, "88"),
      "scrollbarSlider.background": alpha(palette.secondary, "44"),
      "scrollbarSlider.hoverBackground": alpha(palette.secondary, "77"),
      "scrollbarSlider.activeBackground": alpha(palette.secondary, "99"),
    },
  });
}

export function currentAppTheme(): "dark" | "light" {
  const root = document.querySelector<HTMLElement>(".app-root");
  return root?.dataset.theme === "light" ? "light" : "dark";
}

export { monaco };
