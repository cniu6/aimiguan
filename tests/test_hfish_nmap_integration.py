"""HFish 和 Nmap 集成测试"""
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


def test_hfish_config_save(client, admin_token):
    """测试保存 HFish 配置"""
    response = client.post(
        "/api/v1/defense/hfish/config",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "host_port": "127.0.0.1:4433",
            "api_key": "test_api_key_12345",
            "sync_interval": 60,
            "enabled": True
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert "配置已保存" in data["message"]


def test_hfish_config_get(client, admin_token):
    """测试获取 HFish 配置"""
    # 先保存配置
    client.post(
        "/api/v1/defense/hfish/config",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "host_port": "192.168.1.100:4433",
            "api_key": "test_key",
            "sync_interval": 120,
            "enabled": True
        }
    )
    
    # 获取配置
    response = client.get(
        "/api/v1/defense/hfish/config",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["host_port"] == "192.168.1.100:4433"
    assert data["sync_interval"] == 120
    assert data["enabled"] is True


@patch('services.hfish_collector.hfish_collector.sync_once')
def test_hfish_manual_sync(mock_sync, client, admin_token):
    """测试手动触发 HFish 同步"""
    # Mock 同步结果
    mock_sync.return_value = {
        "success": True,
        "message": "同步成功",
        "count": 5
    }
    
    # 先启用 HFish
    client.post(
        "/api/v1/defense/hfish/config",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "host_port": "127.0.0.1:4433",
            "api_key": "test_key",
            "sync_interval": 60,
            "enabled": True
        }
    )
    
    # 触发同步
    response = client.post(
        "/api/v1/defense/hfish/sync",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["count"] == 5


def test_hfish_sync_disabled(client, admin_token):
    """测试 HFish 未启用时同步失败"""
    # 禁用 HFish
    client.post(
        "/api/v1/defense/hfish/config",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "host_port": "127.0.0.1:4433",
            "api_key": "test_key",
            "sync_interval": 60,
            "enabled": False
        }
    )
    
    # 尝试同步
    response = client.post(
        "/api/v1/defense/hfish/sync",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 400
    assert "未启用" in response.json()["detail"]


def test_nmap_config_save(client, admin_token):
    """测试保存 Nmap 配置"""
    response = client.post(
        "/api/v1/scan/nmap/config",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "nmap_path": "nmap",
            "ip_ranges": ["192.168.1.0/24", "10.0.0.0/24"],
            "scan_interval": 604800,
            "enabled": True
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert "配置已保存" in data["message"]


def test_nmap_config_get(client, admin_token):
    """测试获取 Nmap 配置"""
    # 先保存配置
    client.post(
        "/api/v1/scan/nmap/config",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "nmap_path": "/usr/bin/nmap",
            "ip_ranges": ["172.16.0.0/16"],
            "scan_interval": 86400,
            "enabled": True
        }
    )
    
    # 获取配置
    response = client.get(
        "/api/v1/scan/nmap/config",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nmap_path"] == "/usr/bin/nmap"
    assert "172.16.0.0/16" in data["ip_ranges"]
    assert data["scan_interval"] == 86400


@patch('services.nmap_scanner.nmap_scanner.scan_target')
def test_nmap_manual_scan(mock_scan, client, admin_token, operator_token):
    """测试手动触发 Nmap 扫描"""
    # Mock 扫描结果
    mock_scan.return_value = {
        "success": True,
        "message": "扫描完成",
        "task_id": 1,
        "hosts_count": 3
    }
    
    # 先启用 Nmap
    client.post(
        "/api/v1/scan/nmap/config",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "nmap_path": "nmap",
            "ip_ranges": ["192.168.1.0/24"],
            "scan_interval": 604800,
            "enabled": True
        }
    )
    
    # 触发扫描
    response = client.post(
        "/api/v1/scan/nmap/scan?target=192.168.1.0/24&profile=quick",
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["hosts_count"] == 3


def test_nmap_scan_invalid_profile(client, operator_token):
    """测试使用无效的扫描配置"""
    response = client.post(
        "/api/v1/scan/nmap/scan?target=192.168.1.1&profile=invalid_profile",
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    assert response.status_code == 400
    assert "无效的扫描配置" in response.json()["detail"]


def test_nmap_scan_disabled(client, admin_token, operator_token):
    """测试 Nmap 未启用时扫描失败"""
    # 禁用 Nmap
    client.post(
        "/api/v1/scan/nmap/config",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "nmap_path": "nmap",
            "ip_ranges": ["192.168.1.0/24"],
            "scan_interval": 604800,
            "enabled": False
        }
    )
    
    # 尝试扫描
    response = client.post(
        "/api/v1/scan/nmap/scan?target=192.168.1.1&profile=quick",
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    assert response.status_code == 400
    assert "未启用" in response.json()["detail"]


def test_get_win7_hosts(client, operator_token, test_db):
    """测试获取 Win7 主机列表"""
    from core.database import ScanTask, ScanFinding, Asset
    from datetime import datetime, timezone
    import uuid
    
    # 创建测试资产
    asset = Asset(
        target="192.168.1.0/24",
        target_type="CIDR",
        description="Test Network",
        created_at=datetime.now(timezone.utc)
    )
    test_db.add(asset)
    test_db.commit()
    
    # 创建测试扫描任务
    task = ScanTask(
        asset_id=asset.id,
        target="192.168.1.0/24",
        target_type="CIDR",
        tool_name="nmap",
        profile="default",
        state="COMPLETED",
        trace_id=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc)
    )
    test_db.add(task)
    test_db.commit()
    
    # 添加 Win7 主机发现
    finding1 = ScanFinding(
        scan_task_id=task.id,
        asset="192.168.1.10",
        port=445,
        service="microsoft-ds",
        os_type="Windows 7 Professional",
        os_accuracy="95",
        severity="INFO",
        trace_id=task.trace_id,
        created_at=datetime.now(timezone.utc)
    )
    finding2 = ScanFinding(
        scan_task_id=task.id,
        asset="192.168.1.20",
        port=3389,
        service="ms-wbt-server",
        os_type="Windows Server 2008 R2",
        os_accuracy="90",
        severity="INFO",
        trace_id=task.trace_id,
        created_at=datetime.now(timezone.utc)
    )
    test_db.add_all([finding1, finding2])
    test_db.commit()
    
    # 验证 operator 用户是否存在
    from core.database import User
    operator = test_db.query(User).filter(User.username == "operator").first()
    print(f"Operator user exists: {operator is not None}")
    if operator:
        print(f"Operator enabled: {operator.enabled}")
    
    # 获取 Win7 主机
    response = client.get(
        f"/api/v1/scan/tasks/{task.id}/win7-hosts",
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["count"] == 2
    assert len(data["data"]["win7_hosts"]) == 2


def test_get_win7_hosts_task_not_found(client, operator_token):
    """测试获取不存在任务的 Win7 主机"""
    response = client.get(
        "/api/v1/scan/tasks/99999/win7-hosts",
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_scheduler_lifecycle():
    """测试调度服务生命周期"""
    from services.scheduler_service import scheduler_service
    
    # 测试启动
    await scheduler_service.start()
    assert scheduler_service.running is True
    
    # 测试停止
    await scheduler_service.stop()
    assert scheduler_service.running is False


def test_hfish_config_requires_permission(client, viewer_token):
    """测试 HFish 配置需要权限"""
    response = client.post(
        "/api/v1/defense/hfish/config",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={
            "host_port": "127.0.0.1:4433",
            "api_key": "test_key",
            "sync_interval": 60,
            "enabled": True
        }
    )
    assert response.status_code == 403


def test_nmap_config_requires_admin(client, operator_token):
    """测试 Nmap 配置需要管理员权限"""
    response = client.post(
        "/api/v1/scan/nmap/config",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "nmap_path": "nmap",
            "ip_ranges": ["192.168.1.0/24"],
            "scan_interval": 604800,
            "enabled": True
        }
    )
    assert response.status_code == 403
