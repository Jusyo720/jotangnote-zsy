# MySQL
## Q1
 单机下，可以承载**千万级**（1kw-5kw行）的数据；通过合理的表结构设计、硬件升级，单机也可以承载**亿级**数据。而Excel最多只能存储104万行，且卡顿。    

## Q2 
- **索引（Index）**：
    - 本质上是一种极其高效的数据结构（通常是*B+树*，一个“自动平衡的、层数极少的超级目录”）。若没有索引，则进行**全表扫描**；而有了索引后，就只需要**访问3到4次节点**，就能定位到具体的数据位置。
    - 原则：1. **不要给每个字段都加索引**，这会使所占空间变大、更新目录速度变慢；                      
          2. **只给最常被查询（Where）的字段加索引**。
        - 缺点：1. **降低增删改的速度**  
                2. **索引不总是生效**，比如在SQL语句的`WHERE`条件中对索引字段进行了**运算**或者使用了**模糊匹配**，此时数据库会放弃索引，回到全表扫描。
- **存储引擎与内存缓存**：MySQL会把最近经常访问的数据（和索引）放在**内存**里，内存的读写速度是硬盘的几十上百倍，所以大部分常用查询直接从内存返回，速度快。

## Q3
- **安装与连接数据库** 
1. 安装驱动
````python
pip install pymysql  
````
2. 编写连接逻辑
````python
import pymysql

# 1. 建立连接
conn = pymysql.connect(
    host='localhost',        # 数据库服务器地址
    user='root',             # 用户名
    password='your_password',# 密码
    database='your_db',      # 要操作的数据库名
    charset='utf8mb4'        # utf8mb4完美支持emoji等字符
)

# 2. 创建游标 (Cursor)，所有的SQL执行都通过它
cursor = conn.cursor()
````  
- **执行增删改查（CRUD）与防注入**
1. 增（Insert）
````python
sql = "INSERT INTO users (name, email) VALUES (%s, %s)"

# 执行单条插入
data = ('name1', 'email1')
cursor.execute(sql, data)

# 批量插入
data_list = [('name2', 'email2'), ('name3', 'email5')]
cursor.executemany(sql, data_list)
````
2. 查（Select）
````python
sql = "SELECT * FROM users WHERE name = %s"
# 执行查询
cursor.execute(sql, ('name1',)) 

# 获取数据
result_one = cursor.fetchone()   # 获取单条记录，返回元组 (1, 'name1', '...')
result_all = cursor.fetchall()   # 获取所有记录，返回元组套元组 ((...), (...))
````
3. 改（Update）
````python
# 更新数据
update_sql = "UPDATE users SET email = %s WHERE name = %s"
cursor.execute(update_sql, ('emailnew', 'name'))
````
4. 删（Delete）
````python
delete_sql = "DELETE FROM users WHERE name = %s"
cursor.execute(delete_sql, ('name',))
````
5. **防注入**：不要把用户输入当作SQL代码的一部分；而是把其**只当成数据值**。
````python
# ❌ 危险
username = request.form["username"]
sql = f"SELECT * FROM users WHERE username = '{username}'"
cursor.execute(sql)
````
````python
# ✅ 安全
username = request.form["username"]
sql = "SELECT * FROM users WHERE username = %s"
cursor.execute(sql, (username,))
````
- **事务提交与资源关闭**
1. **每次**执行完**增、删、改**操作后，必须显式调用`com.commit()`提交事务，如果是查询操作，则不需要提交。
2. 在`finally`块中关闭**游标和连接**，释放资源。
````python
# 放在 finally 块中
finally:
    cursor.close()  # 关闭游标
    conn.close()    # 关闭数据库连接
````