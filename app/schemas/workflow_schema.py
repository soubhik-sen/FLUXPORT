from typing import Optional

from pydantic import BaseModel


class WorkflowRuleBase(BaseModel):
    doc_category: str
    doc_type_id: int
    state_code: str
    action_key: str
    required_role_id: int
    is_blocking: bool = False


class WorkflowRuleCreate(WorkflowRuleBase):
    pass


class WorkflowRuleUpdate(BaseModel):
    doc_category: Optional[str] = None
    doc_type_id: Optional[int] = None
    state_code: Optional[str] = None
    action_key: Optional[str] = None
    required_role_id: Optional[int] = None
    is_blocking: Optional[bool] = None


class WorkflowRuleResponse(WorkflowRuleBase):
    id: int

    class Config:
        from_attributes = True
