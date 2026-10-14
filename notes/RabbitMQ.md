# RabbitMQ
## Q1
- **异步处理**（Asynchronous）：若不使用MQ，代码必须按顺序执行（如插入数据库-发送邮件-发送短信-返回成功），耗时长；若使用MQ，代码只需要执行（插入数据库-发送消息到MQ-返回成功），其他操作由后端其他程序从MQ中取出来处理，缩短了所用的时间。
- **系统解耦（Decoupling）**：若不使用MQ，所有接口都从代码里直接调用，倘若有一个接口升级或者报错，则所有系统都会报错；若使用MQ，各个系统作为不同的主体来输入消息或拉取消息，互不影响。
- **流量削峰（Peak Clipping）**：若某一瞬间请求激增，不使用MQ的话，大量请求涌入MySQL数据库，造成数据库宕机；若使用MQ，那么这些请求会先进入MQ中，后端的消费者根据自己能承受的能力，慢慢从MQ中取出来处理，保护了后端数据库。
## Q2
- 生产者：发送消息
````python
import pika

# 连接本地 RabbitMQ
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host="localhost")
)
channel = connection.channel()

# 声明队列，如果不存在就创建
channel.queue_declare(queue="hello", durable=True)

# 发送消息
channel.basic_publish(
    exchange="",
    routing_key="hello",  #把消息发送到“hello”这个队列
    body="Hello RabbitMQ",
    properties=pika.BasicProperties(
        delivery_mode=2,  # 消息持久化，重启不丢
    ),
)

print("已发送消息: Hello RabbitMQ")
connection.close()
````
- 消费者：接收消息
````python
import pika

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host="localhost")
)
channel = connection.channel()

# 消费者也要声明同一个队列
channel.queue_declare(queue="hello", durable=True)

def callback(ch, method, properties, body):
    print("收到消息:", body.decode())
    # 手动确认消息已处理完成
    ch.basic_ack(delivery_tag=method.delivery_tag)

# 公平分发：一次只取一条
channel.basic_qos(prefetch_count=1)

channel.basic_consume(
    queue="hello",
    on_message_callback=callback,
    auto_ack=False,  # 关闭自动确认，使用手动 ACK
)

print("等待消息，按 Ctrl+C 退出")
channel.start_consuming()
````
- 运行顺序
````python
# 终端1：先启动消费者
python consumer.py

# 终端2：再运行生产者
python producer.py
````
