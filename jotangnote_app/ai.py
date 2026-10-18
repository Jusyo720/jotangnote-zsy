import os
import sys
import json
import os, sys, json
import pymysql  
from flask_cors import CORS
from flask import Flask, request, jsonify
from openai import OpenAI

DB_HOST = '127.0.0.1'     
DB_PORT = 3306            
DB_USER = 'root'          
DB_PASS = '080720zsY_' 
DB_NAME = 'note_app'     

app = Flask(__name__)
CORS(app)

# 0. 读取 API Key（环境变量方式） 
api_key = os.environ.get("DEEPSEEK_API_KEY")
if not api_key:
    sys.exit("错误：未检测到环境变量 DEEPSEEK_API_KEY，请先设置后再运行。")

# 初始化 DeepSeek 客户端
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com/v1" 
)

# 1. 会话管理
chat_sessions = {}
MAX_HISTORY_SIZE = 20  # 最大历史条数，防止内存溢出

# 定义会话上下文初始化的函数
def get_history(session_id):
    if session_id not in chat_sessions:
        chat_sessions[session_id] = [
            {"role": "system", "content": "你是一个乐于助人的AI助手。"}
        ]
    return chat_sessions[session_id]

# 2. 定义 Tool (查询笔记工具)
# 1. 声明工具的 Schema，告诉 AI 它拥有什么能力
tools = [
    {
        "type": "function",
        "function": {
            "name": "query_note",
            "description": "根据笔记 ID 查询笔记的全文内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "笔记的唯一标识 ID"
                    }
                },
                "required": ["note_id"]
            }
        }
    }
]

# 2. 定义 Tool 对应的真实执行逻辑
def execute_query_note(note_id):
    """根据笔记ID真实查询数据库内容"""
    conn = None
    try:
        # 1. 建立数据库连接
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,  
            charset='utf8mb4'
        )
        
        # 2. 获取游标
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 3. 执行SQL查询（表名确认是 note）
        sql = "SELECT * FROM notes WHERE id = %s"
        cursor.execute(sql, (note_id,))
        
        # 4. 获取结果
        result = cursor.fetchone()
        
        # 5. 返回结果
        if result:
            return f"【标题】：{result.get('title', '无标题')} \n【内容】：{result.get('content', '')}"
        else:
            return f"未找到 ID 为 {note_id} 的笔记内容"
            
    except Exception as e:
        return f"查询数据库时出错：{str(e)}"
    finally:
        # 6. 关闭数据库连接
        if conn:
            conn.close()


@app.route('/chat', methods=['POST'])
def chat_with_ai():
    data = request.get_json()
    user_message = data.get('message')
    session_id = data.get('session_id', 'default_session')

    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400

    # 获取当前会话的历史记录
    current_history = get_history(session_id)

    try:
        # 3. 将用户新消息追加到历史中
        current_history.append({"role": "user", "content": user_message})

        # 4. Tool Use 核心循环 
        while True:
            # 第一次请求或后续补充请求
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=current_history,
                tools=tools,          # 传入工具描述
                tool_choice="auto",   # 让 AI 自动决定是否调用工具
                stream=False
            )

            response_message = response.choices[0].message

            # 核心：将 AI 的回复（含 tool_calls）存入会话上下文 
            current_history.append({
                "role": response_message.role,
                "content": response_message.content,
                "tool_calls": response_message.tool_calls
            })

            # 如果 AI 决定要调用工具
            if response_message.tool_calls:
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    # 执行对应的函数并获取结果
                    if function_name == "query_note":
                        function_response = execute_query_note(function_args.get("note_id"))
                    else:
                        function_response = "未找到该函数"

                    # 将函数执行结果追加到会话历史中
                    current_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": function_response
                    })
                # 带着用户消息+AI工具调用+工具返回结果，进行下一次循环，让 AI 生成最终回复
                continue
            else:
                # 没有工具调用，直接拿到最终回复，退出循环
                ai_reply = response_message.content
                break

        # 5. 会话滑动窗口维护
        if len(current_history) > MAX_HISTORY_SIZE:
            chat_sessions[session_id] = [current_history[0]] + current_history[-(MAX_HISTORY_SIZE - 1):]

        return jsonify({
            "reply": ai_reply,
            "session_id": session_id
        })

    except Exception as e:
        # 异常时清理最后追加的用户消息
        current_history.pop()
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5001)