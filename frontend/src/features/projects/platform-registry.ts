export interface SnippetStep {
  title: string;
  description?: string;
  code: string;
  language: "bash" | "python";
}

export interface PlatformConfig {
  value: string;
  label: string;
  subtitle: string;
  badge?: string;
  installCommand: string;
  steps: SnippetStep[];
}

export const PLATFORM_REGISTRY: Record<string, PlatformConfig> = {
  fastapi: {
    value: "fastapi",
    label: "FastAPI",
    subtitle: "Python · ASGI",
    badge: "Supported",
    installCommand: "pip install faultline-python[fastapi]",
    steps: [
      {
        title: "1. Install the Faultline SDK",
        description: "Install the SDK with FastAPI and ASGI framework instrumentation.",
        code: "pip install faultline-python[fastapi]",
        language: "bash",
      },
      {
        title: "2. Initialize SDK and attach middleware",
        description: "Configure your DSN and attach FaultlineFastAPIMiddleware to capture unhandled exceptions.",
        code: `from fastapi import FastAPI
import faultline
from faultline.integrations.fastapi import FaultlineFastAPIMiddleware

faultline.init(
    dsn="{{dsn}}",
    environment="production",
    traces_sample_rate=1.0,
)

app = FastAPI()
app.add_middleware(FaultlineFastAPIMiddleware)`,
        language: "python",
      },
      {
        title: "3. Verify connection with a test error",
        description: "Add a test route to verify real-time ingestion.",
        code: `@app.get("/debug-faultline")
async def trigger_error():
    division_by_zero = 1 / 0
    return {"status": "ok"}`,
        language: "python",
      },
    ],
  },
  python: {
    value: "python",
    label: "Python",
    subtitle: "Standard Python",
    badge: "Supported",
    installCommand: "pip install faultline-python",
    steps: [
      {
        title: "1. Install the Faultline SDK",
        description: "Install the core Python package via pip.",
        code: "pip install faultline-python",
        language: "bash",
      },
      {
        title: "2. Initialize SDK",
        description: "Initialize the Faultline client in your application entrypoint.",
        code: `import faultline

faultline.init(
    dsn="{{dsn}}",
    environment="production",
    traces_sample_rate=1.0,
)`,
        language: "python",
      },
      {
        title: "3. Capture exceptions",
        description: "Capture exceptions manually or unhandled tracebacks.",
        code: `try:
    1 / 0
except Exception as e:
    faultline.capture_exception(e)
finally:
    faultline.flush()`,
        language: "python",
      },
    ],
  },
};

export const DEFAULT_PLATFORM = PLATFORM_REGISTRY.fastapi;

export function getPlatformConfig(platform?: string | null): PlatformConfig {
  if (!platform) return PLATFORM_REGISTRY.python;
  const normalized = platform.toLowerCase().trim();
  return PLATFORM_REGISTRY[normalized] || PLATFORM_REGISTRY.python;
}

export function interpolateSnippets(steps: SnippetStep[], dsn: string): SnippetStep[] {
  return steps.map((step) => ({
    ...step,
    code: step.code.replace(/\{\{dsn\}\}/g, dsn || "YOUR_FAULTLINE_DSN"),
  }));
}
