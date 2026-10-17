import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


class GroupTrip(Base):
    """旅行群組 / 專案"""
    __tablename__ = "group_trips"

    id = Column(Integer, primary_key=True, index=True)
    line_group_id = Column(String(100), unique=True, index=True, nullable=False)
    trip_name = Column(String(100), default="旅程記帳")
    base_currency = Column(String(10), default="TWD")  # 主要結算幣別
    last_active_expense_id = Column(Integer, nullable=True)  # 最近活躍/正在編輯的支出 ID
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    members = relationship("Member", back_populates="group", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="group", cascade="all, delete-orphan")
    custom_rates = relationship("CurrencyRate", back_populates="group", cascade="all, delete-orphan")


class CurrencyRate(Base):
    """群組自訂匯率表"""
    __tablename__ = "currency_rates"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("group_trips.id"), nullable=False, index=True)
    currency = Column(String(10), nullable=False)  # 例如 JPY, USD
    rate_to_base = Column(Float, nullable=False)   # 例如 JPY -> TWD 為 0.215
    created_at = Column(DateTime, default=utc_now)

    group = relationship("GroupTrip", back_populates="custom_rates")


class Member(Base):
    """旅行夥伴成員"""
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("group_trips.id"), nullable=False, index=True)
    line_user_id = Column(String(100), nullable=True)
    display_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=utc_now)

    group = relationship("GroupTrip", back_populates="members")
    paid_expenses = relationship("Expense", back_populates="payer")
    splits = relationship("ExpenseSplit", back_populates="member")


class Expense(Base):
    """消費支出紀錄"""
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("group_trips.id"), nullable=False, index=True)
    item_name = Column(String(200), nullable=False)
    currency = Column(String(10), default="TWD")       # 原始幣別
    original_amount = Column(Float, nullable=True, default=0.0)    # 原始幣別金額（如 3000 JPY）
    exchange_rate = Column(Float, default=1.0)         # 折合主幣別之匯率
    amount = Column(Float, nullable=False)             # 折合主幣別金額（如 645 TWD，用於統一結算）
    payer_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    split_count = Column(Integer, default=1)
    split_type = Column(String(50), default="EQUAL_ALL")  # EQUAL_ALL, EQUAL_COUNT, CUSTOM_MEMBERS
    note = Column(Text, nullable=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    group = relationship("GroupTrip", back_populates="expenses")
    payer = relationship("Member", back_populates="paid_expenses")
    splits = relationship("ExpenseSplit", back_populates="expense", cascade="all, delete-orphan")


class ExpenseSplit(Base):
    """每筆支出的分攤明細"""
    __tablename__ = "expense_splits"

    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(Integer, ForeignKey("expenses.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    amount_owed = Column(Float, nullable=False)

    expense = relationship("Expense", back_populates="splits")
    member = relationship("Member", back_populates="splits")


class DraftExpense(Base):
    """記帳互動階段的暫存資料（支援按鈕引導多步驟流程）"""
    __tablename__ = "draft_expenses"

    id = Column(Integer, primary_key=True, index=True)
    line_group_id = Column(String(100), index=True, nullable=False)
    initiator_user_id = Column(String(100), nullable=False)
    item_name = Column(String(200), nullable=False)
    currency = Column(String(10), default="TWD")
    original_amount = Column(Float, nullable=True, default=0.0)
    exchange_rate = Column(Float, default=1.0)
    amount = Column(Float, nullable=False)  # 折合主幣別金額
    payer_member_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utc_now)
