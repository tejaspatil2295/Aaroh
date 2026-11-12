"""AAROH data model.

Multi-user readiness: every user-owned record carries `owner_id` (the author) and
`workspace_id` (the space it lives in) plus `visibility`. In the MVP each user has a
single personal workspace and everything is private. Sharing with a partner later means
adding them to a shared workspace and flipping `visibility` to "shared" on chosen
records; private records are only ever returned to their owner (see app/access.py).
"""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

JSONType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class OwnedMixin(TimestampMixin):
    """Columns shared by every user-owned record."""

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    visibility: Mapped[str] = mapped_column(String(16), default="private")  # private | shared


# ---------------------------------------------------------------- identity & tenancy
class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120), default="")
    about: Mapped[str] = mapped_column(Text, default="")  # career/personal background used as AI context
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped["UserSettings"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserSettings(Base):
    __tablename__ = "user_settings"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    preferences: Mapped[dict] = mapped_column(JSONType, default=dict)
    ai_permissions: Mapped[dict] = mapped_column(JSONType, default=dict)
    ai_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ai_base_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    user: Mapped[User] = relationship(back_populates="settings")


class Workspace(TimestampMixin, Base):
    __tablename__ = "workspaces"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(16), default="personal")  # personal | shared
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))


class WorkspaceMember(TimestampMixin, Base):
    __tablename__ = "workspace_members"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16), default="owner")  # owner | admin | member | viewer


class WorkspaceInvitation(TimestampMixin, Base):
    """Phase 3: partner/family invitations. Table exists so the schema is ready."""

    __tablename__ = "workspace_invitations"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="member")
    token_hash: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    invited_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    family_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    user_agent: Mapped[str] = mapped_column(String(255), default="")


# ---------------------------------------------------------------- tasks, goals, habits
class Goal(OwnedMixin, Base):
    __tablename__ = "goals"
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    area: Mapped[str] = mapped_column(String(32), default="personal")
    status: Mapped[str] = mapped_column(String(16), default="active")
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    metric_unit: Mapped[str] = mapped_column(String(32), default="")
    start_value: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    target_value: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    current_value: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)


class Milestone(OwnedMixin, Base):
    __tablename__ = "milestones"
    goal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Task(OwnedMixin, Base):
    __tablename__ = "tasks"
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(32), default="personal", index=True)
    priority: Mapped[str] = mapped_column(String(16), default="medium")
    status: Mapped[str] = mapped_column(String(16), default="todo", index=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    scheduled_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimate_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reminder_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recurrence: Mapped[str] = mapped_column(String(16), default="none")
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    goal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("goals.id", ondelete="SET NULL"), nullable=True)
    tags: Mapped[list] = mapped_column(JSONType, default=list)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    postponed_count: Mapped[int] = mapped_column(Integer, default=0)


class Habit(OwnedMixin, Base):
    __tablename__ = "habits"
    name: Mapped[str] = mapped_column(String(120))
    area: Mapped[str] = mapped_column(String(32), default="personal")
    target_per_week: Mapped[int] = mapped_column(Integer, default=7)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class HabitLog(OwnedMixin, Base):
    __tablename__ = "habit_logs"
    __table_args__ = (UniqueConstraint("habit_id", "date"),)
    habit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("habits.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)


# ---------------------------------------------------------------- finance
class Transaction(OwnedMixin, Base):
    __tablename__ = "transactions"
    kind: Mapped[str] = mapped_column(String(16), default="expense")  # expense | income
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    category: Mapped[str] = mapped_column(String(48), default="other", index=True)
    description: Mapped[str] = mapped_column(String(300), default="")
    date: Mapped[date] = mapped_column(Date, index=True)
    payment_method: Mapped[str] = mapped_column(String(32), default="")
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True)
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True)
    tags: Mapped[list] = mapped_column(JSONType, default=list)


class Budget(OwnedMixin, Base):
    __tablename__ = "budgets"
    __table_args__ = (UniqueConstraint("owner_id", "workspace_id", "month", "category"),)
    month: Mapped[str] = mapped_column(String(7))  # YYYY-MM
    category: Mapped[str] = mapped_column(String(48), default="__total__")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class Subscription(OwnedMixin, Base):
    __tablename__ = "subscriptions"
    name: Mapped[str] = mapped_column(String(120))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    billing_cycle: Mapped[str] = mapped_column(String(16), default="monthly")
    next_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    category: Mapped[str] = mapped_column(String(48), default="subscriptions")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class FinancialGoal(OwnedMixin, Base):
    __tablename__ = "financial_goals"
    name: Mapped[str] = mapped_column(String(120))
    target_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    saved_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")


