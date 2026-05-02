def generate(lean_code_body):
    """
    Leanコードの先頭に追加するヘルパー関数や定義（プリアンブル）を生成する
    """
    # 使用されている機能を判定
    uses_date = "Date" in lean_code_body
    uses_float = "Float" in lean_code_body
    uses_div = "py_div" in lean_code_body
    uses_floor = "py_floor" in lean_code_body
    uses_ceil = "py_ceil" in lean_code_body
    uses_round = "py_round" in lean_code_body
    uses_sum = "py_sum" in lean_code_body
    uses_half_up = "py_round_half_up" in lean_code_body
    uses_rat = "Rat" in lean_code_body or uses_floor or uses_ceil or uses_round or uses_half_up

    # インポート文の構築
    imports = ["import Lean"]
    if uses_rat:
        imports.append("import Mathlib.Data.Rat.Basic")
        imports.append("import Mathlib.Data.Rat.Floor")

    # 定義本体の構築
    sections = []

    if uses_date:
        sections.append("""-- Pythonのdatetime.date互換の構造体
structure Date where
  year : Int
  month : Int
  day : Int
deriving Repr, BEq, Inhabited""")

    if uses_div:
        sections.append("""-- Pythonの / 演算子ヘルパー
class PyDiv (α : Type) (β : Type) where
  py_div : α -> β -> Float

instance : PyDiv Int Int where
  py_div a b := (Float.ofInt a) / (Float.ofInt b)

instance : PyDiv Float Float where
  py_div a b := a / b

instance : PyDiv Int Float where
  py_div a b := (Float.ofInt a) / b

instance : PyDiv Float Int where
  py_div a b := a / (Float.ofInt b)

def py_div {α β} [PyDiv α β] (a : α) (b : β) : Float := PyDiv.py_div a b""")

    if uses_float:
        sections.append("""-- 浮動小数点数と整数の混在演算を許可するインスタンス
instance : HAdd Int Float Float where hAdd n f := Float.ofInt n + f
instance : HAdd Float Int Float where hAdd f n := f + Float.ofInt n
instance : HSub Int Float Float where hSub n f := Float.ofInt n - f
instance : HSub Float Int Float where hSub f n := f - Float.ofInt n
instance : HMul Int Float Float where hMul n f := Float.ofInt n * f
instance : HMul Float Int Float where hMul f n := f * Float.ofInt n
instance : HPow Float Int Float where hPow f n := f.pow (Float.ofInt n)
instance : HPow Float Nat Float where hPow f n := f.pow (Float.ofInt n)""")

    math_helpers = []
    if uses_floor:
        math_helpers.append("def py_floor (x : Rat) : Int := x.floor")
    if uses_ceil:
        math_helpers.append("def py_ceil (x : Rat) : Int := x.ceil")
    if uses_round:
        math_helpers.append("def py_round (x : Rat) : Int := x.round")
    if uses_half_up:
        # 四捨五入: x + 1/2 を床関数に通す (xが正の場合)
        math_helpers.append("def py_round_half_up (x : Rat) : Int := (x + 1/2).floor")
    
    if math_helpers:
        sections.append("\n".join(math_helpers))

    if uses_sum:
        sections.append("def py_sum [Add α] [OfNat α 0] (xs : List α) : α := xs.foldl (· + ·) 0")

    # 出力の組み立て
    header = "\n".join(imports)
    
    if not sections:
        return header + "\n"

    body = "\n\n".join(sections)
    return f"""{header}

-- ==========================================
-- PyLean Preamble
-- ==========================================

{body}

-- ==========================================
"""