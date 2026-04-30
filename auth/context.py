# auth/context.py
import contextvars
from typing import Optional, Any

# 1. 定义 ContextVar，类似于 Java 的 private static ThreadLocal<User>
# default=None 表示如果没有设置，获取到的就是 None
current_user_var: contextvars.ContextVar = contextvars.ContextVar("current_user", default=None)

# 2. 封装 getter 方法 (可选，为了方便调用)
def get_current_user_global() -> Optional[Any]:
    return current_user_var.get()