# ---------------------------------------------------------------- investments & net worth
class Investment(OwnedMixin, Base):
    """A holding: mutual fund, stock, FD, PPF, EPF, NPS, gold, property, crypto... Values are entered by the user."""
    __tablename__ = "investments"
    name: Mapped[str] = mapped_column(String(160))
    asset_class: Mapped[str] = mapped_column(String(32), default="mutual_fund", index=True)
    platform: Mapped[str] = mapped_column(String(80), default="")  # Zerodha, Groww, bank, post office...
    invested_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    current_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    units: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    maturity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    interest_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)  # % p.a. for FD/RD/PPF/bonds
    sip_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    sip_day: Mapped[int | None] = mapped_column(Integer, nullable=True)  # day of month 1-28
    risk: Mapped[str] = mapped_column(String(8), default="medium")  # low | medium | high
    liquidity: Mapped[str] = mapped_column(String(12), default="medium")  # high (days) | medium | locked
    financial_goal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("financial_goals.id", ondelete="SET NULL"), nullable=True)
    value_updated_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class Liability(OwnedMixin, Base):
    __tablename__ = "liabilities"
    name: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(24), default="personal_loan")
    lender: Mapped[str] = mapped_column(String(80), default="")
    principal: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    outstanding: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    interest_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    emi: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    emi_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class NetWorthSnapshot(OwnedMixin, Base):
    """One row per user per day, written whenever the investments summary is computed (for the trend chart)."""
    __tablename__ = "net_worth_snapshots"
    __table_args__ = (UniqueConstraint("owner_id", "workspace_id", "date"),)
    date: Mapped[date] = mapped_column(Date, index=True)
    assets: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    liabilities: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    invested: Mapped[Decimal] = mapped_column(Numeric(16, 2))


# ---------------------------------------------------------------- journal
class JournalEntry(OwnedMixin, Base):
    __tablename__ = "journal_entries"
    title: Mapped[str] = mapped_column(String(200), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(24), default="reflection")
    entry_date: Mapped[date] = mapped_column(Date, index=True)
    mood: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1..5
    energy: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1..5
    tags: Mapped[list] = mapped_column(JSONType, default=list)
    location: Mapped[str] = mapped_column(String(120), default="")
    decision_outcome: Mapped[str] = mapped_column(Text, default="")
    hide_from_ai: Mapped[bool] = mapped_column(Boolean, default=False)


class Attachment(OwnedMixin, Base):
    __tablename__ = "attachments"
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    storage_path: Mapped[str] = mapped_column(String(500))
    data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True, deferred=True)


# ---------------------------------------------------------------- learning
class Skill(OwnedMixin, Base):
    __tablename__ = "skills"
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(48), default="backend")
    current_level: Mapped[int] = mapped_column(Integer, default=1)  # 0..5
    target_level: Mapped[int] = mapped_column(Integer, default=4)
    status: Mapped[str] = mapped_column(String(16), default="planned")  # planned | learning | paused | strong
    priority: Mapped[str] = mapped_column(String(16), default="medium")
    notes: Mapped[str] = mapped_column(Text, default="")


class RoadmapItem(OwnedMixin, Base):
    __tablename__ = "roadmap_items"
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LearningLog(OwnedMixin, Base):
    __tablename__ = "learning_logs"
    date: Mapped[date] = mapped_column(Date, index=True)
    minutes: Mapped[int] = mapped_column(Integer)
    skill_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("skills.id", ondelete="SET NULL"), nullable=True)
    topic: Mapped[str] = mapped_column(String(200), default="")
    notes: Mapped[str] = mapped_column(Text, default="")


class KnowledgeNote(OwnedMixin, Base):
    __tablename__ = "knowledge_notes"
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(16), default="note")  # note | snippet
    language: Mapped[str] = mapped_column(String(32), default="")
    tags: Mapped[list] = mapped_column(JSONType, default=list)
    skill_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("skills.id", ondelete="SET NULL"), nullable=True)


class Resource(OwnedMixin, Base):
    __tablename__ = "resources"
    title: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(1000), default="")
    kind: Mapped[str] = mapped_column(String(16), default="article")
    status: Mapped[str] = mapped_column(String(16), default="to_read")
    skill_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("skills.id", ondelete="SET NULL"), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class LearningItem(OwnedMixin, Base):
    """Courses, projects and certifications."""

    __tablename__ = "learning_items"
    kind: Mapped[str] = mapped_column(String(16), default="course")
    title: Mapped[str] = mapped_column(String(200))
    provider: Mapped[str] = mapped_column(String(120), default="")
    url: Mapped[str] = mapped_column(String(1000), default="")
    status: Mapped[str] = mapped_column(String(16), default="planned")
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)
    started_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class InterviewItem(OwnedMixin, Base):
    __tablename__ = "interview_items"
    topic: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(24), default="dsa")
    question: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="todo")  # todo | practicing | confident
    confidence: Mapped[int] = mapped_column(Integer, default=1)
    notes: Mapped[str] = mapped_column(Text, default="")
    last_practiced: Mapped[date | None] = mapped_column(Date, nullable=True)


