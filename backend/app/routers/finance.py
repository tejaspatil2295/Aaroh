from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import analytics as A
from .. import schemas as S
from ..crud import assert_ref, crud_router
from ..deps import Ctx, get_ctx
from ..models import Budget, FinancialGoal, Opportunity, Subscription, Transaction

TransactionOut = S.read(S.TransactionIn, "TransactionOut")
BudgetOut = S.read(S.BudgetIn, "BudgetOut")
SubscriptionOut = S.read(S.SubscriptionIn, "SubscriptionOut")
FinancialGoalOut = S.read(S.FinancialGoalIn, "FinancialGoalOut")

EXPENSE_CATEGORIES = [
    "groceries", "food_delivery", "dining", "rent", "utilities", "transport", "fuel", "health", "fitness",
    "education", "books_courses", "shopping", "entertainment", "subscriptions", "travel", "family", "emi_loans",
    "insurance", "investments", "gifts", "gadgets", "business", "other",
]
INCOME_CATEGORIES = ["salary", "freelance", "consulting", "teaching", "content", "interest", "refund", "other_income"]

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/categories")
def categories():
    return {"expense": EXPENSE_CATEGORIES, "income": INCOME_CATEGORIES}


@router.get("/summary", summary="Monthly financial summary")
def summary(month: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"), ctx: Ctx = Depends(get_ctx)):
    month = month or A.today(ctx).strftime("%Y-%m")
    data = A.finance_month(ctx, month)
    data["subscriptions"] = A.subscriptions_monthly(ctx)
    data["observations"] = A.spending_flags(ctx, month)
    return data


@router.get("/trends", summary="Income vs expense for the last N months")
def trends(months: int = Query(default=6, ge=1, le=24), ctx: Ctx = Depends(get_ctx)):
    d = A.today(ctx).replace(day=1)
    out = []
    for i in range(months - 1, -1, -1):
        y, m = d.year, d.month - i
        while m <= 0:
            m += 12
            y -= 1
        fm = A.finance_month(ctx, f"{y}-{m:02d}")
        out.append({"month": fm["month"], "expense": fm["total_expense"], "income": fm["total_income"], "savings": fm["net_savings"]})
    return out


def _tx_hook(obj, ctx: Ctx, data: dict) -> None:
    assert_ref(Subscription, data.get("subscription_id"), ctx)
    assert_ref(Opportunity, data.get("opportunity_id"), ctx)
    if "currency" in data and data["currency"]:
        data["currency"] = data["currency"].upper()


def _budget_hook(obj, ctx: Ctx, data: dict) -> None:
    if "month" in data:
        try:
            A.month_bounds(data["month"])
        except ValueError:
            raise HTTPException(422, "Invalid month")


routers = [
    router,
    crud_router(Transaction, S.TransactionIn, S.partial(S.TransactionIn, "TransactionPatch"), TransactionOut,
                prefix="/finance/transactions", tag="finance", filters=("kind", "category", "opportunity_id", "subscription_id"),
                date_field="date", search_fields=("description", "category"), order_by=(Transaction.date.desc(), Transaction.created_at.desc()),
                before_save=_tx_hook, max_limit=5000),
    crud_router(Budget, S.BudgetIn, S.partial(S.BudgetIn, "BudgetPatch"), BudgetOut, prefix="/finance/budgets", tag="finance",
                filters=("month", "category"), order_by=(Budget.month.desc(), Budget.category), before_save=_budget_hook),
    crud_router(Subscription, S.SubscriptionIn, S.partial(S.SubscriptionIn, "SubscriptionPatch"), SubscriptionOut,
                prefix="/finance/subscriptions", tag="finance", filters=("active",), order_by=(Subscription.next_due_date.nulls_last(),)),
    crud_router(FinancialGoal, S.FinancialGoalIn, S.partial(S.FinancialGoalIn, "FinancialGoalPatch"), FinancialGoalOut,
                prefix="/finance/goals", tag="finance", order_by=(FinancialGoal.target_date.nulls_last(),)),
]

_ = date
