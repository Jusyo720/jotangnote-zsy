# Redis
## Q1 
Redis**基于内存操作**，数据直接存储在内存中；同时它采用**单线程模型**（在旧版本中）或**多路复用机制**（在较新版本中）；此外，Redis支持丰富的数据结构，可以灵活组织数据。
## Q2
在MySQL中的一行数据，可以以**字符串**（String）、**哈希**（Hash）、**列表**（List）或**集合**（Set）等形式存入Redis作为缓存。最常用的是**Hash**结构，因为MySQL的一行数据本质上是**键值对的集合**，与Redis的Hash结构天然对应，便于按字段存取。
## Q3
- **连接与基础字符串操作**
````python
import redis

# 1. 建立连接
# decode_responses=True 可以让 get 出来的数据直接是 str(文本/字符串)，而不是 b'string'（字节/字节流）
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# 2. 测试连接
print("连接状态:", r.ping())  # 输出: 连接状态: True

# 3. 设置和获取键值对 (String)
r.set('username', '123456')
print(r.get('username'))  # 输出: 123456

# 4. 设置带过期时间的键,适合做缓存
r.setex('captcha', 60, 'abcd')  # 60秒后过期
print(r.ttl('captcha'))         # 查看剩余存活时间

# 5. 删除键
r.delete('username')
print(r.exists('username'))     # 输出: 0 (表示不存在)
````
- **基础数据类型操作**
1. 哈希
````python
# 设置哈希表
r.hset('user:1001', 'name', 'Alice')
r.hset('user:1001', 'age', 25)

# 获取单个字段
print(r.hget('user:1001', 'name'))  # 输出: Alice

# 获取所有字段
print(r.hgetall('user:1001'))       # 输出: {'name': 'Alice', 'age': '25'}

# 删除某个字段
r.hdel('user:1001', 'age')
````
2. 列表
````python
# 从右侧入队 (rpush)
r.rpush('my_queue', 'task1', 'task2')
# 从左侧出队 (lpop)
print(r.lpop('my_queue'))  # 输出: task1

# 获取所有元素 (0 到 -1 表示全部)
print(r.lrange('my_queue', 0, -1))  # 输出: ['task2']
````
3. 集合
````python
# 添加元素 (自动去重)
r.sadd('tags', 'python', 'web', 'python') # 重复的 python 会被忽略

# 查看集合所有元素
print(r.smembers('tags'))  # 输出: {'python', 'web'}

# 判断元素是否存在
print(r.sismember('tags', 'java'))  # 输出: False
````
