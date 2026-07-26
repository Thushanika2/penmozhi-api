from datetime import date, datetime, time

from app.extensions import db
from app.models.ai_health_assistant_session_model import AIHealthAssistantSession
from app.models.cycle_history_log_model import CycleHistoryLog
from app.models.educational_resource_model import EducationalResource
from app.models.forum_comment_model import ForumComment
from app.models.forum_post_model import ForumPost
from app.models.health_profile_model import HealthProfile
from app.models.medication_supplement_reminder_model import MedicationSupplementReminder
from app.models.pcos_disorder_status_model import PCOSDisorderStatus
from app.models.symptom_tracking_log_model import SymptomTrackingLog
from app.models.user_profile_model import UserProfile


def seed_users():
    admin_email = "admin@penmozhi.com"
    if not UserProfile.query.filter_by(email=admin_email).first():
        admin = UserProfile(
            full_name="Penmozhi Admin",
            date_of_birth=date(2006, 3, 29),
            email=admin_email,
            language_preference="english",
            role="admin",
        )
        admin.set_password("Admin123")
        db.session.add(admin)
        db.session.flush()
        print(f"  Created admin: {admin_email}")
    else:
        print(f"  Skipped admin (exists): {admin_email}")

    user_email = "user@penmozhi.com"
    if not UserProfile.query.filter_by(email=user_email).first():
        user = UserProfile(
            full_name="Demo User",
            date_of_birth=date(1998, 5, 15),
            email=user_email,
            language_preference="tamil",
            role="user",
        )
        user.set_password("User123!")
        db.session.add(user)
        db.session.flush()

        health = HealthProfile(profile_id=user.id)
        db.session.add(health)
        db.session.flush()

        pcos = PCOSDisorderStatus(
            health_profile_id=health.id,
            disorder_type="none",
            diagnosis_status="not_diagnosed",
        )
        db.session.add(pcos)
        print(f"  Created user: {user_email}")
    else:
        print(f"  Skipped user (exists): {user_email}")

    db.session.commit()


def seed_health_data():
    user = UserProfile.query.filter_by(email="user@penmozhi.com").first()
    if not user:
        print("  Skipped wellness seed data (demo user not found).")
        return

    health_profile = HealthProfile.query.filter_by(profile_id=user.id).first()
    if not health_profile:
        health_profile = HealthProfile(
            profile_id=user.id,
            weight=62.5,
            height=1.63,
            calculated_bmi=23.5,
            nutritional_needs="Balanced meals with protein, fiber, and hydration",
            health_risks="Stress-related fatigue and occasional irregular sleep",
        )
        db.session.add(health_profile)
        db.session.flush()

    if not PCOSDisorderStatus.query.filter_by(health_profile_id=health_profile.id).first():
        pcos = PCOSDisorderStatus(
            health_profile_id=health_profile.id,
            disorder_type="pcos",
            diagnosis_status="diagnosed",
            diagnosed_date=date(2025, 4, 12),
        )
        db.session.add(pcos)
        db.session.flush()

    if not CycleHistoryLog.query.filter_by(profile_id=user.id).first():
        cycle_logs = [
            CycleHistoryLog(
                profile_id=user.id,
                cycle_start_date=date(2026, 6, 1),
                cycle_end_date=date(2026, 6, 5),
                flow_intensity="moderate",
                predicted_next_period_date=date(2026, 7, 1),
            ),
            CycleHistoryLog(
                profile_id=user.id,
                cycle_start_date=date(2026, 7, 1),
                cycle_end_date=date(2026, 7, 5),
                flow_intensity="light",
                predicted_next_period_date=date(2026, 8, 1),
            ),
        ]
        db.session.add_all(cycle_logs)

    if not SymptomTrackingLog.query.filter_by(profile_id=user.id).first():
        symptom_logs = [
            SymptomTrackingLog(
                profile_id=user.id,
                date_time=datetime(2026, 6, 3, 8, 30),
                category="pain",
                pain_severity=6,
                mood_status="tired",
                sleep_metrics="6h sleep",
            ),
            SymptomTrackingLog(
                profile_id=user.id,
                date_time=datetime(2026, 6, 4, 14, 0),
                category="mood",
                pain_severity=4,
                mood_status="stressed",
                sleep_metrics="5h sleep",
            ),
        ]
        db.session.add_all(symptom_logs)

    if not MedicationSupplementReminder.query.filter_by(profile_id=user.id).first():
        reminders = [
            MedicationSupplementReminder(
                profile_id=user.id,
                item_name="Vitamin D3",
                reminder_type="supplement",
                scheduled_time=time(8, 0),
                dosage="1000 IU",
                adherence_status="pending",
            ),
            MedicationSupplementReminder(
                profile_id=user.id,
                item_name="Iron Tablet",
                reminder_type="medication",
                scheduled_time=time(19, 30),
                dosage="1 tablet",
                adherence_status="pending",
            ),
        ]
        db.session.add_all(reminders)

    db.session.commit()
    print("  Created wellness seed data for demo user.")
    seed_forum_and_ai(user)


def seed_forum_and_ai(user):
    educational_resource = EducationalResource.query.first()
    if not educational_resource:
        print("  Skipped forum and AI seed data (no education resources found).")
        return

    if not ForumPost.query.filter_by(profile_id=user.id).first():
        post = ForumPost(
            profile_id=user.id,
            content_id=educational_resource.id,
            title="Tips for managing irregular cycles",
            body=(
                "I have been tracking my symptoms and would love to hear from others "
                "about what helped them feel more balanced."
            ),
        )
        db.session.add(post)
        db.session.flush()

        comment = ForumComment(
            post_id=post.id,
            profile_id=user.id,
            body="Keeping a simple symptom log really helped me notice patterns over time.",
        )
        db.session.add(comment)

    if not AIHealthAssistantSession.query.filter_by(profile_id=user.id).first():
        session = AIHealthAssistantSession(
            profile_id=user.id,
            symptom_analysis_log="Reported fatigue, mild cramps, and mood changes over the last week.",
            generated_recommendations="Rest, hydrate, and continue tracking symptoms for 7 days.",
            posted_messages="User: I feel tired and anxious. Assistant: Try gentle activity and balanced meals.",
            saved_chat_sessions="Session saved on 2026-06-04.",
        )
        db.session.add(session)

    db.session.commit()
    print("  Created forum and AI assistant seed data.")


def seed_education():
    if EducationalResource.query.first():
        print("  Skipped education resources (already present).")
        return

    resources = [
        EducationalResource(
            article_title="Understanding Your Menstrual Cycle",
            content_category="cycle",
            content_body=(
                "A typical menstrual cycle lasts 21–35 days. Tracking start and end "
                "dates helps predict your next period and spot irregularities."
            ),
            publication_date=date(2026, 1, 10),
        ),
        EducationalResource(
            article_title="PCOS: Signs and Support",
            content_category="pcos",
            content_body=(
                "Polycystic ovary syndrome can cause irregular cycles, acne, and "
                "weight changes. Early logging of symptoms supports conversations "
                "with a clinician."
            ),
            publication_date=date(2026, 2, 1),
        ),
        EducationalResource(
            article_title="Nutrition for Hormonal Balance",
            content_category="nutrition",
            content_body=(
                "Balanced meals with fiber, protein, and healthy fats can support "
                "energy and mood across the cycle. Stay hydrated and limit excess sugar."
            ),
            publication_date=date(2026, 3, 5),
        ),
    ]
    db.session.add_all(resources)
    db.session.commit()
    print(f"  Created {len(resources)} educational resources.")
