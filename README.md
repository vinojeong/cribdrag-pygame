# Crib‑Dragging Demo

A simple interactive tool for a **two‑time pad** assignment.  
Loads two ciphertexts (`citext49`, `citext192`), computes `X = C1 ⊕ C2`, then lets you *drag a crib* across the xortext to recover plaintext candidates.

---

## Overview

- Displays **C1**, **C2**, **X**, the crib **R**, and the recovered plaintext **X ⊕ R** in a scrollable grid.
- You type a crib (e.g. `" the "`) directly into the crib row, then click/drag it left or right to try different alignments. Arrow keys also work.
- Any byte you click shows bit info in the footer.
- All valid plaintext characters (ASCII 32–41, 44–59, 63, 91, 93, 65–90, 97–122) are displayed as themselves; others show as `·` or special symbols.

---

## Requirements

- **Python 3** (tested with 3.6+)
- **pygame** (`pip install pygame`)

---

## How to Run

1. Place the two ciphertext files **`citext49`** and **`citext192`** in the same folder as `cribdrag.py`.  
   (If they’re missing, the script falls back to embedded copies.)

2. Run:
   ```bash
   python cribdrag.py
   ```
---

## How to Use

- **Typing** – just start typing while the window is focused. The crib appears in the **R** (crib) row.
- **Moving the crib** – click and drag anywhere in the **R** row, or use the **← / →** arrow keys.
- **Inspect a byte** – click any byte in any row; the footer shows its value and XOR breakdown.
- **Undo** – `Ctrl/Cmd+Z` undoes your last change.
- **Paste** – `Ctrl/Cmd+V` pastes clipboard text into the crib.
- **Clear** – `Esc` clears the entire crib and resets the interface.
- **Delete last word** – `Ctrl/Option+Backspace`.
- **Scrolling** – mouse wheel, **↑/↓**, **Page Up/Down**.

---

## Extra

- The grid always shows **100 bytes per row**, so you can see a whole 600‑byte file without horizontal scrolling.
- The crib’s active range is highlighted in gold across **all rows** – you can see exactly which bytes are affected.
- The tool was built for the specific plaintext character set defined in an assignment; may be updated later.

---
