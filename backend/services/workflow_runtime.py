from __future__ import annotations

import ast
import asyncio
import json
from pathlib import Path
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Mapping, Optional

from sqlalchemy.orm import Session

from core.database import AIReport, Asset, ScanFinding, ScanTask, WorkflowDefinition, WorkflowRun, WorkflowStepRun, WorkflowVersion
from services.ai_engine import ai_engine
from services.audit_service import AuditService
from services.mcp_client import mcp_client
from services.scanner import scanner
from services.workflow_dsl import WorkflowDSL, WorkflowNode, WorkflowRunState, validate_workflow_dsl

WorkflowAdapter = Callable[["WorkflowAdapterInput"], Awaitable["NodeExecutionResult"]]


@dataclass(slots=True)
class CompiledTransition:
    to_node: str
    condition: str
    priority: int


@dataclass(slots=True)
class CompiledNode:
    id: str
    node_type: str
    name: str
    timeout: int
    config: dict[str, Any]
    retry_policy: Any
    transitions: list[CompiledTransition] = field(default_factory=list)


@dataclass(slots=True)
class CompiledWorkflow:
    workflow_key: str
    version: int
    start_node_id: str
    terminal_node_ids: set[str]
    nodes: dict[str, CompiledNode]
    runtime_states: set[str]
    terminal_states: set[str]


@dataclass(slots=True)
class WorkflowAdapterInput:
    db: Session
    actor: str
    trace_id: str
    workflow_run: WorkflowRun
    node: CompiledNode
    input_payload: dict[str, Any]
    context: dict[str, Any]


@dataclass(slots=True)
class WorkflowRuntimeResult:
    run_id: int
    workflow_id: int
    workflow_version_id: int
    run_state: str
    trace_id: str
    reused_existing: bool = False
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WorkflowReplayResult:
    source_run_id: int
    source_run_state: str
    mode: str
    resumed_from_node_id: Optional[str]
    replay_run: WorkflowRuntimeResult
    workflow_key: str
    workflow_version: int
    debug_report: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NodeExecutionResult:
    state: str
    output: dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


_ALLOWED_AST_NODES = (
    ast.Expression,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.UnaryOp,
    ast.Not,
    ast.Compare,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    data = json.loads(value)
    return data if isinstance(data, dict) else {}


def _payload_summary(value: str | None, limit: int = 180) -> str | None:
    if not value:
        return None
    try:
        parsed = json.loads(value)
        text = json.dumps(parsed, ensure_ascii=False, default=str)
    except Exception:
        text = str(value)
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3]}..."


def _normalize_condition(condition: str) -> str:
    expr = condition.strip() or "false"
    expr = re.sub(r"\btrue\b", "True", expr, flags=re.IGNORECASE)
    expr = re.sub(r"\bfalse\b", "False", expr, flags=re.IGNORECASE)
    expr = expr.replace("&&", " and ").replace("||", " or ")
    return expr


def _validate_condition_ast(condition: str) -> ast.Expression:
    tree = ast.parse(_normalize_condition(condition), mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_AST_NODES):
            raise ValueError(f"unsupported condition syntax: {condition}")
    return tree


class WorkflowRuntimeError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False, output: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.retryable = retryable
        self.output = output or {}


def _evaluate_condition(condition: str, variables: Mapping[str, Any]) -> bool:
    tree = _validate_condition_ast(condition)
    try:
        value = eval(compile(tree, "<workflow-condition>", "eval"), {"__builtins__": {}}, dict(variables))
    except NameError:
        return False
    return bool(value)


def load_published_workflow(db: Session, workflow_key: str) -> tuple[WorkflowDefinition, WorkflowVersion, WorkflowDSL]:
    definition = (
        db.query(WorkflowDefinition)
        .filter(WorkflowDefinition.workflow_key == workflow_key)
        .first()
    )
    if definition is None or definition.published_version is None:
        raise ValueError(f"published workflow not found: {workflow_key}")

    version = (
        db.query(WorkflowVersion)
        .filter(
            WorkflowVersion.workflow_id == definition.id,
            WorkflowVersion.version == definition.published_version,
        )
        .first()
    )
    if version is None:
        raise ValueError(f"published workflow version not found: {workflow_key}@{definition.published_version}")
    return definition, version, validate_workflow_dsl(_json_loads(version.dsl_json))


