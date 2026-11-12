"""Pydantic schemas. `*In` models validate writes; update/read variants are derived."""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, create_model

Str200 = Field(max_length=200)
Visibility = Literal["private", "shared"]


class Base(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid", str_strip_whitespace=True)


def partial(model: type[BaseModel], name: str) -> type[BaseModel]:
    """All-optional copy of a schema, used for PATCH."""
    fields = {k: (Optional[v.annotation], None) for k, v in model.model_fields.items()}
    return create_model(name, __base__=Base, **fields)


def read(model: type[BaseModel], name: str, **extra: Any) -> type[BaseModel]:
    fields = {
        "id": (uuid.UUID, ...),
        "owner_id": (uuid.UUID, ...),
        "visibility": (str, "private"),
        "created_at": (datetime, ...),
        "updated_at": (datetime, ...),
        **extra,
    }
    return create_model(name, __base__=model, **fields)


# ---------------------------------------------------------------- auth & profile
class RegisterIn(Base):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=120)


class LoginIn(Base):
    email: EmailStr
    password: str = Field(max_length=128)


class RefreshIn(Base):
    refresh_token: Optional[str] = None


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    full_name: str
    about: str
    created_at: datetime


class ProfileUpdate(Base):
    full_name: Optional[str] = Field(default=None, max_length=120)
    about: Optional[str] = Field(default=None, max_length=5000)


class PasswordChange(Base):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class DeleteAccountIn(Base):
    password: str
    confirm: Literal["DELETE"]


AI_MODULES = ["tasks", "goals", "finance", "investments", "journal", "learning", "fitness", "work", "side_income", "profile"]


class SettingsOut(BaseModel):
    preferences: dict
    ai_permissions: dict
    ai_provider: Optional[str]
    ai_model: Optional[str]
    ai_base_url: Optional[str]
    ai_key_set: bool
    ai_effective: dict


class SettingsUpdate(Base):
    preferences: Optional[dict] = None
    ai_permissions: Optional[dict[str, bool]] = None
    ai_provider: Optional[Literal["default", "none", "anthropic", "openai_compatible"]] = None
    ai_model: Optional[str] = Field(default=None, max_length=120)
    ai_base_url: Optional[str] = Field(default=None, max_length=255)
    ai_api_key: Optional[str] = Field(default=None, max_length=500)  # "" clears the stored key


# ---------------------------------------------------------------- goals, tasks, habits
Area = Literal["personal", "career", "finance", "fitness", "learning", "side_income", "work", "health", "relationships"]


class GoalIn(Base):
    title: str = Str200
    description: str = ""
    area: Area = "personal"
    status: Literal["active", "completed", "paused", "abandoned"] = "active"
    target_date: Optional[date] = None
    metric_unit: str = Field(default="", max_length=32)
    start_value: Optional[Decimal] = None
    target_value: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    visibility: Visibility = "private"


class MilestoneIn(Base):
    goal_id: uuid.UUID
    title: str = Str200
    due_date: Optional[date] = None
    done: bool = False


TaskCategory = Literal["personal", "professional", "fitness", "learning", "finance", "side_income", "household"]


class TaskIn(Base):
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    category: TaskCategory = "personal"
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    status: Literal["todo", "in_progress", "done", "cancelled"] = "todo"
    due_date: Optional[date] = None
    scheduled_start: Optional[datetime] = None
    estimate_minutes: Optional[int] = Field(default=None, ge=1, le=24 * 60)
    reminder_at: Optional[datetime] = None
    recurrence: Literal["none", "daily", "weekdays", "weekly", "monthly"] = "none"
    parent_id: Optional[uuid.UUID] = None
    goal_id: Optional[uuid.UUID] = None
    tags: list[str] = []
    visibility: Visibility = "private"


class HabitIn(Base):
    name: str = Field(min_length=1, max_length=120)
    area: Area = "personal"
    target_per_week: int = Field(default=7, ge=1, le=7)
    active: bool = True


class HabitLogIn(Base):
    habit_id: uuid.UUID
    date: date


# ---------------------------------------------------------------- finance
class TransactionIn(Base):
    kind: Literal["expense", "income"] = "expense"
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    category: str = Field(default="other", max_length=48)
    description: str = Field(default="", max_length=300)
    date: date
    payment_method: str = Field(default="", max_length=32)
    subscription_id: Optional[uuid.UUID] = None
    opportunity_id: Optional[uuid.UUID] = None
    tags: list[str] = []
    visibility: Visibility = "private"


class BudgetIn(Base):
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    category: str = Field(default="__total__", max_length=48)
    amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class SubscriptionIn(Base):
    name: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    billing_cycle: Literal["weekly", "monthly", "quarterly", "yearly"] = "monthly"
    next_due_date: Optional[date] = None
    category: str = Field(default="subscriptions", max_length=48)
    active: bool = True
    notes: str = ""


