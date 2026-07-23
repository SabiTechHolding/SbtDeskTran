import { monaco } from "./monaco";

export function installNotepadPlusPlusKeybindings(editor: monaco.editor.ICodeEditor) {
  const { CtrlCmd, Shift } = monaco.KeyMod;
  const bind = (keybinding: number, actionId?: string) => {
    editor.addCommand(keybinding, () => {
      if (actionId) void editor.getAction(actionId)?.run();
    });
  };

  // Command Palette is intentionally unavailable in this desktop tool.
  bind(monaco.KeyCode.F1);
  bind(CtrlCmd | Shift | monaco.KeyCode.KeyP);

  bind(CtrlCmd | monaco.KeyCode.KeyD, "editor.action.copyLinesDownAction");
  bind(CtrlCmd | monaco.KeyCode.KeyL, "editor.action.clipboardCutAction");
  bind(CtrlCmd | Shift | monaco.KeyCode.KeyL, "editor.action.deleteLines");
  bind(CtrlCmd | monaco.KeyCode.KeyT, "editor.action.moveLinesUpAction");
  bind(CtrlCmd | Shift | monaco.KeyCode.UpArrow, "editor.action.moveLinesUpAction");
  bind(CtrlCmd | Shift | monaco.KeyCode.DownArrow, "editor.action.moveLinesDownAction");
  bind(CtrlCmd | monaco.KeyCode.KeyJ, "editor.action.joinLines");
  bind(CtrlCmd | monaco.KeyCode.KeyQ, "editor.action.commentLine");
  bind(CtrlCmd | Shift | monaco.KeyCode.KeyQ, "editor.action.blockComment");
  bind(CtrlCmd | monaco.KeyCode.KeyU, "editor.action.transformToLowercase");
  bind(CtrlCmd | Shift | monaco.KeyCode.KeyU, "editor.action.transformToUppercase");
  bind(CtrlCmd | monaco.KeyCode.KeyB, "editor.action.jumpToBracket");
  bind(CtrlCmd | monaco.KeyCode.KeyG, "editor.action.gotoLine");
  bind(CtrlCmd | monaco.KeyCode.KeyH, "editor.action.startFindReplaceAction");
  bind(monaco.KeyCode.F3, "editor.action.nextMatchFindAction");
  bind(Shift | monaco.KeyCode.F3, "editor.action.previousMatchFindAction");
  bind(CtrlCmd | monaco.KeyCode.F3, "editor.action.nextSelectionMatchFindAction");
  bind(CtrlCmd | Shift | monaco.KeyCode.F3, "editor.action.previousSelectionMatchFindAction");

  const bookmarks = editor.createDecorationsCollection();
  const bookmarkDecoration = (range: monaco.Range): monaco.editor.IModelDeltaDecoration => ({
    range,
    options: { isWholeLine: true, className: "sbt-bookmarked-line" },
  });
  const bookmarkRanges = () => bookmarks.getRanges().sort((a, b) => a.startLineNumber - b.startLineNumber);

  editor.addCommand(CtrlCmd | monaco.KeyCode.F2, () => {
    const position = editor.getPosition();
    if (!position) return;
    const ranges = bookmarkRanges();
    const existing = ranges.findIndex((range) => range.startLineNumber === position.lineNumber);
    if (existing >= 0) ranges.splice(existing, 1);
    else ranges.push(new monaco.Range(position.lineNumber, 1, position.lineNumber, 1));
    bookmarks.set(ranges.map(bookmarkDecoration));
  });

  const goToBookmark = (forward: boolean) => {
    const ranges = bookmarkRanges();
    const position = editor.getPosition();
    if (!ranges.length || !position) return;
    const target = forward
      ? ranges.find((range) => range.startLineNumber > position.lineNumber) ?? ranges[0]
      : ranges.findLast((range) => range.startLineNumber < position.lineNumber) ?? ranges.at(-1);
    if (!target) return;
    editor.setPosition({ lineNumber: target.startLineNumber, column: 1 });
    editor.revealLineInCenter(target.startLineNumber);
    editor.focus();
  };
  editor.addCommand(monaco.KeyCode.F2, () => goToBookmark(true));
  editor.addCommand(Shift | monaco.KeyCode.F2, () => goToBookmark(false));
  editor.addCommand(CtrlCmd | Shift | monaco.KeyCode.F2, () => bookmarks.clear());
}
