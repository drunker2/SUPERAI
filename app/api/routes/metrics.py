"""
Prometheus 指标端点
"""

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.utils.metrics import set_app_info

router = APIRouter(tags=["监控"])


@router.get(
    "/metrics",
    summary="Prometheus 指标",
    description="""
暴露 Prometheus 格式的监控指标数据。

## 可用指标

### 应用指标
| 指标名 | 类型 | 说明 |
|--------|------|------|
| fitness_app_info | Gauge | 应用信息 (version, environment) |
| fitness_chat_requests_total | Counter | 对话请求总数 |
| fitness_chat_latency_seconds | Histogram | 对话延迟分布 |
| fitness_llm_calls_total | Counter | LLM 调用总数 |
| fitness_llm_latency_seconds | Histogram | LLM 调用延迟 |
| fitness_llm_tokens_total | Counter | Token 使用量 |
| fitness_errors_total | Counter | 错误总数 |

### Prometheus 配置示例
```yaml
scrape_configs:
  - job_name: 'fitness-agent'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Grafana 看板
可使用 Grafana 导入 Prometheus 数据源创建监控看板。
""",
    responses={
        200: {
            "description": "Prometheus 指标",
            "content": {
                "text/plain": {
                    "example": """# HELP fitness_app_info Application information
# TYPE fitness_app_info gauge
fitness_app_info{environment="production",version="1.0.0"} 1
# HELP fitness_chat_requests_total Total chat requests
# TYPE fitness_chat_requests_total counter
fitness_chat_requests_total{intent="fitness_consult",status="success"} 100
"""
                }
            }
        },
    },
)
async def metrics():
    """
    Prometheus 指标端点

    返回 Prometheus 可以抓取的指标数据。
    用于监控系统性能、请求量、错误率等。
    """
    # 设置应用信息
    from app.config import settings
    set_app_info(version="1.0.0", environment=settings.app_env)

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
