"""
OpenTelemetry 初始化
用于 Trace / Metric 上报
"""
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider

def init_otel(service_name="auto_test_framework"):
    """
    初始化 OpenTelemetry
    """
    tracer_provider = TracerProvider()
    trace.set_tracer_provider(tracer_provider)

    meter_provider = MeterProvider()
    metrics.set_meter_provider(meter_provider)
