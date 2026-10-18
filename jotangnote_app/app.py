from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_cors import CORS
import redis
import json
import pika
import threading

app = Flask(__name__)
CORS(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:080720zsY_@127.0.0.1:3306/note_app"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# RabbitMQ 配置
RABBITMQ_HOST = "localhost"
NOTE_QUEUE = "note_operations"


def get_rabbitmq_channel():
    """获取一个可用的 RabbitMQ channel，失败返回 None, None"""
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST)
        )
        channel = connection.channel()
        channel.queue_declare(queue=NOTE_QUEUE)
        return channel, connection
    except Exception as e:
        print(f"RabbitMQ 连接失败: {e}")
        return None, None


def publish_note_message(message: dict) -> bool:
    """发送笔记消息到 RabbitMQ，成功返回 True"""
    channel, connection = get_rabbitmq_channel()
    if not channel:
        return False

    try:
        channel.basic_publish(
            exchange="",
            routing_key=NOTE_QUEUE,
            body=json.dumps(message),
        )
        return True
    except Exception as e:
        print(f"RabbitMQ 发送失败: {e}")
        return False
    finally:
        try:
            connection.close()
        except Exception:
            pass


# Redis 配置
redis_client = redis.Redis(host="127.0.0.1", port=6379, db=0)

# 模型定义
class Note(db.Model):
    __tablename__ = "notes"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)


# 1. 用户注册接口 
@app.route("/api/v1/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"code": 400, "msg": "用户名和密码不能为空"}), 400

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({"code": 409, "msg": "用户名已存在"}), 409

    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"code": 201, "msg": "注册成功，快去登录吧！"}), 201


# 2. 用户登录接口
@app.route("/api/v1/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = User.query.filter_by(username=username).first()

    if not user or user.password != password:
        return jsonify({"code": 401, "msg": "用户名或密码错误"}), 401

    return jsonify(
        {
            "code": 200,
            "msg": "登录成功",
            "data": {"user_id": user.id, "username": user.username},
        }
    )


# 3. 创建笔记（异步）
@app.route('/api/v1/notes', methods=['GET'])
def get_notes():
    # 获取前端传过来的 user_id
    user_id = request.args.get('user_id')
    notes = Note.query.filter_by(author_id=user_id).all() 
    
    result = []
    for note in notes:
        result.append({
            'id': note.id,
            'title': note.title,
            'content': note.content,
            'author_id': note.author_id
        })
        
    return jsonify({'notes': result}), 200

@app.route("/api/v1/notes", methods=["POST"])
def create_note():
    data = request.get_json()
    user_id = data.get("user_id")

    if not user_id or not data.get("title") or not data.get("content"):
        return jsonify({"code": 400, "msg": "缺少必要参数"}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"code": 404, "msg": "用户不存在"}), 404

    message = {
        "action": "create",
        "data": {
            "title": data["title"],
            "content": data["content"],
            "author_id": user_id,
        },
    }

    if publish_note_message(message):
        return jsonify({"code": 200, "msg": "请求已接收，正在后台异步创建笔记..."})

    # 降级：RabbitMQ 不可用时同步写入
    note = Note(
        title=data["title"],
        content=data["content"],
        author_id=user_id,
    )
    db.session.add(note)
    db.session.commit()
    return jsonify({"code": 201, "msg": "RabbitMQ异常，已同步创建", "data": {"id": note.id}}), 201


# 4. 获取笔记（带缓存 & 权限校验）
@app.route("/api/v1/notes/<int:note_id>", methods=["GET"])
def get_note(note_id):
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"code": 400, "msg": "请提供 user_id"}), 400

    redis_key = f"note_{note_id}"
    cached_data = redis_client.get(redis_key)

    if cached_data:
        return jsonify(
            {
                "code": 200,
                "msg": "success (缓存命中)",
                "data": json.loads(cached_data),
            }
        )

    note = db.session.get(Note, note_id)
    if not note:
        return jsonify({"code": 404, "msg": "笔记不存在"}), 404

    if note.author_id != int(user_id):
        return jsonify({"code": 403, "msg": "无权查看此笔记"}), 403

    note_data = {
        "id": note.id,
        "title": note.title,
        "content": note.content,
    }

    redis_client.setex(redis_key, 3600, json.dumps(note_data))

    return jsonify({"code": 200, "msg": "success (数据库查询)", "data": note_data})


