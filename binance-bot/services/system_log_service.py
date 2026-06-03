import collections
import datetime

# 系統日誌儲存
system_logs = collections.deque(maxlen=100)

def add_system_log(text: str, level: str = "info"):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    system_logs.append({"time": now, "text": text, "level": level})

def get_system_logs():
    return list(system_logs)

def clear_system_logs():
    system_logs.clear()
