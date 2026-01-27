[English] [**日本語**](README.ja.md)

# VeriPyLean (Prototype v0.1)

**"Human-readable Python, Machine-verifiable Lean 4."**

VeriPyLean is an experimental project that bridges the intuitive readability of Python with the mathematical rigor of Lean 4, using a shared Abstract Syntax Tree (AST).

## 🌟 Concept: "AI Writes, Math Audits"

While modern AI code generation is powerful, it carries the risk of hallucinations. VeriPyLean "translates" Python code written by humans or AI into Lean 4, using formal verification to detect logical inconsistencies before the code ever runs.

* **Python View**: The frontend for humans (and AI) to write and read logic intuitively.
* **Lean 4 View**: The backend to verify logical consistency (e.g., division by zero, type mismatches, termination) mathematically.
* **AST-First**: By managing programs as data structures (AST) rather than just text, we ensure a reliable 1-to-1 mapping between the two languages.

## 🚀 What is Working (v0.1)

The following flow is already functional in our minimal prototype:

* [x] **Arithmetic Translation**: Maps Python `+`, `-`, `*`, `//` to Lean 4 operators.
* [x] **Conditional Logic**: Recursive translation of `if-else` blocks.
* [x] **Safety Check (Heuristics)**: Detects division operations and warns if they are not guarded by a conditional check.

### Demo

**Input (Python):**

```python
if b != 0:
    return 10 // b
else:
    return 0

```

**Output (Lean 4):**

```lean
def example (b : Int) : Int :=
  if b ≠ 0 then (10 / b) else 0

```

## 🛠 Tech Stack

* **Language**: Python 3.10+
* **Parsing**: Standard `ast` module (Built-in Python parser)
* **UI**: Streamlit (For rapid prototyping)
* **Verification (Target)**: Lean 4

## 🗺 Roadmap (We Need Your Help!)

I have built the core concept and a minimal "chilly" prototype. To bring this vision to life, we need contributors who are passionate about formal methods and developer experience.

1. **Expanding AST Mapping**: Adding support for list operations, recursive functions, and custom types.
2. **Lean 4 Kernel Integration**: Feeding the generated code directly into the Lean 4 compiler to pipe error feedback back to the Python view.
3. **AI Assist**: Using LLMs to infer strict Lean types from ambiguous Python code.

## 💬 From the Creator

"Let's spend less time writing tests and more time proving correctness."
VeriPyLean started with this simple dream. It’s a small step, but I’m looking for developers who believe in a future where code is not just 'tested,' but 'proven.'

---
