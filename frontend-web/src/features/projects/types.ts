export type PlatformId =
  | "python"
  | "javascript"
  | "node"
  | "java"
  | "go"
  | "other";

export interface PlatformOption {
  id: PlatformId;
  name: string;
  tagline: string;
  badge?: string;
  iconName: string;
}

export interface Project {
  id: string;
  name: string;
  slug: string;
  platform: PlatformId;
  environment: string;
  dsn: string;
  apiKey: string;
  createdAt: string;
  eventCount: number;
}

export interface SdkConfig {
  platform: PlatformId;
  installCommand: string;
  initSnippet: string;
  envSnippet: string;
  dsn: string;
  apiKey: string;
}

export interface LiveStatusEvent {
  status: "waiting" | "received";
  event?: {
    id: string;
    title: string;
    timestamp: string;
    ip: string;
  };
}