def compile_workflow(payload: dict[str, Any] | WorkflowDSL) -> CompiledWorkflow:
    dsl = payload if isinstance(payload, WorkflowDSL) else validate_workflow_dsl(payload)

    nodes: dict[str, CompiledNode] = {
        node.id: CompiledNode(
            id=node.id,
            node_type=node.type,
            name=node.name,
            timeout=node.timeout,
            config=dict(node.config),
            retry_policy=node.retry_policy,
        )
        for node in dsl.nodes
    }
    incoming_count = {node_id: 0 for node_id in nodes}

    for edge in dsl.edges:
        _validate_condition_ast(edge.condition)
        incoming_count[edge.to_node] += 1
        nodes[edge.from_node].transitions.append(
            CompiledTransition(
                to_node=edge.to_node,
                condition=edge.condition,
                priority=edge.priority,
            )
        )

    start_nodes = sorted(node_id for node_id, count in incoming_count.items() if count == 0)
    if len(start_nodes) != 1:
        raise ValueError(f"workflow requires exactly one entry node, got {len(start_nodes)}")

    for node in nodes.values():
        node.transitions.sort(key=lambda item: (item.priority, item.to_node))

    terminal_node_ids = {node_id for node_id, node in nodes.items() if not node.transitions}
    runtime_states = {state.value if isinstance(state, WorkflowRunState) else str(state) for state in dsl.runtime.state_enum}
    terminal_states = {state.value if isinstance(state, WorkflowRunState) else str(state) for state in dsl.runtime.terminal_states}

    if dsl.runtime.initial_state.value not in runtime_states:
        raise ValueError("runtime.initial_state must exist in runtime.state_enum")
    if not terminal_states.issubset(runtime_states):
        raise ValueError("runtime.terminal_states must be a subset of runtime.state_enum")

    return CompiledWorkflow(
        workflow_key=dsl.workflow_id,
        version=dsl.version,
        start_node_id=start_nodes[0],
        terminal_node_ids=terminal_node_ids,
        nodes=nodes,
        runtime_states=runtime_states,
        terminal_states=terminal_states,
    )


def _extract_context_value(context: Mapping[str, Any], key: str, default: Any = None) -> Any:
    if key in context:
        return context[key]
    nested_input = context.get("input")
    if isinstance(nested_input, Mapping) and key in nested_input:
        return nested_input[key]
    event = context.get("event")
    if isinstance(event, Mapping) and key in event:
        return event[key]
    return default


def _merge_context(context: dict[str, Any], node_id: str, output: Mapping[str, Any]) -> None:
    steps = context.setdefault("steps", {})
    if isinstance(steps, dict):
        steps[node_id] = dict(output)
    context[node_id] = dict(output)
    for key, value in output.items():
        context[key] = value


def _build_initial_context(
    *,
    input_payload: Mapping[str, Any],
    trace_id: str,
    workflow_key: str,
    workflow_version: int,
    trigger_source: str,
    trigger_ref: str | None,
) -> dict[str, Any]:
    context: dict[str, Any] = {
        "input": dict(input_payload),
        "trace_id": trace_id,
        "workflow_key": workflow_key,
        "workflow_version": workflow_version,
        "trigger_source": trigger_source,
        "trigger_ref": trigger_ref,
        "steps": {},
    }
    context.update(dict(input_payload))
    event = input_payload.get("event")
    if isinstance(event, Mapping):
        context.setdefault("event", dict(event))
        for key, value in event.items():
            context.setdefault(str(key), value)
    return context