class FinancialGoalIn(Base):
    name: str = Field(min_length=1, max_length=120)
    target_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    saved_amount: Decimal = Field(default=Decimal(0), ge=0, max_digits=14, decimal_places=2)
    target_date: Optional[date] = None
    notes: str = ""


# ---------------------------------------------------------------- investments
AssetClass = Literal[
    "mutual_fund", "stock", "etf", "fd", "rd", "ppf", "epf", "nps", "gold", "sgb", "bonds", "real_estate",
    "crypto", "savings", "insurance_ulip", "other",
]


class InvestmentIn(Base):
    name: str = Field(min_length=1, max_length=160)
    asset_class: AssetClass = "mutual_fund"
    platform: str = Field(default="", max_length=80)
    invested_amount: Decimal = Field(default=Decimal(0), ge=0, max_digits=14, decimal_places=2)
    current_value: Decimal = Field(default=Decimal(0), ge=0, max_digits=14, decimal_places=2)
    units: Optional[Decimal] = Field(default=None, ge=0, max_digits=18, decimal_places=6)
    start_date: Optional[date] = None
    maturity_date: Optional[date] = None
    interest_rate: Optional[Decimal] = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    sip_amount: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    sip_day: Optional[int] = Field(default=None, ge=1, le=28)
    risk: Literal["low", "medium", "high"] = "medium"
    liquidity: Literal["high", "medium", "locked"] = "medium"
    financial_goal_id: Optional[uuid.UUID] = None
    value_updated_on: Optional[date] = None
    active: bool = True
    notes: str = ""


class LiabilityIn(Base):
    name: str = Field(min_length=1, max_length=160)
    kind: Literal["home_loan", "car_loan", "personal_loan", "education_loan", "credit_card", "gold_loan", "borrowed_family", "other"] = "personal_loan"
    lender: str = Field(default="", max_length=80)
    principal: Optional[Decimal] = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    outstanding: Decimal = Field(default=Decimal(0), ge=0, max_digits=14, decimal_places=2)
    interest_rate: Optional[Decimal] = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    emi: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    emi_day: Optional[int] = Field(default=None, ge=1, le=28)
    end_date: Optional[date] = None
    active: bool = True
    notes: str = ""


# ---------------------------------------------------------------- journal
class JournalIn(Base):
    title: str = Field(default="", max_length=200)
    body: str = Field(default="", max_length=50000)
    kind: Literal[
        "reflection", "experience", "event", "achievement", "travel", "lesson", "decision", "gratitude", "daily_review"
    ] = "reflection"
    entry_date: date
    mood: Optional[int] = Field(default=None, ge=1, le=5)
    energy: Optional[int] = Field(default=None, ge=1, le=5)
    tags: list[str] = []
    location: str = Field(default="", max_length=120)
    decision_outcome: str = ""
    hide_from_ai: bool = False


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime


# ---------------------------------------------------------------- learning
Level = Field(default=1, ge=0, le=5)


class SkillIn(Base):
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(default="backend", max_length=48)
    current_level: int = Level
    target_level: int = Field(default=4, ge=0, le=5)
    status: Literal["planned", "learning", "paused", "strong"] = "planned"
    priority: Literal["low", "medium", "high"] = "medium"
    notes: str = ""


class RoadmapItemIn(Base):
    skill_id: uuid.UUID
    title: str = Str200
    description: str = ""
    order_index: int = 0
    done: bool = False


class LearningLogIn(Base):
    date: date
    minutes: int = Field(ge=1, le=24 * 60)
    skill_id: Optional[uuid.UUID] = None
    topic: str = Field(default="", max_length=200)
    notes: str = ""


class NoteIn(Base):
    title: str = Str200
    content: str = Field(default="", max_length=100000)
    kind: Literal["note", "snippet"] = "note"
    language: str = Field(default="", max_length=32)
    tags: list[str] = []
    skill_id: Optional[uuid.UUID] = None


class ResourceIn(Base):
    title: str = Str200
    url: str = Field(default="", max_length=1000)
    kind: Literal["article", "docs", "video", "course", "book", "repo", "other"] = "article"
    status: Literal["to_read", "in_progress", "done"] = "to_read"
    skill_id: Optional[uuid.UUID] = None
    notes: str = ""


class LearningItemIn(Base):
    kind: Literal["course", "project", "certification"] = "course"
    title: str = Str200
    provider: str = Field(default="", max_length=120)
    url: str = Field(default="", max_length=1000)
    status: Literal["planned", "in_progress", "completed", "dropped"] = "planned"
    progress_pct: int = Field(default=0, ge=0, le=100)
    started_on: Optional[date] = None
    completed_on: Optional[date] = None
    notes: str = ""


