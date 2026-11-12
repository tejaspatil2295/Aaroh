"""Default user preferences. Nothing about the user's routine is assumed: every value is editable in Settings."""

DEFAULT_PREFERENCES: dict = {
    "timezone": "Asia/Kolkata",
    "currency": "INR",
    "day_start": "09:00",  # when planning starts each day
    "day_end": "21:00",
    "focus_block_minutes": 90,
    "break_minutes": 15,
    "daily_learning_minutes": 60,
    "weekly_learning_hours": 7,
    "daily_protein_g": 120,
    "daily_calories": 2200,
    "daily_water_ml": 3000,
    "daily_steps": 8000,
    "weekly_gym_sessions": 4,
    "monthly_budget": 30000,
    "theme": "system",
    "morning_briefing_time": "07:30",
    "evening_review_time": "21:30",
}

DEFAULT_AI_PERMISSIONS: dict = {
    "profile": True,
    "tasks": True,
    "goals": True,
    "finance": True,
    "investments": True,
    "journal": False,  # journals are most sensitive: opt-in
    "learning": True,
    "fitness": True,
    "work": True,
    "side_income": True,
}
