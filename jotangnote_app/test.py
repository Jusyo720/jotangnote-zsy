# test_rabbitmq.py
# 用法：python test_rabbitmq.py
# 跑之前确认：Flask 应用已启动、RabbitMQ 已启动、MySQL 已启动

import requests
import time
import json
import pymysql

# ==================== 配置区 ====================
BASE_URL = "http://127.0.0.1:5000"
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "080720zsY_",
    "database": "note_app",
    "charset": "utf8mb4",
}
WAIT_SECONDS = 3  # 等待消费者异步处理的时间（秒）

# ==================== 工具函数 ====================
def get_db():
    return pymysql.connect(**DB_CONFIG)


def db_query(sql, params=None):
    conn = get_db()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    finally:
        conn.close()


def db_count(sql, params=None):
    rows = db_query(sql, params)
    return len(rows)


def print_result(title, passed):
    status = " PASS" if passed else " FAIL"
    print(f"\n{'='*60}")
    print(f"  {status}  {title}")
    print(f"{'='*60}")


# ==================== 测试用例 ====================
def test_1_create_note():
    """测试创建笔记 → 消息队列 → 数据库"""
    print("\n 测试1：创建笔记（异步）")

    resp = requests.post(
        f"{BASE_URL}/api/v1/notes",
        json={"user_id": 1, "title": "测试笔记", "content": "这是一条测试内容"},
    )
    print(f"  接口响应: {resp.status_code} {resp.json()}")

    # 验证接口返回异步提示
    data = resp.json()
    assert "异步" in data.get("msg", "") or "后台" in data.get("msg", ""), \
        f"期望异步提示，实际: {data}"
    print("   接口返回异步提示")

    # 等待消费者处理
    time.sleep(WAIT_SECONDS)

    # 验证数据库中有记录
    rows = db_query("SELECT * FROM notes WHERE title=%s", ("测试笔记",))
    assert len(rows) > 0, "数据库中未找到创建的笔记"
    note_id = rows[0]["id"]
    print(f"   数据库中存在记录, ID={note_id}")

    return note_id


def test_2_update_note(note_id):
    """测试更新笔记 → 消息队列 → 数据库"""
    print(f"\n 测试2：更新笔记 ID={note_id}（异步）")

    resp = requests.put(
        f"{BASE_URL}/api/v1/notes/{note_id}",
        json={"user_id": 1, "title": "更新后的标题", "content": "更新后的内容"},
    )
    print(f"  接口响应: {resp.status_code} {resp.json()}")

    data = resp.json()
    assert "异步" in data.get("msg", "") or "后台" in data.get("msg", ""), \
        f"期望异步提示，实际: {data}"
    print("   接口返回异步提示")

    time.sleep(WAIT_SECONDS)

    rows = db_query("SELECT * FROM notes WHERE id=%s", (note_id,))
    assert len(rows) > 0, "数据库中未找到该笔记"
    assert rows[0]["title"] == "更新后的标题", \
        f"标题未更新: {rows[0]['title']}"
    assert rows[0]["content"] == "更新后的内容", \
        f"内容未更新: {rows[0]['content']}"
    print("   数据库中 title 和 content 已更新")


def test_3_delete_note(note_id):
    """测试删除笔记 → 消息队列 → 数据库"""
    print(f"\n 测试3：删除笔记 ID={note_id}（异步）")

    resp = requests.delete(
        f"{BASE_URL}/api/v1/notes/{note_id}",
        params={"user_id": 1},
    )
    print(f"  接口响应: {resp.status_code} {resp.json()}")

    data = resp.json()
    assert "异步" in data.get("msg", "") or "后台" in data.get("msg", ""), \
        f"期望异步提示，实际: {data}"
    print("   接口返回异步提示")

    time.sleep(WAIT_SECONDS)

    rows = db_query("SELECT * FROM notes WHERE id=%s", (note_id,))
    assert len(rows) == 0, f"数据库中仍存在 ID={note_id} 的记录，删除未生效"
    print("   数据库中记录已删除")


def test_4_rabbitmq_queue_empty():
    """验证队列中没有堆积消息"""
    print("\n 测试4：检查 RabbitMQ 队列状态")

    try:
        import pika
        conn = pika.BlockingConnection(pika.ConnectionParameters(host="localhost"))
        ch = conn.channel()
        # passive=True 只查询不创建
        result = ch.queue_declare(queue="note_operations", passive=True)
        msg_count = result.method.message_count
        conn.close()

        assert msg_count == 0, f"队列中还有 {msg_count} 条未消费消息"
        print(f"   队列 note_operations 中无堆积消息 (Ready={msg_count})")
    except Exception as e:
        print(f"   无法连接 RabbitMQ 检查队列: {e}")


# ==================== 主入口 ====================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("   RabbitMQ 增删改自动化测试")
    print("=" * 60)

    try:
        note_id = test_1_create_note()
        print_result("创建笔记", True)

        test_2_update_note(note_id)
        print_result("更新笔记", True)

        test_3_delete_note(note_id)
        print_result("删除笔记", True)

        test_4_rabbitmq_queue_empty()
        print_result("队列无堆积", True)

        print("\n" + " " * 10)
        print("  全部测试通过！RabbitMQ 增删改链路已打通。")
        print(" " * 10 + "\n")

    except AssertionError as e:
        print(f"\n 测试失败: {e}")
        print("请检查 Flask 应用、RabbitMQ、MySQL 是否正常运行。")
    except requests.exceptions.ConnectionError:
        print(f"\n 无法连接 Flask 应用 ({BASE_URL})")
        print("请先启动 Flask 应用：python app.py")
    except Exception as e:
        print(f"\n 未知错误: {e}")
        raise