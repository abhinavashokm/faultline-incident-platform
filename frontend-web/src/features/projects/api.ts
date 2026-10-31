import { delay } from "@/lib/api-client";
import { CreateProjectFormData } from "./schemas";
import { Project, SdkConfig, LiveStatusEvent, PlatformId } from "./types";

const mockPlatformSnippets: Record<
  PlatformId,
  { install: string; init: string; env: string }
> = {
  python: {
    install: "pip install faultline-python",
    env: "export FAULTLINE_DSN=https://fl_pub_9a82f1b4@ingest.faultline.io/42019",
    init: `import faultline

# Initialize Faultline SDK
faultline.init(
    dsn="https://fl_pub_9a82f1b4@ingest.faultline.io/42019",
    environment="production",
    traces_sample_rate=1.0,
    send_default_pii=False,
)

# Unhandled exceptions and ASGI traces are captured automatically.`,
  },
  javascript: {
    install: "npm install @faultline/browser",
    env: "NEXT_PUBLIC_FAULTLINE_DSN=https://fl_pub_9a82f1b4@ingest.faultline.io/42019",
    init: `import * as Faultline from "@faultline/browser";

Faultline.init({
  dsn: "https://fl_pub_9a82f1b4@ingest.faultline.io/42019",
  environment: "production",
  integrations: [Faultline.browserTracingIntegration()],
});`,
  },
  node: {
    install: "npm install @faultline/node",
    env: "FAULTLINE_DSN=https://fl_pub_9a82f1b4@ingest.faultline.io/42019",
    init: `const Faultline = require("@faultline/node");

Faultline.init({
  dsn: "https://fl_pub_9a82f1b4@ingest.faultline.io/42019",
  environment: "production",
  tracesSampleRate: 1.0,
});`,
  },
  java: {
    install: "implementation 'io.faultline:faultline-spring-boot-starter:1.4.0'",
    env: "FAULTLINE_DSN=https://fl_pub_9a82f1b4@ingest.faultline.io/42019",
    init: `// In application.yml:
faultline:
  dsn: "https://fl_pub_9a82f1b4@ingest.faultline.io/42019"
  environment: "production"
  traces-sample-rate: 1.0`,
  },
  go: {
    install: "go get github.com/faultline/faultline-go",
    env: "FAULTLINE_DSN=https://fl_pub_9a82f1b4@ingest.faultline.io/42019",
    init: `package main

import "github.com/faultline/faultline-go"

func main() {
    faultline.Init(faultline.ClientOptions{
        Dsn:         "https://fl_pub_9a82f1b4@ingest.faultline.io/42019",
        Environment: "production",
    })
    defer faultline.Flush(2 * time.Second)
}`,
  },
  other: {
    install: "curl -sSL https://get.faultline.io/otel-exporter.sh | bash",
    env: "OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp.faultline.io:4317",
    init: `# Configure standard OpenTelemetry collector:
exporters:
  otlp/faultline:
    endpoint: "https://otlp.faultline.io:4317"
    headers:
      "x-faultline-key": "fl_sec_9a82f1b4892cfa7"`,
  },
};

export async function createProjectApi(data: CreateProjectFormData): Promise<Project> {
  await delay(600);

  return {
    id: "proj_" + Math.random().toString(36).substring(2, 10),
    name: data.name,
    slug: data.slug,
    platform: data.platform,
    environment: data.environment || "production",
    dsn: "https://fl_pub_9a82f1b4@ingest.faultline.io/42019",
    apiKey: "fl_sec_9a82f1b4892cfa7eb40",
    createdAt: new Date().toISOString(),
    eventCount: 0,
  };
}

export async function getSdkConfigApi(platform: PlatformId = "python"): Promise<SdkConfig> {
  await delay(200);
  const snippet = mockPlatformSnippets[platform] || mockPlatformSnippets.python;

  return {
    platform,
    installCommand: snippet.install,
    initSnippet: snippet.init,
    envSnippet: snippet.env,
    dsn: "https://fl_pub_9a82f1b4@ingest.faultline.io/42019",
    apiKey: "fl_sec_9a82f1b4892cfa7eb40",
  };
}

export async function checkFirstEventStatusApi(
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _projectId?: string
): Promise<LiveStatusEvent> {
  await delay(400);

  return {
    status: "waiting",
  };
}

