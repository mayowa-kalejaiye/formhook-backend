"""CLI helper for running trial reminder emails."""
from ..core.database import SessionLocal
from ..services.trial_reminder import send_trial_reminders


def main() -> None:
    db = SessionLocal()
    try:
        stats = send_trial_reminders(db)
        print(f"Trial reminder emails sent -> day2: {stats['day2']}, day3: {stats['day3']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
