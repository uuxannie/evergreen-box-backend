路由 A (POST /upload_log)： 专给 ESP8266 用，用来向数据库存日志。
路由 B (POST /set_state)： 专给前端用，用来修改后端的“信箱”状态。
路由 C (GET /current_state)： 专给 ESP8266 轮询用，每隔 5 秒来读一次“信箱”。
