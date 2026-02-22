import logging

from app.core.config import settings


def _category_enabled(category: str | None) -> bool:
    if not settings.FLOW_LOGS_ENABLED:
        return False
    if category == "po_grouping":
        return settings.FLOW_LOGS_PO_GROUPING_ENABLED
    if category == "shipment":
        return settings.FLOW_LOGS_SHIPMENT_ENABLED
    return True


def flow_info(
    logger: logging.Logger,
    msg: str,
    *args,
    category: str | None = None,
    **kwargs,
) -> None:
    if _category_enabled(category):
        logger.info(msg, *args, **kwargs)