class InterviewItemIn(Base):
    topic: str = Str200
    category: Literal["dsa", "system_design", "frontend", "backend", "database", "devops", "behavioral", "other"] = "dsa"
    question: str = ""
    status: Literal["todo", "practicing", "confident"] = "todo"
    confidence: int = Field(default=1, ge=1, le=5)
    notes: str = ""
    last_practiced: Optional[date] = None


# ---------------------------------------------------------------- fitness
class BodyMetricIn(Base):
    date: date
    weight_kg: Optional[Decimal] = Field(default=None, gt=0, lt=400)
    body_fat_pct: Optional[Decimal] = Field(default=None, ge=0, le=70)
    waist_cm: Optional[Decimal] = Field(default=None, gt=0, lt=300)
    chest_cm: Optional[Decimal] = Field(default=None, gt=0, lt=300)
    arm_cm: Optional[Decimal] = Field(default=None, gt=0, lt=100)
    notes: str = ""


class WorkoutSetIn(Base):
    exercise: str = Field(min_length=1, max_length=120)
    set_number: int = Field(default=1, ge=1, le=100)
    reps: Optional[int] = Field(default=None, ge=0, le=1000)
    weight_kg: Optional[Decimal] = Field(default=None, ge=0, lt=1000)


class WorkoutSetOut(WorkoutSetIn):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    id: uuid.UUID


class WorkoutIn(Base):
    date: date
    title: str = Field(min_length=1, max_length=120)
    workout_type: Literal["strength", "cardio", "mobility", "sport", "rest"] = "strength"
    duration_minutes: Optional[int] = Field(default=None, ge=0, le=600)
    attended_gym: bool = True
    status: Literal["planned", "done", "skipped"] = "done"
    notes: str = ""
    sets: list[WorkoutSetIn] = []


class DailyActivityIn(Base):
    date: date
    steps: int = Field(default=0, ge=0, le=200000)
    water_ml: int = Field(default=0, ge=0, le=20000)
    sleep_hours: Optional[Decimal] = Field(default=None, ge=0, le=24)
    active_minutes: int = Field(default=0, ge=0, le=1440)


class FoodLogIn(Base):
    date: date
    meal: Literal["breakfast", "lunch", "dinner", "snack", "pre_workout", "post_workout"] = "snack"
    food: str = Field(min_length=1, max_length=200)
    quantity: str = Field(default="", max_length=60)
    calories: int = Field(default=0, ge=0, le=10000)
    protein_g: Decimal = Field(default=Decimal(0), ge=0, le=1000)
    carbs_g: Decimal = Field(default=Decimal(0), ge=0, le=2000)
    fat_g: Decimal = Field(default=Decimal(0), ge=0, le=1000)


# ---------------------------------------------------------------- work
class WorkLogIn(Base):
    date: date
    project: str = Field(default="", max_length=120)
    summary: str = ""
    tasks_completed: str = ""
    problems: str = ""
    solutions: str = ""
    learnings: str = ""
    pending: str = ""
    hours: Optional[Decimal] = Field(default=None, ge=0, le=24)
    tags: list[str] = []


# ---------------------------------------------------------------- side income
class OpportunityIn(Base):
    title: str = Str200
    category: Literal[
        "upsc_mentorship", "content_creation", "current_affairs", "teaching", "online_course",
        "freelancing", "consulting", "blogging", "digital_product", "other",
    ] = "other"
    description: str = ""
    status: Literal["idea", "validating", "active", "paused", "dropped"] = "idea"
    estimated_investment: Optional[Decimal] = Field(default=None, ge=0)
    est_monthly_low: Optional[Decimal] = Field(default=None, ge=0)
    est_monthly_high: Optional[Decimal] = Field(default=None, ge=0)
    hours_per_week: Optional[Decimal] = Field(default=None, ge=0, le=100)
    skills_required: list[str] = []
    validation_notes: str = ""
    execution_plan: str = ""
    next_action: str = Field(default="", max_length=300)
    progress_pct: int = Field(default=0, ge=0, le=100)


# ---------------------------------------------------------------- AI
Persona = Literal[
    "life_coach", "career_mentor", "tech_teacher", "finance_coach", "fitness_companion", "journal_companion",
    "side_hustle_advisor",
]


class ChatIn(Base):
    message: str = Field(min_length=1, max_length=8000)
    persona: Persona = "life_coach"
    conversation_id: Optional[uuid.UUID] = None


class AIMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    role: str
    content: str
    provider: str
    model: str
    is_fallback: bool
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    persona: str
    created_at: datetime
    updated_at: datetime


class InsightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    kind: str
    period_start: date
    content: str
    provider: str
    model: str
    is_fallback: bool
    created_at: datetime


InsightKind = Literal[
    "morning_briefing", "evening_review", "weekly_review", "monthly_review", "task_suggestions",
    "learning_recommendation", "finance_insights", "fitness_insights", "journal_patterns", "work_weekly_report",
    "habit_analysis", "investment_review",
]


class InsightRequest(Base):
    kind: InsightKind
    force: bool = False
