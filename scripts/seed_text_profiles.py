from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.text_lookups import TextTypeLookup
from app.models.text_profile import (
    TextProfile,
    ProfileTextMap,
    ProfileTextValue,
)


def _seed_profile(db: Session) -> TextProfile:
    profile = (
        db.query(TextProfile)
        .filter(TextProfile.object_type == "PO")
        .order_by(TextProfile.profile_version.desc())
        .first()
    )
    if profile:
        return profile

    profile = TextProfile(
        name="po_text_profile",
        object_type="PO",
        profile_version=1,
        is_active=True,
        created_by="seed@local",
        last_changed_by="seed@local",
    )
    db.add(profile)
    db.flush()
    return profile


def _dummy_text_for_type(text_type: TextTypeLookup) -> str:
    label = text_type.text_type_name or text_type.text_type_code or "Text"
    return f"Sample {label}"


def seed() -> None:
    db: Session = SessionLocal()
    try:
        profile = _seed_profile(db)
        text_types = (
            db.query(TextTypeLookup)
            .filter(TextTypeLookup.is_active == True)
            .order_by(TextTypeLookup.id.asc())
            .all()
        )
        map_rows = {
            map_row.text_type_id: map_row
            for map_row in (
                db.query(ProfileTextMap)
                .filter(ProfileTextMap.profile_id == profile.id)
                .all()
            )
        }

        for seq, text_type in enumerate(text_types, start=1):
            map_row = map_rows.get(text_type.id)
            if map_row is None:
                map_row = ProfileTextMap(
                    profile_id=profile.id,
                    text_type_id=text_type.id,
                    sequence=seq,
                    is_mandatory=False,
                    is_editable=True,
                    is_active=True,
                    created_by="seed@local",
                    last_changed_by="seed@local",
                )
                db.add(map_row)
                db.flush()
            else:
                map_row.sequence = seq
                map_row.is_active = True
                map_row.is_editable = True
                map_row.last_changed_by = "seed@local"

            existing_value = next(
                (
                    value
                    for value in map_row.values
                    if value.language == "en" and not value.country_code
                ),
                None,
            )
            if existing_value is None:
                value = ProfileTextValue(
                    profile_text_map_id=map_row.id,
                    language="en",
                    country_code=None,
                    text_value=_dummy_text_for_type(text_type),
                    is_active=True,
                    created_by="seed@local",
                    last_changed_by="seed@local",
                )
                db.add(value)
            else:
                existing_value.text_value = _dummy_text_for_type(text_type)
                existing_value.is_active = True
                existing_value.last_changed_by = "seed@local"

        db.commit()
        print("Text profile map/value seed completed for profile id", profile.id)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
