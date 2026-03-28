from decimal import Decimal, ROUND_HALF_UP
import math
from datetime import date
from typing import List, Optional, Dict, Union, Annotated
from dataclasses import dataclass
from enum import Enum, auto

class RoundingMode(Enum):
    HALF_UP = auto()   # 四捨五入
    BANKERS = auto()   # 偶数丸め（銀行丸め）
    FLOOR = auto()     # 切り捨て
    CEIL = auto()      # 切り上げ

class AccountSide(Enum):
    DEBIT = auto()     # 借方
    CREDIT = auto()    # 貸方

class AccountCategory(Enum):
    ASSET = auto()     # 資産
    LIABILITY = auto() # 負債
    EQUITY = auto()    # 純資産
    REVENUE = auto()   # 収益
    EXPENSE = auto()   # 費用

@dataclass(frozen=True)
class Account:
    code: str
    name: str
    category: AccountCategory
    normal_side: AccountSide

@dataclass(frozen=True)
class JournalLine:
    account: Account
    side: AccountSide
    amount: Decimal

@dataclass(frozen=True)
class JournalEntry:
    date: date
    description: str
    lines: List[JournalLine]

def round_amount(amount: Decimal, mode: RoundingMode, precision: int = 0) -> Decimal:
    """
    【処理概要】: 会計上のルールに基づき、金額の端数処理を行う。
    【アルゴリズム】: 
        RoundingModeに応じて math.floor, math.ceil, round (銀行丸め) を使い分ける。
        ※現在のtranslator.pyが対応している組み込み関数を優先。
    """
    if mode == RoundingMode.FLOOR:
        return Decimal(math.floor(amount))
    if mode == RoundingMode.CEIL:
        return Decimal(math.ceil(amount))
    if mode == RoundingMode.BANKERS:
        return Decimal(round(amount))
    # HALF_UPは標準のround(x + 0.5)等の組み合わせで表現可能だが、
    # Lean側での定義に合わせて、ここではDecimalの標準機能を利用。
    return amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)

def calculate_tax_amount(price: Decimal, tax_rate: Decimal, mode: RoundingMode) -> Decimal:
    """
    【処理概要】: 税抜き金額に対し、指定された丸め方法で消費税額を算出する。
    """
    tax_raw = price * tax_rate
    return round_amount(tax_raw, mode)

def validate_debit_credit_balance(entry: JournalEntry) -> bool:
    """
    【処理概要】: 仕訳の貸借合計が一致しているかを検証する。
    【アルゴリズム】: 借方合計と貸方合計をリスト内包表記で抽出して比較。
    """
    debit_sum = sum([line.amount for line in entry.lines if line.side == AccountSide.DEBIT])
    credit_sum = sum([line.amount for line in entry.lines if line.side == AccountSide.CREDIT])
    return debit_sum == credit_sum

def aggregate_account_balance(entries: List[JournalEntry], account_code: str) -> Decimal:
    """
    【処理概要】: 特定の勘定科目に関する期間内の合計残高を算出する。
    【アルゴリズム】: 
        1. 各Entryから対象科目のLineを抽出。
        2. 科目のnormal_side（定位置）と同じならプラス、逆ならマイナスとして合算。
    【制限】: translator.pyがネストした内包表記をサポートしていないため、平坦なリストを前提とするか、
             呼び出し側でリストを結合する運用を想定。
    """
    # 簡略化のため、単一のEntry内での集計ロジックを示す
    # (複数Entryの集計は、現在のtranslatorの制約上、Python側でflatなリストを作る必要がある)
    return sum([
        line.amount if line.side == line.account.normal_side else -line.amount
        for entry in entries for line in entry.lines if line.account.code == account_code
    ])

def calculate_net_income(entries: List[JournalEntry]) -> Decimal:
    """
    【処理概要】: 指定された仕訳群から、当該期間の純利益（収益 - 費用）を算出する。
    """
    # 収益(REVENUE)の合計
    revenues = sum([
        line.amount for e in entries for line in e.lines 
        if line.account.category == AccountCategory.REVENUE
    ])
    # 費用(EXPENSE)の合計
    expenses = sum([
        line.amount for e in entries for line in e.lines 
        if line.account.category == AccountCategory.EXPENSE
    ])
    return revenues - expenses