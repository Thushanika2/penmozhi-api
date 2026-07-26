from app.extensions import db
from app.utils import utc_now


class TrackingCategory(db.Model):
    __tablename__ = "tracking_categories"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    label = db.Column(db.String(255), nullable=False)
    label_ta = db.Column(db.String(255), nullable=False)
    group = db.Column(db.String(50), nullable=False)
    is_default = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    symptom_tracking_logs = db.relationship(
        "SymptomTrackingLog",
        back_populates="tracking_category",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "key": self.key,
            "label": self.label,
            "label_ta": self.label_ta,
            "group": self.group,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
