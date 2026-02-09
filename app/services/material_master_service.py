from __future__ import annotations

from sqlalchemy import and_
from sqlalchemy.orm import Query, Session, aliased, contains_eager

from app.models.product_master import MaterialMaster, MaterialText


def build_material_query(db: Session, current_language: str | None = None) -> Query:
    """
    Build a MaterialMaster query with an optional language-specific join to MaterialText.
    """
    query = db.query(MaterialMaster)
    if current_language:
        text_alias = aliased(MaterialText)
        query = (
            query.outerjoin(
                text_alias,
                and_(
                    MaterialMaster.id == text_alias.material_id,
                    text_alias.language_code == current_language,
                ),
            )
            .options(contains_eager(MaterialMaster.texts, alias=text_alias))
        )
    return query
