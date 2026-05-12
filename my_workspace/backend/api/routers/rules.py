"""Rules router — CRUD detection rules."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from api.deps import CurrentUser, DBDep, require
from models.rule import Rule
from schemas.zone import RuleCreate, RuleRead, RuleUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=list[RuleRead], dependencies=[require("rules:read")])
async def list_rules(db: DBDep, zone_id: int | None = None) -> list[Rule]:
    query = select(Rule).order_by(Rule.id)
    if zone_id is not None:
        query = query.where(Rule.zone_id == zone_id)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=RuleRead, status_code=status.HTTP_201_CREATED,
             dependencies=[require("rules:create")])
async def create_rule(body: RuleCreate, request: Request, db: DBDep, user: CurrentUser) -> Rule:
    data = body.model_dump()
    rule = Rule(
        zone_id=data["zone_id"],
        name=data["name"],
        behavior=data["behavior"],
        confidence_threshold=data["confidence_threshold"],
        dwell_threshold_seconds=data["dwell_threshold_seconds"],
        cooldown_seconds=data["cooldown_seconds"],
        severity=data["severity"],
        schedule=json.dumps(data["schedule"]) if data["schedule"] else None,
        logic=json.dumps(data["logic"]) if data["logic"] else None,
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    await db.commit()
    await request.app.state.config_svc.invalidate("rule")
    logger.info("Rule created: id=%d behavior=%s by=%s", rule.id, rule.behavior, user.username)
    return rule


@router.get("/{rule_id}", response_model=RuleRead, dependencies=[require("rules:read")])
async def get_rule(rule_id: int, db: DBDep) -> Rule:
    rule = await db.get(Rule, rule_id)
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    return rule


@router.patch("/{rule_id}", response_model=RuleRead, dependencies=[require("rules:update")])
async def update_rule(
    rule_id: int, body: RuleUpdate, request: Request, db: DBDep, user: CurrentUser
) -> Rule:
    data = body.model_dump(exclude_none=True)
    if "schedule" in data:
        data["schedule"] = json.dumps(data["schedule"])
    if "logic" in data:
        data["logic"] = json.dumps(data["logic"])
    rule = await request.app.state.config_svc.update_rule(rule_id, data, actor=user.username)
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[require("rules:delete")])
async def delete_rule(rule_id: int, request: Request, db: DBDep, user: CurrentUser) -> None:
    rule = await db.get(Rule, rule_id)
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    await db.delete(rule)
    await db.commit()
    await request.app.state.config_svc.invalidate("rule", rule_id)
    logger.info("Rule deleted: id=%d by=%s", rule_id, user.username)
