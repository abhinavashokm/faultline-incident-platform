export interface Project {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  platform?: string | null;
  status?: string;
  created_at?: string;
  updated_at?: string;
  dsn?: string;
  environment?: string;
  apiKey?: string;
  createdAt?: string;
  eventCount?: number;
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
