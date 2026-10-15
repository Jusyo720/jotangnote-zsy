# JSON
## Q1
- **核心结构**
    - **对象**：用大括号 `{}` 包裹的键值对集合，键和值[^1]用**冒号**分隔，键值对之间用**逗号**分隔，键必须是**字符串**并用**双引号**包围。
    - **数组**：用方括号 `[]` 包裹的有序值集合，值之间用**逗号**分隔。
- **语法规则**
    - 键名必须用**双引号**，单引号或无引号都非法。
    - **不支持 undefined 和函数**。
    - 数组或对象最后一个元素后**不能有多余逗号**。
    - 标准 JSON **不支持注释**，JSON5 才支持。
    - 根节点[^2]一般是**对象**或**数组**。

## Q2
- **字典与JSON互转**
````json
import json

data = {"name": "姓名", "age": 20, "city": "城市"}

# 字典 -> JSON字符串
json_str = json.dumps(data, ensure_ascii=False, indent=2)

# JSON字符串 -> 字典
back = json.loads(json_str)

# 直接读写文件
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

with open("data.json", "r", encoding="utf-8") as f:
    loaded = json.load(f)
````
*注：带 s 的是和字符串打交道，不带 s 的是和文件对象打交道。中文想正常显示要加 `ensure_ascii=False，indent` 用来美化输出。*
- **自定义对象转JSON**
需要用`__dict__`把对象属性直接当作字典序列化。
````json
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

p = Person("Alice", 30)
print(json.dumps(p.__dict__, ensure_ascii=False))
````
- **JSON转成对象**  
用 `object_hook`  
loads 遇到每个 JSON 对象都会调用这个函数，可以把字典换成对象返回。
````json
class JSONObject:
    def __init__(self, d):
        self.__dict__ = d

data = json.loads('{"name": "n1", "price": 232.3}', object_hook=JSONObject)
print(data.name, data.price)
````

[^1]：值可以是字符串、数字、布尔值、数组、对象或 null，并且可以层层嵌套。  
[^2]：根节点是JSON数据最外层的结构。