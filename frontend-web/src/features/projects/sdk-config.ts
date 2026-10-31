export interface SdkInstruction {
  name: string;
  installCommand: string;
  initSnippet: string;
  envSnippet: string;
}

export const SUPPORTED_SDKS: Record<string, SdkInstruction> = {
  python: {
    name: "Python",
    installCommand: "pip install faultline-python",
    envSnippet: "export FAULTLINE_DSN=https://fl_pub_9a82f1b4@ingest.faultline.io/42019",
    initSnippet: `import faultline

# Initialize Faultline SDK
faultline.init(
    dsn="https://fl_pub_9a82f1b4@ingest.faultline.io/42019",
    environment="production",
    traces_sample_rate=1.0,
    send_default_pii=False,
)

# Unhandled exceptions and ASGI traces are captured automatically.`,
  },
};

export const DEFAULT_SDK = SUPPORTED_SDKS.python;

