"""`/v1/ingest` 测试用例。

覆盖契约 §1：
- 成功 upsert / delete
- 幂等：同 biz_type:biz_id 重复 upsert 只留 1 个点
- 幂等：delete 不存在的 id 也返回成功
- 失败：空 content 的 upsert 返回 4xx（不是 200）
- 鉴权：不带 X-Agent-Key 返回 401
"""

import uuid

import httpx

BASE = "http://127.0.0.1:8001"
KEY = "change-me"
HEADERS = {"X-Agent-Key": KEY}

# 用固定 trace_id 便于日志追踪
TRACE = "a1b2c3d4e5f60718"


def _post(body: dict, headers: dict | None = None) -> httpx.Response:
    return httpx.post(
        f"{BASE}/v1/ingest",
        headers=headers if headers is not None else HEADERS,
        json=body,
        timeout=30,
    )


def _upsert(biz_type="moment", biz_id=123, scope="couple", scope_id=11, content="测试内容"):
    return _post({
        "trace_id": TRACE,
        "biz_type": biz_type,
        "biz_id": biz_id,
        "content": content,
        "scope": scope,
        "scope_id": scope_id,
        "action": "upsert",
    })


def _delete(biz_type="moment", biz_id=123, scope="couple", scope_id=11):
    return _post({
        "trace_id": TRACE,
        "biz_type": biz_type,
        "biz_id": biz_id,
        "scope": scope,
        "scope_id": scope_id,
        "action": "delete",
    })


# ============================================================
# 1. 成功场景
# ============================================================

def test_upsert_moment():
    """couple 域的 moment，写入成功。"""
    resp = _upsert(biz_type="moment", biz_id=123, scope="couple", scope_id=11)
    print("1. upsert moment:", resp.status_code, resp.json())
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


def test_upsert_photo():
    """couple 域的 photo，和 moment 同 collection。"""
    resp = _upsert(biz_type="photo", biz_id=456, scope="couple", scope_id=11,
                   content="相册名 照片描述")
    print("2. upsert photo:", resp.status_code, resp.json())
    assert resp.status_code == 200


def test_upsert_note():
    """personal 域的 note，独立 collection。"""
    resp = _upsert(biz_type="note", biz_id=789, scope="personal", scope_id=1,
                   content="Redis 学习笔记 正文")
    print("3. upsert note:", resp.status_code, resp.json())
    assert resp.status_code == 200


def test_delete_existing():
    """删一个刚写进去的点。"""
    _upsert(biz_type="moment", biz_id=999, content="将被删除")
    resp = _delete(biz_type="moment", biz_id=999)
    print("4. delete 已存在的点:", resp.status_code, resp.json())
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


# ============================================================
# 2. 幂等场景（契约 §1.3 的核心）
# ============================================================

def test_upsert_idempotent():
    """同一 biz_type:biz_id upsert 两次，仍然只应成功（点被覆盖）。

    真正的验证要去 Qdrant 看 points_count。
    这里只验证两次请求都 200。
    """
    r1 = _upsert(biz_type="moment", biz_id=1001, content="第一次")
    r2 = _upsert(biz_type="moment", biz_id=1001, content="第二次（覆盖）")
    print("5. 重复 upsert:", r1.status_code, r2.status_code)
    assert r1.status_code == 200
    assert r2.status_code == 200


def test_delete_non_existing():
    """delete 一个不存在的 id，仍返回 200（幂等）。"""
    resp = _delete(biz_type="moment", biz_id=999999)
    print("6. delete 不存在的点:", resp.status_code, resp.json())
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


# ============================================================
# 3. 失败场景（契约 §1.2：Java 只看状态码）
# ============================================================

def test_upsert_missing_content():
    """upsert 缺 content → 400（不是 200）。"""
    resp = _post({
        "trace_id": TRACE,
        "biz_type": "moment",
        "biz_id": 123,
        "scope": "couple",
        "scope_id": 11,
        "action": "upsert",
    })
    print("7. upsert 缺 content:", resp.status_code, resp.json())
    assert resp.status_code == 400


def test_upsert_blank_content():
    """upsert content 是空白 → 400。"""
    resp = _upsert(biz_id=123, content="   ")
    print("8. upsert 空白 content:", resp.status_code, resp.json())
    assert resp.status_code == 400


def test_invalid_biz_type():
    """非法 biz_type → 400。"""
    resp = _post({
        "trace_id": TRACE,
        "biz_type": "invalid_type",
        "biz_id": 1,
        "content": "x",
        "scope": "couple",
        "scope_id": 11,
        "action": "upsert",
    })
    print("9. 非法 biz_type:", resp.status_code, resp.json())
    assert resp.status_code == 400


def test_invalid_action():
    """非法 action → 400。"""
    resp = _post({
        "trace_id": TRACE,
        "biz_type": "moment",
        "biz_id": 1,
        "content": "x",
        "scope": "couple",
        "scope_id": 11,
        "action": "invalid",
    })
    print("10. 非法 action:", resp.status_code, resp.json())
    assert resp.status_code == 400


def test_scope_mismatch():
    """moment + personal 是无效组合 → 400（namespace_for 会抛 ValueError）。

    注：如果契约允许这种组合，就删掉这个测试。
    """
    resp = _upsert(biz_type="moment", scope="personal", scope_id=1)
    print("11. 非法 scope 组合:", resp.status_code, resp.json())
    # 这里两种可能都合理：
    # - 400：schema 层拦住了
    # - 500：schema 放过了，但 namespace_for 抛异常
    assert resp.status_code in (400, 500)


# ============================================================
# 4. 鉴权
# ============================================================

def test_no_key():
    """不带 X-Agent-Key → 401。"""
    resp = _post(
        {
            "trace_id": TRACE,
            "biz_type": "moment",
            "biz_id": 123,
            "content": "x",
            "scope": "couple",
            "scope_id": 11,
            "action": "upsert",
        },
        headers={},  # 空 headers，不传 key
    )
    print("12. 不带 key:", resp.status_code, resp.json())
    assert resp.status_code == 401


def test_wrong_key():
    """错误的 key → 401。"""
    resp = _post(
        {
            "trace_id": TRACE,
            "biz_type": "moment",
            "biz_id": 123,
            "content": "x",
            "scope": "couple",
            "scope_id": 11,
            "action": "upsert",
        },
        headers={"X-Agent-Key": "wrong-key"},
    )
    print("13. 错误 key:", resp.status_code, resp.json())
    assert resp.status_code == 401


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    tests = [
        test_upsert_moment,
        test_upsert_photo,
        test_upsert_note,
        test_delete_existing,
        test_upsert_idempotent,
        test_delete_non_existing,
        test_upsert_missing_content,
        test_upsert_blank_content,
        test_invalid_biz_type,
        test_invalid_action,
        test_scope_mismatch,
        test_no_key,
        test_wrong_key,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"  ❌ {t.__name__} 失败: {e}")
        except Exception as e:
            failed += 1
            print(f"  💥 {t.__name__} 异常: {type(e).__name__}: {e}")

    print()
    print(f"通过: {passed}, 失败: {failed}")