# 5. 更新笔记（异步）
@app.route("/api/v1/notes/<int:note_id>", methods=["PUT"])
def update_note(note_id):
    data = request.get_json()
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"code": 400, "msg": "请提供 user_id"}), 400

    note = db.session.get(Note, note_id)
    if not note:
        return jsonify({"code": 404, "msg": "笔记不存在"}), 404

    if note.author_id != int(user_id):
        return jsonify({"code": 403, "msg": "无权修改此笔记"}), 403

    message = {
        "action": "update",
        "data": {
            "id": note_id,
            "title": data.get("title"),
            "content": data.get("content"),
            "author_id": int(user_id),
        },
    }

    if publish_note_message(message):
        return jsonify({"code": 200, "msg": "更新请求已接收，正在后台异步处理..."})

    # 降级同步更新
    if "title" in data:
        note.title = data["title"]
    if "content" in data:
        note.content = data["content"]
    db.session.commit()
    return jsonify({"code": 200, "msg": "RabbitMQ异常，已同步更新"})


# 6. 删除笔记（异步）
@app.route("/api/v1/notes/<int:note_id>", methods=["DELETE"])
def delete_note(note_id):
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"code": 400, "msg": "请提供 user_id"}), 400

    note = db.session.get(Note, note_id)
    if not note:
        return jsonify({"code": 404, "msg": "笔记不存在"}), 404

    if note.author_id != int(user_id):
        return jsonify({"code": 403, "msg": "无权删除此笔记"}), 403

    message = {
        "action": "delete",
        "data": {
            "id": note_id,
            "author_id": int(user_id),
        },
    }

    if publish_note_message(message):
        return jsonify({"code": 200, "msg": "删除请求已接收，正在后台异步处理..."})

    # 降级同步删除
    db.session.delete(note)
    db.session.commit()
    return jsonify({"code": 200, "msg": "RabbitMQ异常，已同步删除"})


# 消费者回调 
def callback(ch, method, properties, body):
    message = json.loads(body)
    action = message.get("action")
    data = message.get("data")

    print(f"[消费者] 收到消息: {message}")

    with app.app_context():
        try:
            if action == "create":
                new_note = Note(
                    title=data["title"],
                    content=data["content"],
                    author_id=data["author_id"],
                )
                db.session.add(new_note)
                db.session.commit()
                print(f"[消费者] 笔记创建成功, ID: {new_note.id}")

            elif action == "update":
                note = db.session.get(Note, data["id"])
                if not note:
                    print("[消费者] 更新失败：笔记不存在")
                    return

                if note.author_id != data["author_id"]:
                    print("[消费者] 更新失败：无权修改")
                    return

                if "title" in data and data["title"] is not None:
                    note.title = data["title"]
                if "content" in data and data["content"] is not None:
                    note.content = data["content"]

                db.session.commit()
                print(f"[消费者] 笔记更新成功, ID: {note.id}")

            elif action == "delete":
                note = db.session.get(Note, data["id"])
                if not note:
                    print("[消费者] 删除失败：笔记不存在")
                    return

                if note.author_id != data["author_id"]:
                    print("[消费者] 删除失败：无权删除")
                    return

                db.session.delete(note)
                db.session.commit()
                print(f"[消费者] 笔记删除成功, ID: {data['id']}")

        except Exception as e:
            db.session.rollback()
            print(f"[消费者] 操作失败: {e}")


def start_consumer():
    try:
        consumer_connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST)
        )
        consumer_channel = consumer_connection.channel()
        consumer_channel.queue_declare(queue=NOTE_QUEUE)
        consumer_channel.basic_consume(
            queue=NOTE_QUEUE,
            on_message_callback=callback,
            auto_ack=True,
        )
        print("[*] 消费者线程已启动，正在等待消息...")
        consumer_channel.start_consuming()
    except Exception as e:
        print(f"消费者线程无法连接 RabbitMQ: {e}")


# 启动入口
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    t = threading.Thread(target=start_consumer, daemon=True)
    t.start()
    app.run(debug=True)