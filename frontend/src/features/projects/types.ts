export interface Project {
  id: string;
  name: string;
  slug: string;
  environment: string;
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
