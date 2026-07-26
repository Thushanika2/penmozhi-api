from app.extensions import db
from app.models.tracking_category_model import TrackingCategory

TRACKING_CATEGORIES = [
    {"key": "sex_drive", "label": "Sex drive", "label_ta": "பாலியல் விருப்பம்", "group": "sex", "is_default": True},
    {"key": "sexual_activity", "label": "Sexual activity", "label_ta": "பாலியல் செயல்பாடு", "group": "sex", "is_default": True},
    {"key": "libido_low", "label": "Low libido", "label_ta": "குறைந்த பாலியல் விருப்பம்", "group": "sex", "is_default": False},
    {"key": "acne", "label": "Acne", "label_ta": "முகப்பரு", "group": "skin", "is_default": True},
    {"key": "oily_skin", "label": "Oily skin", "label_ta": "எண்ணெய் தோல்", "group": "skin", "is_default": True},
    {"key": "dry_skin", "label": "Dry skin", "label_ta": "வறண்ட தோல்", "group": "skin", "is_default": False},
    {"key": "eczema", "label": "Eczema flare", "label_ta": "எக்ஸிமா", "group": "skin", "is_default": False},
    {"key": "hives", "label": "Hives", "label_ta": "சரம்பு", "group": "skin", "is_default": False},
    {"key": "hair_loss", "label": "Hair loss", "label_ta": "முடி வளர்ச்சி குறைவு", "group": "hair", "is_default": True},
    {"key": "hirsutism", "label": "Excess hair growth", "label_ta": "அதிக முடி வளர்ச்சி", "group": "hair", "is_default": True},
    {"key": "scalp_itch", "label": "Scalp itch", "label_ta": "தலையீட்டம்", "group": "hair", "is_default": False},
    {"key": "bloating", "label": "Bloating", "label_ta": "வயிற்று வீக்கம்", "group": "digestion", "is_default": True},
    {"key": "nausea", "label": "Nausea", "label_ta": "குமட்டல்", "group": "digestion", "is_default": True},
    {"key": "constipation", "label": "Constipation", "label_ta": "மலச்சிக்கல்", "group": "digestion", "is_default": False},
    {"key": "diarrhea", "label": "Diarrhea", "label_ta": "வயிற்றுப்போக்கு", "group": "digestion", "is_default": False},
    {"key": "appetite_change", "label": "Appetite change", "label_ta": "பசியின்மை/அதிகப்பசி", "group": "digestion", "is_default": False},
    {"key": "weight_change", "label": "Weight change", "label_ta": "எடை மாற்றம்", "group": "digestion", "is_default": True},
    {"key": "fatigue", "label": "Fatigue", "label_ta": "சோர்வு", "group": "energy", "is_default": True},
    {"key": "brain_fog", "label": "Brain fog", "label_ta": "மூளை மங்கல்", "group": "energy", "is_default": True},
    {"key": "insomnia", "label": "Insomnia", "label_ta": "தூக்கமின்மை", "group": "energy", "is_default": True},
    {"key": "restless_sleep", "label": "Restless sleep", "label_ta": "அமைதியற்ற தூக்கம்", "group": "energy", "is_default": False},
    {"key": "cervical_fluid", "label": "Cervical fluid", "label_ta": "கர்ப்பப்பை fluid", "group": "discharge", "is_default": True},
    {"key": "spotting", "label": "Spotting", "label_ta": "சிறிய இரத்தப்போக்கு", "group": "discharge", "is_default": True},
    {"key": "unusual_discharge", "label": "Unusual discharge", "label_ta": "அசாதாரண சுரப்பு", "group": "discharge", "is_default": False},
    {"key": "vaginal_dryness", "label": "Vaginal dryness", "label_ta": "யோனி dryness", "group": "discharge", "is_default": False},
    {"key": "mood_swings", "label": "Mood swings", "label_ta": "மனநிலை மாற்றம்", "group": "emotions", "is_default": True},
    {"key": "anxiety", "label": "Anxiety", "label_ta": "பதட்டம்", "group": "emotions", "is_default": True},
    {"key": "irritability", "label": "Irritability", "label_ta": "எரிச்சல்", "group": "emotions", "is_default": True},
    {"key": "depression", "label": "Low mood", "label_ta": "மனச்சோர்வு", "group": "emotions", "is_default": False},
    {"key": "stress", "label": "Stress", "label_ta": "மன அழுத்தம்", "group": "emotions", "is_default": False},
]


def seed_tracking_categories():
    created = 0
    for item in TRACKING_CATEGORIES:
        existing = TrackingCategory.query.filter_by(key=item["key"]).first()
        if existing:
            continue
        db.session.add(TrackingCategory(**item))
        created += 1
    db.session.commit()
    print(f"  Tracking categories seeded: {created} new, {len(TRACKING_CATEGORIES)} total defined.")