# ---------------------------------------------------------------- fitness
class BodyMetric(OwnedMixin, Base):
    __tablename__ = "body_metrics"
    date: Mapped[date] = mapped_column(Date, index=True)
    weight_kg: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    body_fat_pct: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    waist_cm: Mapped[float | None] = mapped_column(Numeric(5, 1), nullable=True)
    chest_cm: Mapped[float | None] = mapped_column(Numeric(5, 1), nullable=True)
    arm_cm: Mapped[float | None] = mapped_column(Numeric(5, 1), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class Workout(OwnedMixin, Base):
    __tablename__ = "workouts"
    date: Mapped[date] = mapped_column(Date, index=True)
    title: Mapped[str] = mapped_column(String(120))
    workout_type: Mapped[str] = mapped_column(String(16), default="strength")
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attended_gym: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(16), default="done")  # planned | done | skipped
    notes: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(24), default="manual")  # manual | health_connect | google_fit
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sets: Mapped[list["WorkoutSet"]] = relationship(
        back_populates="workout", cascade="all, delete-orphan", order_by="WorkoutSet.set_number"
    )


class WorkoutSet(Base):
    __tablename__ = "workout_sets"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workout_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workouts.id", ondelete="CASCADE"), index=True)
    exercise: Mapped[str] = mapped_column(String(120))
    set_number: Mapped[int] = mapped_column(Integer, default=1)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    workout: Mapped[Workout] = relationship(back_populates="sets")


class DailyActivity(OwnedMixin, Base):
    __tablename__ = "daily_activity"
    __table_args__ = (UniqueConstraint("owner_id", "date"),)
    date: Mapped[date] = mapped_column(Date, index=True)
    steps: Mapped[int] = mapped_column(Integer, default=0)
    water_ml: Mapped[int] = mapped_column(Integer, default=0)
    sleep_hours: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    active_minutes: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(24), default="manual")


class FoodLog(OwnedMixin, Base):
    __tablename__ = "food_logs"
    date: Mapped[date] = mapped_column(Date, index=True)
    meal: Mapped[str] = mapped_column(String(16), default="snack")
    food: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[str] = mapped_column(String(60), default="")
    calories: Mapped[int] = mapped_column(Integer, default=0)
    protein_g: Mapped[float] = mapped_column(Numeric(6, 1), default=0)
    carbs_g: Mapped[float] = mapped_column(Numeric(6, 1), default=0)
    fat_g: Mapped[float] = mapped_column(Numeric(6, 1), default=0)


# ---------------------------------------------------------------- work journal
class WorkLog(OwnedMixin, Base):
    __tablename__ = "work_logs"
    date: Mapped[date] = mapped_column(Date, index=True)
    project: Mapped[str] = mapped_column(String(120), default="", index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    tasks_completed: Mapped[str] = mapped_column(Text, default="")
    problems: Mapped[str] = mapped_column(Text, default="")
    solutions: Mapped[str] = mapped_column(Text, default="")
    learnings: Mapped[str] = mapped_column(Text, default="")
    pending: Mapped[str] = mapped_column(Text, default="")
    hours: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    tags: Mapped[list] = mapped_column(JSONType, default=list)


# ---------------------------------------------------------------- side income
class Opportunity(OwnedMixin, Base):
    __tablename__ = "opportunities"
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(32), default="other")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="idea")  # idea | validating | active | paused | dropped
    estimated_investment: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    est_monthly_low: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    est_monthly_high: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    hours_per_week: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    skills_required: Mapped[list] = mapped_column(JSONType, default=list)
    validation_notes: Mapped[str] = mapped_column(Text, default="")
    execution_plan: Mapped[str] = mapped_column(Text, default="")
    next_action: Mapped[str] = mapped_column(String(300), default="")
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)
    ai_evaluation: Mapped[str] = mapped_column(Text, default="")


# ---------------------------------------------------------------- AI
class AIConversation(OwnedMixin, Base):
    __tablename__ = "ai_conversations"
    title: Mapped[str] = mapped_column(String(200), default="New conversation")
    persona: Mapped[str] = mapped_column(String(32), default="life_coach")
    messages: Mapped[list["AIMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="AIMessage.created_at"
    )


class AIMessage(Base):
    __tablename__ = "ai_messages"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ai_conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(32), default="")
    model: Mapped[str] = mapped_column(String(120), default="")
    is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    conversation: Mapped[AIConversation] = relationship(back_populates="messages")


class AIInsight(OwnedMixin, Base):
    __tablename__ = "ai_insights"
    kind: Mapped[str] = mapped_column(String(32), index=True)
    period_start: Mapped[date] = mapped_column(Date, index=True)
    content: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(32), default="")
    model: Mapped[str] = mapped_column(String(120), default="")
    is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
