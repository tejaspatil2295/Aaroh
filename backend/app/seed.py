"""Create a demo account with ~5 weeks of realistic sample data.

Usage:  python -m app.seed            (idempotent: recreates the demo user)
        python -m app.seed --if-missing (only seeds when the demo user does not exist yet)
Login:  demo@aaroh.app / Aaroh@2026
"""
import random
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select

from . import models as M
from .db import SessionLocal
from .routers.auth import create_user

DEMO_EMAIL = "demo@aaroh.app"
DEMO_PASSWORD = "Aaroh@2026"
IST = ZoneInfo("Asia/Kolkata")


def run() -> None:
    rnd = random.Random(42)
    db = SessionLocal()
    old = db.scalar(select(M.User).where(M.User.email == DEMO_EMAIL))
    if old:
        db.execute(M.Workspace.__table__.delete().where(M.Workspace.created_by == old.id))
        db.delete(old)
        db.commit()
    u = create_user(db, DEMO_EMAIL, DEMO_PASSWORD, "Sachin Demo")
    u.about = (
        "Software developer (Angular, React, Node.js, Python, Django, Java Spring Boot, SQL, DevOps). Prepared for UPSC "
        "2018-2023, then moved into IT. Goals: grow as a full-stack engineer, raise income, build financial stability, "
        "stay consistent at the gym, lose body fat, hit protein daily and explore side income from teaching/UPSC mentoring."
    )
    db.flush()
    ws = db.scalar(select(M.WorkspaceMember.workspace_id).where(M.WorkspaceMember.user_id == u.id))
    own = dict(owner_id=u.id, workspace_id=ws)
    today = datetime.now(IST).date()

    def add(obj):
        db.add(obj)
        return obj

    # ---------------- goals & milestones
    g_career = add(M.Goal(**own, title="Land a senior full-stack role (+40% salary)", area="career", target_date=today + timedelta(days=180), description="Strengthen system design, ship portfolio projects, interview actively."))
    g_fat = add(M.Goal(**own, title="Reach 15% body fat", area="fitness", target_date=today + timedelta(days=150), metric_unit="% body fat", start_value=Decimal(22), target_value=Decimal(15), current_value=Decimal("20.4")))
    g_fund = add(M.Goal(**own, title="Build 6-month emergency fund", area="finance", target_date=today + timedelta(days=300), metric_unit="₹", start_value=Decimal(0), target_value=Decimal(300000), current_value=Decimal(118000)))
    g_side = add(M.Goal(**own, title="Earn first ₹10,000 from side income", area="side_income", target_date=today + timedelta(days=90)))
    db.flush()
    for i, t in enumerate(["Finish system design course", "Build & deploy portfolio project", "10 mock interviews", "Apply to 25 roles"]):
        add(M.Milestone(**own, goal_id=g_career.id, title=t, due_date=today + timedelta(days=30 * (i + 1)), done=i == 0))
    for i, t in enumerate(["Validate mentorship demand (10 conversations)", "First paying mentee", "Publish 8 current-affairs explainers"]):
        add(M.Milestone(**own, goal_id=g_side.id, title=t, due_date=today + timedelta(days=20 * (i + 1)), done=False))

    # ---------------- tasks
    task_specs = [
        ("Revise Kafka consumer groups for interview", "learning", "high", 0, 45),
        ("Fix flaky integration test in billing service", "professional", "urgent", 0, 60),
        ("Push day: chest, shoulders, triceps", "fitness", "medium", 0, 75),
        ("Pay credit card bill", "finance", "high", 1, 10),
        ("Draft blog post: UPSC to software engineer", "side_income", "medium", 3, 90),
        ("Call 3 aspirants for mentorship validation", "side_income", "high", -2, 45),
        ("Update resume with Q3 achievements", "professional", "high", -4, 60),
        ("Book dentist appointment", "personal", "low", 5, 10),
        ("LeetCode: 2 medium graph problems", "learning", "medium", 0, 60),
        ("Meal prep for the week", "fitness", "medium", 2, 90),
        ("Review mutual fund SIP allocation", "finance", "medium", 6, 30),
        ("Design API for portfolio project", "learning", "high", 1, 120),
    ]
    for title, cat, pr, off, est in task_specs:
        add(M.Task(**own, title=title, category=cat, priority=pr, due_date=today + timedelta(days=off), estimate_minutes=est,
                   postponed_count=3 if "resume" in title else (2 if "aspirants" in title else 0),
                   goal_id=g_career.id if cat in ("learning", "professional") else (g_side.id if cat == "side_income" else None)))
    add(M.Task(**own, title="Daily standup notes", category="professional", priority="low", due_date=today, recurrence="weekdays", estimate_minutes=10,
               scheduled_start=datetime.combine(today, time(10, 0), IST)))
    for d in range(1, 21):
        day = today - timedelta(days=d)
        for j in range(rnd.randint(1, 4)):
            cat = rnd.choice(["professional", "learning", "fitness", "personal", "finance"])
            done = rnd.random() < (0.55 if cat == "learning" else 0.8)
            add(M.Task(**own, title=f"{cat.title()} task {d}-{j}", category=cat, priority=rnd.choice(["low", "medium", "high"]), due_date=day,
                       status="done" if done else "cancelled",
                       completed_at=datetime.combine(day + timedelta(days=0 if rnd.random() < 0.8 else 1), time(18, 0), IST) if done else None))

    # ---------------- habits
    habits = [add(M.Habit(**own, name=n, area=a, target_per_week=t)) for n, a, t in [
        ("Gym", "fitness", 4), ("Read 20 pages", "learning", 7), ("No phone first hour", "personal", 7),
        ("Code 1 hour", "learning", 6), ("Journal before bed", "personal", 5)]]
    db.flush()
    for d in range(0, 35):
        day = today - timedelta(days=d)
        for h, p in zip(habits, [0.6, 0.7, 0.45, 0.75, 0.55]):
            if d == 0 and h.name in ("Gym", "Journal before bed"):
                continue
            if rnd.random() < p:
                add(M.HabitLog(**own, habit_id=h.id, date=day))

    # ---------------- finance
    subs = [add(M.Subscription(**own, name=n, amount=Decimal(a), billing_cycle=c, next_due_date=today + timedelta(days=dd), category=cat)) for n, a, c, dd, cat in [
        ("Gym membership", 1800, "monthly", 9, "fitness"), ("Netflix", 649, "monthly", 4, "subscriptions"),
        ("Spotify", 119, "monthly", 12, "subscriptions"), ("Cloud VPS", 450, "monthly", 18, "business"),
        ("Coursera Plus", 4999, "yearly", 120, "books_courses"), ("Amazon Prime", 1499, "yearly", 200, "subscriptions")]]
    db.flush()
    for m_off in (1, 0):
        first = (today.replace(day=1) - timedelta(days=1)).replace(day=1) if m_off == 1 else today.replace(day=1)
        add(M.Transaction(**own, kind="income", amount=Decimal(95000), category="salary", description="Monthly salary", date=first))
        add(M.Transaction(**own, kind="expense", amount=Decimal(16000), category="rent", description="Rent", date=first + timedelta(days=1), payment_method="upi"))
        add(M.Transaction(**own, kind="expense", amount=Decimal(15000), category="investments", description="SIP - index fund", date=first + timedelta(days=4), payment_method="bank"))
        add(M.Transaction(**own, kind="expense", amount=Decimal(1800), category="fitness", description="Gym membership", date=first + timedelta(days=2), subscription_id=subs[0].id))
        add(M.Transaction(**own, kind="expense", amount=Decimal(649), category="subscriptions", description="Netflix", date=first + timedelta(days=5), subscription_id=subs[1].id))
    daily_cats = [("groceries", 300, 1200, "BigBasket"), ("food_delivery", 250, 650, "Swiggy"), ("transport", 60, 350, "Metro / auto"),
                  ("dining", 400, 1400, "Dinner out"), ("shopping", 500, 2500, "Amazon order"), ("health", 150, 800, "Pharmacy"),
                  ("utilities", 400, 1200, "Electricity / internet")]
    for d in range(0, 40):
        day = today - timedelta(days=d)
        for cat, lo, hi, desc in daily_cats:
            freq = {"food_delivery": 0.45 if day.month == today.month else 0.25, "groceries": 0.3, "transport": 0.6, "dining": 0.12, "shopping": 0.1, "health": 0.06, "utilities": 0.05}[cat]
            if rnd.random() < freq:
                add(M.Transaction(**own, kind="expense", amount=Decimal(rnd.randint(lo, hi)), category=cat, description=desc, date=day, payment_method=rnd.choice(["upi", "card"])))
    add(M.Budget(**own, month=today.strftime("%Y-%m"), category="__total__", amount=Decimal(55000)))
    add(M.Budget(**own, month=today.strftime("%Y-%m"), category="food_delivery", amount=Decimal(3000)))
    add(M.Budget(**own, month=today.strftime("%Y-%m"), category="shopping", amount=Decimal(4000)))
    add(M.FinancialGoal(**own, name="Emergency fund", target_amount=Decimal(300000), saved_amount=Decimal(118000), target_date=today + timedelta(days=300)))
    add(M.FinancialGoal(**own, name="New laptop for side projects", target_amount=Decimal(120000), saved_amount=Decimal(35000), target_date=today + timedelta(days=150)))

    seed_investments(db, own, today, rnd)

    # ---------------- side income
    opp1 = add(M.Opportunity(**own, title="1:1 UPSC mentorship (answer-writing & strategy)", category="upsc_mentorship", status="validating",
                             description="Weekend 1:1 sessions for Mains aspirants.", estimated_investment=Decimal(2000), est_monthly_low=Decimal(4000),
                             est_monthly_high=Decimal(15000), hours_per_week=Decimal(4), skills_required=["UPSC GS", "mentoring"],
                             validation_notes="Spoke to 4 aspirants; 2 interested at ₹1,500/session.", next_action="Post offer in 2 Telegram groups", progress_pct=30))
    add(M.Opportunity(**own, title="Freelance React dashboards", category="freelancing", status="idea", est_monthly_low=Decimal(10000), est_monthly_high=Decimal(40000),
                      hours_per_week=Decimal(6), skills_required=["React", "TypeScript", "Node.js"], next_action="Create 2 case studies"))
    add(M.Opportunity(**own, title="Technical blog: UPSC to software engineer", category="blogging", status="active", hours_per_week=Decimal(2),
                      skills_required=["writing"], next_action="Publish post #3", progress_pct=20))
    db.flush()
    add(M.Transaction(**own, kind="income", amount=Decimal(1500), category="teaching", description="Mentorship trial session", date=today - timedelta(days=6), opportunity_id=opp1.id))
    add(M.Transaction(**own, kind="expense", amount=Decimal(499), category="business", description="Calendly + Zoom add-on", date=today - timedelta(days=10), opportunity_id=opp1.id))

    # ---------------- learning
    skills = [add(M.Skill(**own, name=n, category=c, current_level=cl, target_level=tl, status=s, priority=p)) for n, c, cl, tl, s, p in [
        ("System Design", "architecture", 2, 4, "learning", "high"), ("Data Structures & Algorithms", "cs_fundamentals", 2, 4, "learning", "high"),
        ("React + TypeScript", "frontend", 3, 5, "learning", "medium"), ("Spring Boot microservices", "backend", 3, 4, "planned", "medium"),
        ("Kubernetes", "devops", 1, 3, "planned", "medium"), ("Apache Kafka", "backend", 1, 3, "learning", "high"),
        ("LLM application engineering", "ai", 1, 3, "planned", "high")]]
    db.flush()
    for i, t in enumerate(["Scalability basics & back-of-envelope estimates", "Caching, CDNs, load balancing", "Databases: replication, sharding", "Message queues & event-driven design", "Design: URL shortener", "Design: news feed", "Design: chat system"]):
        add(M.RoadmapItem(**own, skill_id=skills[0].id, title=t, order_index=i, done=i < 3))
    for i, t in enumerate(["Arrays & hashing", "Two pointers & sliding window", "Trees & BST", "Graphs: BFS/DFS", "Dynamic programming"]):
        add(M.RoadmapItem(**own, skill_id=skills[1].id, title=t, order_index=i, done=i < 2))
    for d in range(0, 28):
        if rnd.random() < 0.7:
            s = rnd.choice(skills[:6])
            add(M.LearningLog(**own, date=today - timedelta(days=d), minutes=rnd.choice([30, 45, 60, 90]), skill_id=s.id, topic=f"{s.name} practice"))
    add(M.KnowledgeNote(**own, title="Idempotent Kafka consumer", kind="snippet", language="java", tags=["kafka", "spring"], skill_id=skills[5].id,
                        content='@KafkaListener(topics = "orders")\npublic void on(OrderEvent e) {\n  if (processed.existsById(e.id())) return; // dedupe\n  service.handle(e);\n  processed.save(new Processed(e.id()));\n}'))
    add(M.KnowledgeNote(**own, title="CAP theorem in one paragraph", kind="note", tags=["system-design"], skill_id=skills[0].id,
                        content="Under a network partition a distributed store must choose consistency (reject/queue writes) or availability (accept writes that may conflict)."))
    add(M.Resource(**own, title="Designing Data-Intensive Applications", kind="book", status="in_progress", skill_id=skills[0].id))
    add(M.Resource(**own, title="Kafka: The Definitive Guide (ch. 4)", kind="book", status="to_read", skill_id=skills[5].id))
    add(M.Resource(**own, title="React docs: You might not need an effect", url="https://react.dev/learn/you-might-not-need-an-effect", kind="docs", status="done", skill_id=skills[2].id))
    add(M.LearningItem(**own, kind="course", title="Grokking the System Design Interview", provider="DesignGurus", status="in_progress", progress_pct=45))
    add(M.LearningItem(**own, kind="project", title="AAROH personal life OS", status="in_progress", progress_pct=60))
    add(M.LearningItem(**own, kind="certification", title="CKAD", provider="CNCF", status="planned"))
    for topic, cat, st, conf in [("Rate limiter design", "system_design", "practicing", 2), ("LRU cache", "dsa", "confident", 4), ("Dijkstra's algorithm", "dsa", "practicing", 2),
                                 ("React reconciliation", "frontend", "confident", 4), ("Spring transaction propagation", "backend", "todo", 1),
                                 ("SQL window functions", "database", "practicing", 3), ("Tell me about a conflict", "behavioral", "todo", 2)]:
        add(M.InterviewItem(**own, topic=topic, category=cat, status=st, confidence=conf))

    # ---------------- fitness
    w = 84.6
    for d in range(35, -1, -1):
        day = today - timedelta(days=d)
        w -= rnd.uniform(-0.15, 0.25)
        if d % 3 == 0:
            add(M.BodyMetric(**own, date=day, weight_kg=Decimal(f"{w:.1f}"), body_fat_pct=Decimal(f"{22 - (35 - d) * 0.045:.1f}"), waist_cm=Decimal(f"{92 - (35 - d) * 0.08:.1f}")))
        if d > 0:
            add(M.DailyActivity(**own, date=day, steps=rnd.randint(4500, 11500), water_ml=rnd.choice([2000, 2500, 3000, 3500]), sleep_hours=Decimal(str(rnd.choice([6, 6.5, 7, 7.5, 8]))), active_minutes=rnd.randint(20, 80)))
        else:
            add(M.DailyActivity(**own, date=day, steps=3200, water_ml=1250, sleep_hours=Decimal("6.5")))
        plan = {0: ("Push", ["Bench press", "Overhead press", "Incline dumbbell press", "Triceps pushdown"]),
                1: ("Pull", ["Deadlift", "Lat pulldown", "Barbell row", "Biceps curl"]),
                3: ("Legs", ["Back squat", "Romanian deadlift", "Leg press", "Calf raise"]),
                4: ("Upper", ["Bench press", "Pull-up", "Lateral raise", "Face pull"])}
        if day.weekday() in plan and d > 0:
            title, exs = plan[day.weekday()]
            skipped = rnd.random() < 0.2
            wk = add(M.Workout(**own, date=day, title=f"{title} day", workout_type="strength", duration_minutes=None if skipped else rnd.randint(55, 80),
                               status="skipped" if skipped else "done", attended_gym=not skipped))
            if not skipped:
                prog = (35 - d) * 0.15
                for ex in exs:
                    base = {"Bench press": 60, "Overhead press": 35, "Deadlift": 100, "Back squat": 80, "Barbell row": 55, "Leg press": 140}.get(ex, 15)
                    for sn in range(1, 4):
                        wk.sets.append(M.WorkoutSet(exercise=ex, set_number=sn, reps=rnd.choice([6, 8, 10, 12]), weight_kg=Decimal(f"{base + prog:.1f}")))
        meals = [("breakfast", "Oats with whey & banana", 420, 32), ("lunch", "Dal, rice, paneer bhurji, salad", 720, 38),
                 ("snack", "Greek yogurt + peanuts", 280, 20), ("dinner", "Chicken curry with 2 rotis", 650, 42)]
        for meal, food, cal, prot in meals:
            if d == 0 and meal in ("snack", "dinner"):
                continue
            if rnd.random() < 0.9:
                add(M.FoodLog(**own, date=day, meal=meal, food=food, calories=cal + rnd.randint(-60, 60), protein_g=Decimal(prot + rnd.randint(-6, 6)), carbs_g=Decimal(cal // 8), fat_g=Decimal(cal // 30)))
    add(M.Workout(**own, date=today, title="Push day", workout_type="strength", status="planned"))

    # ---------------- work journal
    work = [
        ("Billing service", "Implemented retry with exponential backoff for payment webhooks.", "Webhook retries", "Duplicate events from provider", "Added idempotency keys table", "Idempotency patterns", "Load test retries"),
        ("Billing service", "Migrated invoices API to pagination with cursors.", "Cursor pagination", "Offset queries were slow on 2M rows", "Keyset pagination on (created_at,id)", "Postgres index-only scans", ""),
        ("Customer portal", "Built React form for KYC upload with validation.", "KYC form", "Large image uploads timing out", "Client-side compression + presigned S3 URLs", "Presigned URL flow", "Accessibility review"),
        ("Internal tooling", "Set up GitHub Actions caching to cut CI from 14 to 6 minutes.", "CI caching", "Cache misses on lockfile changes", "Keyed caches by lockfile hash", "Actions cache scopes", ""),
        ("Customer portal", "Fixed timezone bug in statement dates for IST users.", "Timezone fix", "Dates off by one", "Store UTC, render with user TZ", "", "Add regression tests"),
    ]
    for i, (proj, summ, done, prob, sol, learn, pend) in enumerate(work):
        day = today - timedelta(days=i + (1 if i >= today.weekday() else 0))
        add(M.WorkLog(**own, date=day, project=proj, summary=summ, tasks_completed=done, problems=prob, solutions=sol, learnings=learn, pending=pend, hours=Decimal(rnd.choice([7, 8, 8.5, 9]))))

    # ---------------- journal
    entries = [
        (1, "reflection", "Skipped gym again", "Third skip this month on a Wednesday. Late meetings drain me; I should move gym to mornings on Wednesdays.", 2, ["gym", "energy"]),
        (3, "achievement", "Shipped cursor pagination", "Reduced invoices API p95 from 1.8s to 220ms. Felt great to see the graph drop.", 5, ["work", "win"]),
        (5, "lesson", "UPSC habits still help", "The answer-writing discipline from UPSC days helps me write clear design docs. That's an asset, not lost time.", 4, ["upsc", "career"]),
        (8, "decision", "Started mentorship validation", "Decided to test 1:1 mentorship before building a course.", 4, ["side-income", "upsc"]),
        (11, "reflection", "Phone in the morning", "Started the day on Instagram, lost 40 minutes, felt scattered until lunch.", 2, ["distraction", "phone"]),
        (14, "experience", "Weekend trek to Rajmachi", "Monsoon trek with college friends. Reset my head completely.", 5, ["travel", "friends"]),
        (18, "reflection", "Money anxiety", "Swiggy orders crept up during crunch week. Need a plan for late-night food.", 3, ["money", "food"]),
    ]
    for off, kind, title, body, mood, tags in entries:
        add(M.JournalEntry(**own, entry_date=today - timedelta(days=off), kind=kind, title=title, body=body, mood=mood, energy=mood, tags=tags,
                           decision_outcome="2 interested so far" if kind == "decision" else ""))
    db.commit()
    db.close()
    print(f"Seeded demo user {DEMO_EMAIL} / {DEMO_PASSWORD}")


def seed_investments(db, own: dict, today: date, rnd: random.Random) -> None:
    """Demo holdings, loans and net-worth history (also back-fills older demo accounts that predate investments)."""
    def add(obj):
        db.add(obj)
        return obj

    D = Decimal
    for name, cls, platform, inv, cur, extra in [
        ("Nifty 50 index fund", "mutual_fund", "Groww", 168000, 201500, dict(sip_amount=D(8000), sip_day=5, risk="high", start_date=today - timedelta(days=700))),
        ("Flexi cap fund", "mutual_fund", "Groww", 72000, 79800, dict(sip_amount=D(4000), sip_day=10, risk="high", start_date=today - timedelta(days=540))),
        ("ELSS tax saver", "mutual_fund", "Zerodha Coin", 45000, 51200, dict(sip_amount=D(2500), sip_day=15, risk="high", start_date=today - timedelta(days=500))),
        ("Employee PF", "epf", "EPFO", 186000, 214000, dict(risk="low", liquidity="locked", interest_rate=D("8.25"))),
        ("PPF account", "ppf", "SBI", 90000, 101300, dict(risk="low", liquidity="locked", interest_rate=D("7.10"), maturity_date=today + timedelta(days=365 * 12))),
        ("Bank FD", "fd", "HDFC Bank", 100000, 104600, dict(risk="low", liquidity="medium", interest_rate=D("7.25"), maturity_date=today + timedelta(days=60))),
        ("Sovereign gold bond", "sgb", "RBI via Zerodha", 30000, 38400, dict(risk="medium", liquidity="locked")),
        ("Savings account", "savings", "SBI", 118000, 118000, dict(risk="low", liquidity="high")),
    ]:
        add(M.Investment(**own, name=name, asset_class=cls, platform=platform, invested_amount=D(inv), current_value=D(cur),
                         value_updated_on=today - timedelta(days=rnd.randint(2, 20)), **{"liquidity": "medium", **extra}))
    add(M.Liability(**own, name="Two-wheeler loan", kind="car_loan", lender="Bajaj Finance", principal=D(90000), outstanding=D(38500),
                    interest_rate=D("11.5"), emi=D(4200), emi_day=7, end_date=today + timedelta(days=270)))
    add(M.Liability(**own, name="Credit card balance", kind="credit_card", lender="ICICI", outstanding=D(14200), interest_rate=D("42")))
    for i in range(6, 0, -1):  # a few months of net-worth history
        add(M.NetWorthSnapshot(**own, date=today - timedelta(days=30 * i), assets=D(820000 + (6 - i) * 21000), liabilities=D(78000 - (6 - i) * 4000), invested=D(760000 + (6 - i) * 15000)))


if __name__ == "__main__":
    import sys

    _ = timezone
    if "--if-missing" in sys.argv:
        with SessionLocal() as _db:
            demo = _db.scalar(select(M.User).where(M.User.email == DEMO_EMAIL))
            if demo:
                if not _db.scalar(select(M.Investment.id).where(M.Investment.owner_id == demo.id).limit(1)):
                    ws = _db.scalar(select(M.WorkspaceMember.workspace_id).where(M.WorkspaceMember.user_id == demo.id))
                    seed_investments(_db, dict(owner_id=demo.id, workspace_id=ws), datetime.now(IST).date(), random.Random(42))
                    _db.commit()
                    print("Added demo investments to the existing demo user")
                print("Demo user already exists; not re-seeding")
                sys.exit(0)
    run()
