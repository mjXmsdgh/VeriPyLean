[English] [**日本語**](README.ja.md)

# VeriPyLean (Prototype v0.1)

**"Human-readable Python, Machine-verifiable Lean 4."**

VeriPyLean is an experimental project that bridges the intuitive readability of Python with the mathematical rigor of Lean 4, using a shared Abstract Syntax Tree (AST).

## 🌟 Concept: "AI Writes, Math Audits"

While modern AI code generation is powerful, it carries the risk of hallucinations. VeriPyLean "translates" Python code written by humans or AI into Lean 4, using formal verification to detect logical inconsistencies before the code ever runs.

* **Python View**: The frontend for humans (and AI) to write and read logic intuitively.
* **Lean 4 View**: The backend to verify logical consistency (e.g., division by zero, type mismatches, termination) mathematically.
* **AST-First**: By managing programs as data structures (AST) rather than just text, we ensure a reliable 1-to-1 mapping between the two languages.




## 🏗 Scope and Strategy: Practical Formal Verification

VeriPyLean does not aim to be a general-purpose Python-to-Lean compiler. Instead, it focuses on the "Mathematical Heart" of software where formal verification provides the highest ROI.

### 1. Target Scope: "Logic, Not Infrastructure"

We prioritize verifying pure logic over environmental side effects.

* **In-Scope (Verified Core)**:
* **Numerical Algorithms**: Physical simulations, statistical models, and financial logic.
* **Pure Functions**: Deterministic logic such as data transformations, sorting, and recursive algorithms.
* **Safety Guards**: Verification of boundary conditions (e.g., preventing division by zero or index-out-of-bounds).


* **Out-of-Scope (Unverified Shell)**:
* **I/O & Side Effects**: File systems, network requests, and database interactions.
* **UI/UX Frameworks**: Frontend logic such as Streamlit or GUI event loops.
* **Dynamic Metaprogramming**: Runtime attribute injection or complex class inheritance that lacks static mapping to Lean 4.



### 2. "Soft Verification" & Precision Trade-offs

Rather than demanding an "all-or-nothing" formal proof, we adopt a pragmatic approach to numerical accuracy.

* **From "Absolute Proof" to "Smart Warnings"**:
If a complete proof is too costly, the system acts as a high-end advisory tool, flagging potential precision loss or rounding errors.
* **Verified Approximation**:
Using Lean 4’s `mathlib`, we aim to verify that truncation errors in numerical methods remain within predefined bounds.
* **Interval Arithmetic Modeling**:
By treating floating-point variables as intervals rather than single points, we can mathematically track error propagation and alert the user when confidence intervals exceed safe limits.



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
---

## 🏗 The Ultimate Goal of This Project: Passing the Torch

I am convinced that the concept of bridging Python and Lean 4 will become an indispensable standard in the era of AI-driven software development. However, it is impossible for me to fully realize this grand vision with my personal implementation skills alone.

### 🕊️ A Request to the Community

* **Independent Implementations are Welcome:** I sincerely hope that "someone who knows what they’re doing" will take this idea and start a "proper implementation" as a completely separate project or repository.
* **Feel Free to Steal or Adapt the Idea:** You can use the name "VeriPyLean" or rename it entirely. My ultimate goal is to see this mechanism of "Mathematical Peer Review for AI-generated Code" become a reality and benefit the world.
* **I am Content Being the "Instigator":** I provide the vision and a minimal prototype. If you feel that you can build this better than I can, please follow that intuition. The stage is yours.













