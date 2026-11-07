import { useQuery } from "@tanstack/react-query";
import { getOverviewDashboardDataApi } from "./api";

export function useOverviewDashboard(
  workspaceSlug: string,
  options?: { isEmpty?: boolean; shouldFail?: boolean }
) {
  return useQuery({
    queryKey: ["overview-dashboard", workspaceSlug, options],
    queryFn: () => getOverviewDashboardDataApi(workspaceSlug, options),
  });
}

