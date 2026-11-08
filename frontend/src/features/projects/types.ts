export interface Project {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  environment: string;
  platform?: string | null;
  dsn: string;
  apiKey: string;
  createdAt: string;
  eventCount: number;
}

export interface SdkConfig {
  name: string;
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
