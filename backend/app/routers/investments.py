from datetime import date

from fastapi import APIRouter, Depends

from .. import analytics as A
from .. import schemas as S
from ..crud import assert_ref, crud_router
from ..deps import Ctx, get_ctx
from ..models import FinancialGoal, Investment, Liability

InvestmentOut = S.read(S.InvestmentIn, "InvestmentOut")
LiabilityOut = S.read(S.LiabilityIn, "LiabilityOut")

router = APIRouter(prefix="/investments", tags=["investments"])


@router.get("/asset-classes")
def asset_classes():
    return A.ASSET_LABELS


@router.get("/summary", summary="Net worth, allocation, returns, SIPs, EMIs and observations")
def summary(ctx: Ctx = Depends(get_ctx)):
    return A.investments_summary(ctx, A.today(ctx))


def _inv_hook(obj, ctx: Ctx, data: dict) -> None:
    assert_ref(FinancialGoal, data.get("financial_goal_id"), ctx)
    # Stamp the "value as of" date when a holding is created or its value changes
    if "current_value" not in data:
        return
    if obj.id is None:  # new holding
        data["value_updated_on"] = data.get("value_updated_on") or A.today(ctx)
    elif obj.current_value is None or float(obj.current_value) != float(data["current_value"]):
        data["value_updated_on"] = A.today(ctx)


routers = [
    router,
    crud_router(Investment, S.InvestmentIn, S.partial(S.InvestmentIn, "InvestmentPatch"), InvestmentOut,
                prefix="/investments/holdings", tag="investments", filters=("asset_class", "risk", "active"),
                search_fields=("name", "platform", "notes"), order_by=(Investment.current_value.desc(),), before_save=_inv_hook),
    crud_router(Liability, S.LiabilityIn, S.partial(S.LiabilityIn, "LiabilityPatch"), LiabilityOut,
                prefix="/investments/liabilities", tag="investments", filters=("kind", "active"),
                order_by=(Liability.outstanding.desc(),)),
]

_ = date
