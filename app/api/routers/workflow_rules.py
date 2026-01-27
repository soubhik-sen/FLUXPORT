"""
Workflow Rules API

Quick verification notes:
1) Unique constraint
   - Attempt two inserts with the same (doc_category, doc_type_id, state_code, action_key).
   - Expect a 409 or IntegrityError.
2) Atomicity
   - In two concurrent sessions, attempt to insert the same composite key.
   - The database should enforce uniqueness, allowing only one commit.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.workflow_rules import SysWorkflowRule
from app.schemas.workflow_schema import (
    WorkflowRuleCreate,
    WorkflowRuleUpdate,
    WorkflowRuleResponse,
)


router = APIRouter(
    prefix="/api/v1/sys-workflow-rules",
    tags=["System Settings - Workflow Rules"],
)


@router.get("", response_model=list[WorkflowRuleResponse])
def list_workflow_rules(
    db: Session = Depends(get_db),
    doc_category: str | None = Query(None),
    doc_type_id: int | None = Query(None),
    state_code: str | None = Query(None),
    action_key: str | None = Query(None),
    required_role_id: int | None = Query(None),
    is_blocking: bool | None = Query(None),
):
    query = db.query(SysWorkflowRule)

    if doc_category is not None:
        query = query.filter(SysWorkflowRule.doc_category == doc_category)
    if doc_type_id is not None:
        query = query.filter(SysWorkflowRule.doc_type_id == doc_type_id)
    if state_code is not None:
        query = query.filter(SysWorkflowRule.state_code == state_code)
    if action_key is not None:
        query = query.filter(SysWorkflowRule.action_key == action_key)
    if required_role_id is not None:
        query = query.filter(SysWorkflowRule.required_role_id == required_role_id)
    if is_blocking is not None:
        query = query.filter(SysWorkflowRule.is_blocking == is_blocking)

    return query.order_by(SysWorkflowRule.id.desc()).all()


@router.post("", response_model=WorkflowRuleResponse, status_code=status.HTTP_201_CREATED)
def create_workflow_rule(payload: WorkflowRuleCreate, db: Session = Depends(get_db)):
    obj = SysWorkflowRule(**payload.model_dump())
    db.add(obj)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Workflow rule already exists for this category/type/state/action.",
        )
    db.refresh(obj)
    return obj


@router.patch("/{rule_id}", response_model=WorkflowRuleResponse)
def update_workflow_rule(
    rule_id: int,
    payload: WorkflowRuleUpdate,
    db: Session = Depends(get_db),
):
    obj = db.query(SysWorkflowRule).filter(SysWorkflowRule.id == rule_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Workflow rule not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Update violates workflow rule uniqueness.",
        )

    db.refresh(obj)
    return obj


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow_rule(rule_id: int, db: Session = Depends(get_db)):
    obj = db.query(SysWorkflowRule).filter(SysWorkflowRule.id == rule_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Workflow rule not found")
    db.delete(obj)
    db.commit()
    return None


@router.get("/evaluate")
def evaluate_workflow_rules(
    doc_category: str = Query(...),
    doc_type_id: int = Query(...),
    state_code: str = Query(...),
    role_id: int = Query(..., description="Current user's role id"),
    action_keys: str | None = Query(
        None, description="Optional comma-separated list of action keys"
    ),
    db: Session = Depends(get_db),
):
    """
    Evaluate which actions are allowed for a document state.
    allowed = role_id >= required_role_id
    """
    query = db.query(SysWorkflowRule).filter(
        SysWorkflowRule.doc_category == doc_category,
        SysWorkflowRule.doc_type_id == doc_type_id,
        SysWorkflowRule.state_code == state_code,
    )

    if action_keys:
        keys = [k.strip() for k in action_keys.split(",") if k.strip()]
        if keys:
            query = query.filter(SysWorkflowRule.action_key.in_(keys))

    rules = query.order_by(SysWorkflowRule.action_key.asc()).all()

    actions = [
        {
            "action_key": r.action_key,
            "required_role_id": r.required_role_id,
            "allowed": role_id >= r.required_role_id,
            "is_blocking": r.is_blocking,
        }
        for r in rules
    ]

    return {
        "doc_category": doc_category,
        "doc_type_id": doc_type_id,
        "state_code": state_code,
        "role_id": role_id,
        "is_blocking": any(r.is_blocking for r in rules),
        "actions": actions,
    }