def _build_runtime_context(
    *,
    input_payload: Mapping[str, Any],
    trace_id: str,
    workflow_key: str,
    workflow_version: int,
    trigger_source: str,
    trigger_ref: str | None,
    initial_context: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    if initial_context is None:
        return _build_initial_context(
            input_payload=input_payload,
            trace_id=trace_id,
            workflow_key=workflow_key,
            workflow_version=workflow_version,
            trigger_source=trigger_source,
            trigger_ref=trigger_ref,
        )

    context = dict(initial_context)
    existing_input = context.get("input")
    merged_input = dict(existing_input) if isinstance(existing_input, Mapping) else {}
    merged_input.update(dict(input_payload))
    context["input"] = merged_input
    context.pop("last_error", None)
    context["trace_id"] = trace_id
    context["workflow_key"] = workflow_key
    context["workflow_version"] = workflow_version
    context["trigger_source"] = trigger_source
    context["trigger_ref"] = trigger_ref
    for key, value in merged_input.items():
        context[str(key)] = value
    event = merged_input.get("event")
    if isinstance(event, Mapping):
        context["event"] = dict(event)
        for key, value in event.items():
            context[str(key)] = value
    return context


def _normalize_scan_target_type(value: Any) -> str:
    mapping = {
        "ip": "host",
        "host": "host",
        "cidr": "network",
        "network": "network",
        "domain": "domain",
    }
    normalized = str(value or "host").strip().lower()
    return mapping.get(normalized, "host")


def _extract_report_summary(markdown: str, fallback: str) -> str:
    for line in str(markdown or "").splitlines():
        content = line.strip().lstrip("#").strip()
        if content:
            return content[:500]
    return fallback[:500]


def _write_generated_report(report_type: str, content: str, now: datetime) -> str:
    repo_root = Path(__file__).resolve().parents[2]
    report_dir = repo_root / "backend" / "generated_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{now.strftime('%Y%m%d_%H%M%S')}_{report_type}_{uuid.uuid4().hex[:6]}.md"
    full_path = report_dir / filename
    full_path.write_text(content, encoding="utf-8")
    return f"/generated_reports/{filename}"


async def _scan_asset_select_adapter(payload: WorkflowAdapterInput) -> NodeExecutionResult:
    asset_id_raw = payload.node.config.get("asset_id", _extract_context_value(payload.context, "asset_id"))
    asset_tag = str(payload.node.config.get("asset_tag") or _extract_context_value(payload.context, "asset_tag", "") or "").strip()
    target = str(payload.node.config.get("target") or _extract_context_value(payload.context, "target", "") or "").strip()
    target_type = _normalize_scan_target_type(
        payload.node.config.get("target_type") or _extract_context_value(payload.context, "target_type", "host")
    )

    selected_asset: Asset | None = None
    if asset_id_raw not in (None, ""):
        try:
            asset_id = int(asset_id_raw)
        except (TypeError, ValueError) as exc:
            raise WorkflowRuntimeError("scan asset selection requires a valid asset_id") from exc
        selected_asset = payload.db.query(Asset).filter(Asset.id == asset_id, Asset.enabled == 1).first()
        if selected_asset is None:
            raise WorkflowRuntimeError(f"asset not found or disabled: {asset_id}")
    elif asset_tag:
        selected_asset = (
            payload.db.query(Asset)
            .filter(Asset.enabled == 1, Asset.tags.contains(asset_tag))
            .order_by(Asset.priority.asc(), Asset.id.asc())
            .first()
        )
        if selected_asset is None:
            raise WorkflowRuntimeError(f"no enabled asset matched tag: {asset_tag}")

    if selected_asset is not None:
        target = str(selected_asset.target or "")
        target_type = _normalize_scan_target_type(selected_asset.target_type)

    if not target:
        raise WorkflowRuntimeError("scan asset selection requires target or asset_id")

    return NodeExecutionResult(
        state=WorkflowRunState.SUCCESS.value,
        output={
            "selected_asset_id": getattr(selected_asset, "id", None),
            "selected_target": target,
            "selected_target_type": target_type,
            "selected_asset_tags": getattr(selected_asset, "tags", None),
        },
    )


async def _scan_task_create_adapter(payload: WorkflowAdapterInput) -> NodeExecutionResult:
    target = str(_extract_context_value(payload.context, "selected_target", _extract_context_value(payload.context, "target", "")) or "").strip()
    if not target:
        raise WorkflowRuntimeError("scan task creation requires target")

    target_type = _normalize_scan_target_type(
        _extract_context_value(payload.context, "selected_target_type", _extract_context_value(payload.context, "target_type", payload.node.config.get("target_type")))
    )
    asset_id_raw = _extract_context_value(payload.context, "selected_asset_id", _extract_context_value(payload.context, "asset_id"))
    profile = str(payload.node.config.get("profile") or _extract_context_value(payload.context, "profile", "default") or "default")
    tool_name = str(payload.node.config.get("tool_name") or _extract_context_value(payload.context, "tool_name", "nmap") or "nmap")
    script_set_raw = payload.node.config.get("script_set")
    if script_set_raw is None:
        script_set_raw = _extract_context_value(payload.context, "script_set")
    timeout_seconds = int(payload.node.config.get("timeout_seconds") or _extract_context_value(payload.context, "timeout_seconds", 3600) or 3600)
    asset_id = 0
    if asset_id_raw not in (None, ""):
        try:
            asset_id = int(asset_id_raw)
        except (TypeError, ValueError) as exc:
            raise WorkflowRuntimeError("scan task creation received invalid asset_id") from exc

    scan_task = ScanTask(
        asset_id=asset_id,
        target=target,
        target_type=target_type,
        tool_name=tool_name,
        profile=profile,
        script_set=str(script_set_raw) if script_set_raw is not None else None,
        state="CREATED",
        timeout_seconds=timeout_seconds,
        trace_id=payload.trace_id,
        created_at=_utc_now(),
        updated_at=_utc_now(),
    )
    payload.db.add(scan_task)
    payload.db.commit()
    payload.db.refresh(scan_task)
    return NodeExecutionResult(
        state=WorkflowRunState.SUCCESS.value,
        output={
            "scan_task_id": scan_task.id,
            "scan_task_trace_id": scan_task.trace_id,
            "scan_target": scan_task.target,
            "scan_target_type": scan_task.target_type,
            "scan_profile": scan_task.profile,
            "scan_tool_name": scan_task.tool_name,
        },
    )


async def _scan_result_parse_adapter(payload: WorkflowAdapterInput) -> NodeExecutionResult:
    scan_task_id_raw = _extract_context_value(payload.context, "scan_task_id")
    try:
        scan_task_id = int(scan_task_id_raw)
    except (TypeError, ValueError) as exc:
        raise WorkflowRuntimeError("scan execution requires scan_task_id") from exc

    scan_task = payload.db.query(ScanTask).filter(ScanTask.id == scan_task_id).first()
    if scan_task is None:
        raise WorkflowRuntimeError(f"scan task not found: {scan_task_id}")

    try:
        result = await scanner._run_scan_workflow(
            scan_task.id,
            scan_task.target,
            scan_task.tool_name,
            scan_task.profile,
            scan_task.script_set,
            payload.actor,
            scan_task.timeout_seconds,
        )
    except Exception as exc:
        raise WorkflowRuntimeError(str(exc)) from exc

    payload.db.expire_all()
    refreshed_task = payload.db.query(ScanTask).filter(ScanTask.id == scan_task_id).first()
    findings_count = (
        payload.db.query(ScanFinding)
        .filter(ScanFinding.scan_task_id == scan_task_id)
        .count()
    )
    if refreshed_task is None:
        raise WorkflowRuntimeError(f"scan task not found after execution: {scan_task_id}")
    if refreshed_task.state != "REPORTED":
        status = str(result.get("status") or "failed").lower()
        retryable = status == "timeout"
        raise WorkflowRuntimeError(
            str(refreshed_task.error_message or result.get("error") or status or "scan task failed"),
            retryable=retryable,
            output={"scan_task_id": scan_task_id, "result": result},
        )

    return NodeExecutionResult(
        state=WorkflowRunState.SUCCESS.value,
        output={
            "scan_task_id": scan_task_id,
            "scan_task_state": refreshed_task.state,
            "scan_findings_count": findings_count,
            "scan_raw_output_path": refreshed_task.raw_output_path,
        },
    )


async def _scan_report_adapter(payload: WorkflowAdapterInput) -> NodeExecutionResult:
    scan_task_id_raw = _extract_context_value(payload.context, "scan_task_id")
    try:
        scan_task_id = int(scan_task_id_raw)
    except (TypeError, ValueError) as exc:
        raise WorkflowRuntimeError("scan report generation requires scan_task_id") from exc

    scan_task = payload.db.query(ScanTask).filter(ScanTask.id == scan_task_id).first()
    if scan_task is None:
        raise WorkflowRuntimeError(f"scan task not found for report: {scan_task_id}")

    findings = (
        payload.db.query(ScanFinding)
        .filter(ScanFinding.scan_task_id == scan_task_id)
        .order_by(ScanFinding.id.asc())
        .all()
    )
    high_count = sum(1 for item in findings if str(getattr(item, "severity", "") or "").upper() == "HIGH")
    summary_fallback = f"扫描任务 {scan_task_id} 目标 {scan_task.target} 共 {len(findings)} 条发现（高危 {high_count}）"
    report_payload = {
        "scan_task": {
            "id": scan_task.id,
            "target": scan_task.target,
            "target_type": scan_task.target_type,
            "tool_name": scan_task.tool_name,
            "profile": scan_task.profile,
            "state": scan_task.state,
        },
        "findings_count": len(findings),
        "high_findings": high_count,
        "findings": [
            {
                "asset": item.asset,
                "port": item.port,
                "service": item.service,
                "severity": item.severity,
                "status": item.status,
                "evidence": item.evidence,
            }
            for item in findings[:50]
        ],
    }
    ai_result = await ai_engine.generate_report(
        str(payload.node.config.get("report_type") or "scan"),
        report_payload,
        trace_id=payload.trace_id,
        with_meta=True,
    )
    report_content = str(ai_result.get("text") or "").strip() or summary_fallback
    summary = _extract_report_summary(report_content, summary_fallback)
    detail_path = _write_generated_report("scan", report_content, _utc_now())
    report = AIReport(
        report_type="scan",
        scope=str(payload.node.config.get("scope") or f"scan_task:{scan_task_id}"),
        summary=summary,
        detail_path=detail_path,
        trace_id=payload.trace_id,
        created_at=_utc_now(),
    )
    payload.db.add(report)
    payload.db.commit()
    payload.db.refresh(report)
    return NodeExecutionResult(
        state=WorkflowRunState.SUCCESS.value,
        output={
            "report_id": report.id,
            "report_summary": summary,
            "report_path": detail_path,
            "report_degraded": bool(ai_result.get("degraded")),
            "scan_task_id": scan_task_id,
        },
    )


async def _trigger_adapter(payload: WorkflowAdapterInput) -> NodeExecutionResult:
    return NodeExecutionResult(
        state=WorkflowRunState.SUCCESS.value,
        output={
            "trigger_source": payload.context.get("trigger_source"),
            "trigger_ref": payload.context.get("trigger_ref"),
        },
    )


async def _manual_approval_adapter(payload: WorkflowAdapterInput) -> NodeExecutionResult:
    decisions = payload.context.get("approval_decisions")
    decision: Any = None
    if isinstance(decisions, Mapping):
        decision = decisions.get(payload.node.id)
    if decision is None:
        return NodeExecutionResult(
            state=WorkflowRunState.MANUAL_REQUIRED.value,
            output={"approved": None, "approval_required": True},
        )

    approved = bool(decision)
    approval_reason = None
    if isinstance(decision, Mapping):
        approved = bool(decision.get("approved"))
        raw_reason = decision.get("reason")
        approval_reason = str(raw_reason) if raw_reason is not None else None
    return NodeExecutionResult(
        state=WorkflowRunState.SUCCESS.value,
        output={"approved": approved, "approval_reason": approval_reason},
    )


async def _ai_assess_adapter(payload: WorkflowAdapterInput) -> NodeExecutionResult:
    ip = str(_extract_context_value(payload.context, "ip", "") or "")
    attack_type = str(_extract_context_value(payload.context, "threat_label", "") or "")
    attack_count = int(_extract_context_value(payload.context, "attack_count", 1) or 1)
    if not ip or not attack_type:
        raise WorkflowRuntimeError("ai_assess requires ip and threat_label")
    result = await ai_engine.assess_threat(
        ip=ip,
        attack_type=attack_type,
        attack_count=attack_count,
        history=str(_extract_context_value(payload.context, "history", "") or "") or None,
        trace_id=payload.trace_id,
    )
    return NodeExecutionResult(state=WorkflowRunState.SUCCESS.value, output=result)


async def _mcp_action_adapter(payload: WorkflowAdapterInput) -> NodeExecutionResult:
    service = str(payload.node.config.get("service") or "").strip()
    ip = str(_extract_context_value(payload.context, "ip", "") or "")
    device_id_raw = _extract_context_value(payload.context, "device_id", payload.node.config.get("device_id"))
    device_id = int(device_id_raw) if isinstance(device_id_raw, int) or (isinstance(device_id_raw, str) and device_id_raw.isdigit()) else None
    if not ip:
        raise WorkflowRuntimeError("mcp_action requires ip")

    if service == "mcp_client.block_ip":
        result = await mcp_client.block_ip(ip, device_id=device_id, operator=payload.actor)
    elif service == "mcp_client.unblock_ip":
        result = await mcp_client.unblock_ip(ip, device_id=device_id, operator=payload.actor)
    else:
        raise WorkflowRuntimeError(f"unsupported mcp action service: {service}")

    if not result.get("success"):
        raise WorkflowRuntimeError(
            str(result.get("error") or "mcp action failed"),
            retryable=bool(result.get("retryable")),
            output=result,
        )
    return NodeExecutionResult(
        state=WorkflowRunState.SUCCESS.value,
        output={"action_result": result, "action_service": service},
    )


async def _audit_adapter(payload: WorkflowAdapterInput) -> NodeExecutionResult:
    action = str(payload.node.config.get("action") or f"workflow_step:{payload.node.id}")
    target = str(payload.node.config.get("target") or f"workflow_run:{payload.workflow_run.id}")
    reason = payload.node.config.get("reason")
    if reason is None:
        reason = _json_dumps(
            {
                "workflow_key": payload.context.get("workflow_key"),
                "node_id": payload.node.id,
                "approved": payload.context.get("approved"),
                "score": payload.context.get("score"),
            }
        )
    AuditService.log(
        db=payload.db,
        actor=payload.actor,
        action=action,
        target=target,
        target_type="workflow_run",
        reason=str(reason),
        result="success",
        trace_id=payload.trace_id,
        auto_commit=False,
    )
    return NodeExecutionResult(state=WorkflowRunState.SUCCESS.value, output={"audited": True})


_NODE_TYPE_ADAPTERS: dict[str, WorkflowAdapter] = {
    "trigger": _trigger_adapter,
    "manual_approval": _manual_approval_adapter,
    "approval": _manual_approval_adapter,
    "ai_assess": _ai_assess_adapter,
    "mcp_action": _mcp_action_adapter,
    "scan_asset_select": _scan_asset_select_adapter,
    "scan_task_create": _scan_task_create_adapter,
    "scan_result_parse": _scan_result_parse_adapter,
    "scan_report": _scan_report_adapter,
    "audit": _audit_adapter,
}

_SERVICE_ADAPTERS: dict[str, WorkflowAdapter] = {
    "ai_engine.assess_threat": _ai_assess_adapter,
    "mcp_client.block_ip": _mcp_action_adapter,
    "mcp_client.unblock_ip": _mcp_action_adapter,
    "scan.select_asset": _scan_asset_select_adapter,
    "scan.create_task": _scan_task_create_adapter,
    "scan.run_task": _scan_result_parse_adapter,
    "scan.generate_report": _scan_report_adapter,
    "audit_service.log": _audit_adapter,
    "AuditService.log": _audit_adapter,
}


def _resolve_adapter(node: CompiledNode, adapters: Optional[Mapping[str, WorkflowAdapter]] = None) -> WorkflowAdapter:
    service = str(node.config.get("service") or "").strip()
    if adapters and service and service in adapters:
        return adapters[service]
    if adapters and node.node_type in adapters:
        return adapters[node.node_type]
    if service and service in _SERVICE_ADAPTERS:
        return _SERVICE_ADAPTERS[service]
    if node.node_type in _NODE_TYPE_ADAPTERS:
        return _NODE_TYPE_ADAPTERS[node.node_type]
    raise WorkflowRuntimeError(f"no adapter registered for node {node.id}")


def _update_run(
    db: Session,
    workflow_run: WorkflowRun,
    *,
    state: str,
    context: Mapping[str, Any],
    ended: bool = False,
) -> None:
    now = _utc_now()
    workflow_run.run_state = state
    workflow_run.context_json = _json_dumps(context)
    workflow_run.updated_at = now
    if workflow_run.started_at is None and state != WorkflowRunState.QUEUED.value:
        workflow_run.started_at = now
    if ended:
        workflow_run.ended_at = now
        workflow_run.output_payload = _json_dumps(context)
    db.commit()


def _load_workflow_run_bundle(
    db: Session,
    *,
    run_id: int,
) -> tuple[WorkflowRun, WorkflowDefinition, WorkflowVersion, CompiledWorkflow]:
    row = (
        db.query(WorkflowRun, WorkflowDefinition, WorkflowVersion)
        .join(WorkflowDefinition, WorkflowDefinition.id == WorkflowRun.workflow_id)
        .join(WorkflowVersion, WorkflowVersion.id == WorkflowRun.workflow_version_id)
        .filter(WorkflowRun.id == run_id)
        .first()
    )
    if row is None:
        raise WorkflowRuntimeError(f"workflow run not found: {run_id}")
    run, definition, version = row
    compiled = compile_workflow(_json_loads(version.dsl_json))
    return run, definition, version, compiled


def _load_step_runs(db: Session, *, run_id: int) -> list[WorkflowStepRun]:
    return (
        db.query(WorkflowStepRun)
        .filter(WorkflowStepRun.workflow_run_id == run_id)
        .order_by(WorkflowStepRun.id.asc())
        .all()
    )


def _resolve_resume_step(steps: list[WorkflowStepRun]) -> WorkflowStepRun | None:
    for step in reversed(steps):
        if str(step.step_state or "").upper() in {WorkflowRunState.FAILED.value, WorkflowRunState.MANUAL_REQUIRED.value}:
            return step
    return None


def _debug_recommendations(step: WorkflowStepRun | None, error_message: str | None) -> list[str]:
    message = str(error_message or "").lower()
    recommendations: list[str] = []
    if "timeout" in message:
        recommendations.append("检查外部依赖可达性，并视情况提高节点 timeout / retry_policy。")
    if "requires ip" in message:
        recommendations.append("补齐 `ip` 参数后再重放，必要时使用参数覆盖修复上下文。")
    if step is not None and step.node_type == "manual_approval":
        recommendations.append("在覆盖参数中补充 `approval_decisions.<node_id>` 后执行失败节点续跑。")
    if step is not None and step.node_type == "mcp_action":
        recommendations.append("确认 MCP/FW 连通性、device_id 和操作者身份，再尝试继续执行。")
    if step is not None and step.node_type.startswith("scan"):
        recommendations.append("核对资产目标、扫描 profile、扫描器执行环境与结果目录权限。")
    if not recommendations:
        recommendations.append("可先查看失败节点输入摘要，再用参数覆盖执行完整重放或从失败节点继续。")
    return recommendations


def build_workflow_debug_report(
    db: Session,
    *,
    run_id: int,
    mode: str = "inspect",
    overrides: Optional[Mapping[str, Any]] = None,
    resumed_from_node_id: str | None = None,
    replay_run: Optional[WorkflowRuntimeResult] = None,
) -> dict[str, Any]:
    run, definition, version, _compiled = _load_workflow_run_bundle(db, run_id=run_id)
    steps = _load_step_runs(db, run_id=run_id)
    failed_step = _resolve_resume_step(steps)
    context = _json_loads(run.context_json)
    input_payload = _json_loads(run.input_payload)
    last_error = str(context.get("last_error") or getattr(failed_step, "error_message", "") or "") or None
    return {
        "source_run": {
            "run_id": run.id,
            "workflow_id": definition.id,
            "workflow_key": definition.workflow_key,
            "workflow_name": definition.name,
            "workflow_version": version.version,
            "run_state": run.run_state,
            "trace_id": run.trace_id,
            "trigger_source": run.trigger_source,
            "trigger_ref": run.trigger_ref,
        },
        "resume_candidate": {
            "node_id": getattr(failed_step, "node_id", None),
            "node_type": getattr(failed_step, "node_type", None),
            "step_state": getattr(failed_step, "step_state", None),
            "attempt": getattr(failed_step, "attempt", None),
            "error_message": getattr(failed_step, "error_message", None),
        },
        "replay_hints": {
            "mode": mode,
            "resume_supported": failed_step is not None,
            "resumed_from_node_id": resumed_from_node_id,
            "override_keys": sorted(str(key) for key in (overrides or {}).keys()),
            "input_keys": sorted(str(key) for key in input_payload.keys()),
            "last_error": last_error,
        },
        "recommendations": _debug_recommendations(failed_step, last_error),
        "step_failures": [
            {
                "node_id": step.node_id,
                "node_type": step.node_type,
                "step_state": step.step_state,
                "attempt": step.attempt,
                "error_message": step.error_message,
                "started_at": step.started_at.isoformat() if step.started_at is not None else None,
                "ended_at": step.ended_at.isoformat() if step.ended_at is not None else None,
            }
            for step in steps
            if str(step.step_state or "").upper() in {WorkflowRunState.FAILED.value, WorkflowRunState.MANUAL_REQUIRED.value}
        ],
        "latest_steps": [
            {
                "node_id": step.node_id,
                "node_type": step.node_type,
                "step_state": step.step_state,
                "attempt": step.attempt,
                "input_summary": _payload_summary(step.input_payload),
                "output_summary": _payload_summary(step.output_payload),
            }
            for step in steps[-5:]
        ],
        "replay_result": None
        if replay_run is None
        else {
            "run_id": replay_run.run_id,
            "run_state": replay_run.run_state,
            "trace_id": replay_run.trace_id,
            "reused_existing": replay_run.reused_existing,
        },
    }


def _create_step_run(
    db: Session,
    *,
    workflow_run: WorkflowRun,
    workflow_id: int,
    workflow_version_id: int,
    node: CompiledNode,
    attempt: int,
    trace_id: str,
    input_payload: Mapping[str, Any],
) -> WorkflowStepRun:
    step = WorkflowStepRun(
        workflow_run_id=workflow_run.id,
        workflow_id=workflow_id,
        workflow_version_id=workflow_version_id,
        node_id=node.id,
        node_type=node.node_type,
        step_state=WorkflowRunState.QUEUED.value,
        attempt=attempt,
        input_payload=_json_dumps(input_payload),
        trace_id=trace_id,
        created_at=_utc_now(),
        updated_at=_utc_now(),
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


async def _execute_node(
    db: Session,
    *,
    workflow_run: WorkflowRun,
    workflow_id: int,
    workflow_version_id: int,
    node: CompiledNode,
    actor: str,
    trace_id: str,
    context: dict[str, Any],
    adapters: Optional[Mapping[str, WorkflowAdapter]] = None,
) -> NodeExecutionResult:
    max_attempts = int(getattr(node.retry_policy, "max_retries", 0)) + 1
    backoff_seconds = int(getattr(node.retry_policy, "backoff_seconds", 1))
    backoff_multiplier = float(getattr(node.retry_policy, "backoff_multiplier", 1.0))
    adapter = _resolve_adapter(node, adapters)

    for attempt in range(1, max_attempts + 1):
        step = _create_step_run(
            db,
            workflow_run=workflow_run,
            workflow_id=workflow_id,
            workflow_version_id=workflow_version_id,
            node=node,
            attempt=attempt,
            trace_id=trace_id,
            input_payload=context,
        )
        step.step_state = WorkflowRunState.RUNNING.value
        step.started_at = _utc_now()
        step.updated_at = _utc_now()
        db.commit()

        try:
            result = await asyncio.wait_for(
                adapter(
                    WorkflowAdapterInput(
                        db=db,
                        actor=actor,
                        trace_id=trace_id,
                        workflow_run=workflow_run,
                        node=node,
                        input_payload=dict(context),
                        context=context,
                    )
                ),
                timeout=node.timeout,
            )
            if result.state == WorkflowRunState.MANUAL_REQUIRED.value:
                step.step_state = WorkflowRunState.MANUAL_REQUIRED.value
                step.output_payload = _json_dumps(result.output)
                step.ended_at = _utc_now()
                step.updated_at = _utc_now()
                db.commit()
                return result

            step.step_state = WorkflowRunState.SUCCESS.value
            step.output_payload = _json_dumps(result.output)
            step.error_message = None
            step.ended_at = _utc_now()
            step.updated_at = _utc_now()
            db.commit()
            return result
        except asyncio.TimeoutError as exc:
            error = WorkflowRuntimeError(f"node timeout: {node.id}", retryable=True)
        except WorkflowRuntimeError as exc:
            error = exc
        except Exception as exc:
            error = WorkflowRuntimeError(str(exc), retryable=False)

        should_retry = error.retryable and attempt < max_attempts
        step.step_state = WorkflowRunState.RETRYING.value if should_retry else WorkflowRunState.FAILED.value
        step.error_message = str(error)
        step.output_payload = _json_dumps(error.output)
        step.ended_at = _utc_now()
        step.updated_at = _utc_now()
        db.commit()

        if not should_retry:
            raise error

        _update_run(db, workflow_run, state=WorkflowRunState.RETRYING.value, context=context)
        delay = backoff_seconds * (backoff_multiplier ** (attempt - 1))
        await asyncio.sleep(delay)
        _update_run(db, workflow_run, state=WorkflowRunState.RUNNING.value, context=context)

    raise WorkflowRuntimeError(f"node execution exhausted: {node.id}")


def _select_next_node(node: CompiledNode, context: Mapping[str, Any]) -> str | None:
    if not node.transitions:
        return None
    for transition in node.transitions:
        if _evaluate_condition(transition.condition, context):
            return transition.to_node
    raise WorkflowRuntimeError(f"no transition matched for node {node.id}")


def _find_existing_run(
    db: Session,
    *,
    workflow_id: int,
    trigger_source: str,
    trigger_ref: str | None,
) -> WorkflowRun | None:
    if not trigger_ref:
        return None
    return (
        db.query(WorkflowRun)
        .filter(
            WorkflowRun.workflow_id == workflow_id,
            WorkflowRun.trigger_source == trigger_source,
            WorkflowRun.trigger_ref == trigger_ref,
        )
        .order_by(WorkflowRun.id.desc())
        .first()
    )


async def run_compiled_workflow(
    db: Session,
    *,
    definition: WorkflowDefinition,
    version: WorkflowVersion,
    compiled: CompiledWorkflow,
    input_payload: Mapping[str, Any],
    trigger_source: str,
    trigger_ref: str | None = None,
    actor: str = "system",
    trace_id: str | None = None,
    adapters: Optional[Mapping[str, WorkflowAdapter]] = None,
    start_node_id: str | None = None,
    initial_context: Optional[Mapping[str, Any]] = None,
    force_new_run: bool = False,
) -> WorkflowRuntimeResult:
    final_trace_id = trace_id or str(input_payload.get("trace_id") or uuid.uuid4())
    if not force_new_run:
        existing = _find_existing_run(
            db,
            workflow_id=definition.id,
            trigger_source=trigger_source,
            trigger_ref=trigger_ref,
        )
        if existing is not None:
            return WorkflowRuntimeResult(
                run_id=existing.id,
                workflow_id=existing.workflow_id,
                workflow_version_id=existing.workflow_version_id,
                run_state=existing.run_state,
                trace_id=existing.trace_id,
                reused_existing=True,
                context=_json_loads(existing.context_json),
            )

    context = _build_runtime_context(
        input_payload=input_payload,
        trace_id=final_trace_id,
        workflow_key=compiled.workflow_key,
        workflow_version=compiled.version,
        trigger_source=trigger_source,
        trigger_ref=trigger_ref,
        initial_context=initial_context,
    )
    workflow_run = WorkflowRun(
        workflow_id=definition.id,
        workflow_version_id=version.id,
        run_state=WorkflowRunState.QUEUED.value,
        trigger_source=trigger_source,
        trigger_ref=trigger_ref,
        input_payload=_json_dumps(input_payload),
        context_json=_json_dumps(context),
        trace_id=final_trace_id,
        created_at=_utc_now(),
        updated_at=_utc_now(),
    )
    db.add(workflow_run)
    db.commit()
    db.refresh(workflow_run)

    current_node_id = start_node_id or compiled.start_node_id
    if current_node_id not in compiled.nodes:
        raise WorkflowRuntimeError(f"invalid start node: {current_node_id}")
    _update_run(db, workflow_run, state=WorkflowRunState.RUNNING.value, context=context)
    try:
        while current_node_id is not None:
            node = compiled.nodes[current_node_id]
            result = await _execute_node(
                db,
                workflow_run=workflow_run,
                workflow_id=definition.id,
                workflow_version_id=version.id,
                node=node,
                actor=actor,
                trace_id=final_trace_id,
                context=context,
                adapters=adapters,
            )
            _merge_context(context, node.id, result.output)
            if result.state == WorkflowRunState.MANUAL_REQUIRED.value:
                _update_run(db, workflow_run, state=WorkflowRunState.MANUAL_REQUIRED.value, context=context, ended=True)
                return WorkflowRuntimeResult(
                    run_id=workflow_run.id,
                    workflow_id=definition.id,
                    workflow_version_id=version.id,
                    run_state=workflow_run.run_state,
                    trace_id=final_trace_id,
                    context=dict(context),
                )

            next_node_id = _select_next_node(node, context)
            if next_node_id is None:
                _update_run(db, workflow_run, state=WorkflowRunState.SUCCESS.value, context=context, ended=True)
                return WorkflowRuntimeResult(
                    run_id=workflow_run.id,
                    workflow_id=definition.id,
                    workflow_version_id=version.id,
                    run_state=workflow_run.run_state,
                    trace_id=final_trace_id,
                    context=dict(context),
                )
            current_node_id = next_node_id
    except WorkflowRuntimeError as exc:
        context["last_error"] = str(exc)
        _update_run(db, workflow_run, state=WorkflowRunState.FAILED.value, context=context, ended=True)
        return WorkflowRuntimeResult(
            run_id=workflow_run.id,
            workflow_id=definition.id,
            workflow_version_id=version.id,
            run_state=workflow_run.run_state,
            trace_id=final_trace_id,
            context=dict(context),
        )


async def replay_workflow_run(
    db: Session,
    *,
    run_id: int,
    mode: str = "full",
    overrides: Optional[Mapping[str, Any]] = None,
    actor: str = "system",
    trace_id: str | None = None,
    adapters: Optional[Mapping[str, WorkflowAdapter]] = None,
) -> WorkflowReplayResult:
    source_run, definition, version, compiled = _load_workflow_run_bundle(db, run_id=run_id)
    source_input = _json_loads(source_run.input_payload)
    merged_input = dict(source_input)
    merged_input.update(dict(overrides or {}))
    replay_suffix = uuid.uuid4().hex[:8]
    resumed_from_node_id: str | None = None
    initial_context: Optional[Mapping[str, Any]] = None
    trigger_ref_prefix = "replay"
    if mode == "resume_from_failure":
        steps = _load_step_runs(db, run_id=run_id)
        resume_step = _resolve_resume_step(steps)
        if resume_step is None:
            raise WorkflowRuntimeError(f"workflow run {run_id} has no failed step to resume")
        resumed_from_node_id = resume_step.node_id
        initial_context = dict(_json_loads(source_run.context_json))
        initial_context["replay_of_run_id"] = run_id
        initial_context["replay_mode"] = mode
        initial_context["resume_from_node_id"] = resumed_from_node_id
        trigger_ref_prefix = "resume"
    else:
        mode = "full"

    replay_run = await run_compiled_workflow(
        db,
        definition=definition,
        version=version,
        compiled=compiled,
        input_payload=merged_input,
        trigger_source="workflow_replay",
        trigger_ref=f"{trigger_ref_prefix}:{run_id}:{replay_suffix}",
        actor=actor,
        trace_id=trace_id,
        adapters=adapters,
        start_node_id=resumed_from_node_id,
        initial_context=initial_context,
        force_new_run=True,
    )
    debug_report = build_workflow_debug_report(
        db,
        run_id=run_id,
        mode=mode,
        overrides=overrides,
        resumed_from_node_id=resumed_from_node_id,
        replay_run=replay_run,
    )
    return WorkflowReplayResult(
        source_run_id=source_run.id,
        source_run_state=source_run.run_state,
        mode=mode,
        resumed_from_node_id=resumed_from_node_id,
        replay_run=replay_run,
        workflow_key=definition.workflow_key,
        workflow_version=version.version,
        debug_report=debug_report,
    )


async def run_published_workflow(
    db: Session,
    *,
    workflow_key: str,
    input_payload: Mapping[str, Any],
    trigger_source: str,
    trigger_ref: str | None = None,
    actor: str = "system",
    trace_id: str | None = None,
    adapters: Optional[Mapping[str, WorkflowAdapter]] = None,
) -> WorkflowRuntimeResult:
    definition, version, dsl = load_published_workflow(db, workflow_key)
    compiled = compile_workflow(dsl)
    return await run_compiled_workflow(
        db,
        definition=definition,
        version=version,
        compiled=compiled,
        input_payload=input_payload,
        trigger_source=trigger_source,
        trigger_ref=trigger_ref,
        actor=actor,
        trace_id=trace_id,
        adapters=adapters,
    )
