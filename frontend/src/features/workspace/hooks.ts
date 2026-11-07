import { useQuery } from "@tanstack/react-query";
import { fetchCurrentWorkspaceApi } from "./api";
import { useAuth } from "@/features/auth/auth-context";

export function useCurrentWorkspace() {
  const { isReady } = useAuth();

  return useQuery({
    queryKey: ["workspace", "current"],
    queryFn: fetchCurrentWorkspaceApi,
    staleTime: 1000 * 60 * 10, // 10 minutes — workspace name rarely changes
    // Do not fire until the bootstrap refresh has settled so we always have
    // a valid access token (or know the session is gone) before fetching.
    enabled: isReady,
  });
}
