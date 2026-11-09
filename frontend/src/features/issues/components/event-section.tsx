"use client";

import React, { useEffect, useMemo, useCallback } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useIssueEventsList, useEventDetail } from "../hooks";
import { EventList } from "./event-list";
import { EventDetailPanel } from "./event-detail-panel";
import { getEventDetailApi } from "../api";

interface EventSectionProps {
  projectId: string;
  issueId: string;
}

export function EventSection({ projectId, issueId }: EventSectionProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();

  // Query parameter ?event=...
  const eventParam = searchParams.get("event");

  // 1. Fetch cursor-paginated events list
  const {
    data: eventsPages,
    isLoading: isListLoading,
    isError: isListError,
    error: listError,
    refetch: refetchList,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
  } = useIssueEventsList(projectId, issueId, 25);

  // Flatten all items across loaded pages
  const allEvents = useMemo(() => {
    if (!eventsPages?.pages) return [];
    return eventsPages.pages.flatMap((page) => page.items);
  }, [eventsPages]);

  // Selected event ID: fallback to eventParam, or default to first item once available
  const selectedEventId = useMemo(() => {
    if (eventParam) return eventParam;
    if (allEvents.length > 0) return allEvents[0].id;
    return null;
  }, [eventParam, allEvents]);

  // Sync to URL if eventParam is missing and we have a default first item
  useEffect(() => {
    if (!eventParam && allEvents.length > 0) {
      const defaultId = allEvents[0].id;
      const params = new URLSearchParams(searchParams.toString());
      params.set("event", defaultId);
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    }
  }, [eventParam, allEvents, pathname, router, searchParams]);

  // 2. Fetch single event detail
  const {
    data: eventDetail,
    isLoading: isDetailLoading,
    isError: isDetailError,
    error: detailError,
    refetch: refetchDetail,
  } = useEventDetail(projectId, issueId, selectedEventId);

  // Index of selected event in the currently loaded events list (0-based)
  const currentLoadedIndex = useMemo(() => {
    if (!selectedEventId || allEvents.length === 0) return -1;
    return allEvents.findIndex((e) => e.id === selectedEventId);
  }, [selectedEventId, allEvents]);

  // Update selection handler
  const handleSelectEvent = useCallback(
    (eventId: string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set("event", eventId);
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [pathname, router, searchParams]
  );

  // Prefetch adjacent events for instant navigation
  useEffect(() => {
    if (currentLoadedIndex === -1 || !projectId || !issueId) return;

    // Prefetch previous (newer)
    if (currentLoadedIndex > 0) {
      const prevId = allEvents[currentLoadedIndex - 1].id;
      queryClient.prefetchQuery({
        queryKey: ["event-detail", projectId, issueId, prevId],
        queryFn: () => getEventDetailApi(projectId, issueId, prevId),
        staleTime: 5 * 60 * 1000,
      });
    }

    // Prefetch next (older)
    if (currentLoadedIndex < allEvents.length - 1) {
      const nextId = allEvents[currentLoadedIndex + 1].id;
      queryClient.prefetchQuery({
        queryKey: ["event-detail", projectId, issueId, nextId],
        queryFn: () => getEventDetailApi(projectId, issueId, nextId),
        staleTime: 5 * 60 * 1000,
      });
    }
  }, [currentLoadedIndex, allEvents, projectId, issueId, queryClient]);

  // Navigation handlers
  // "Newer": higher in list / smaller index
  const canNavigatePrev = currentLoadedIndex > 0;
  const handleNavigatePrev = useCallback(() => {
    if (currentLoadedIndex > 0) {
      const prevEvent = allEvents[currentLoadedIndex - 1];
      handleSelectEvent(prevEvent.id);
    }
  }, [currentLoadedIndex, allEvents, handleSelectEvent]);

  // "Older": lower in list / larger index. If at the end of loaded pages, trigger fetchNextPage
  const canNavigateNext =
    currentLoadedIndex !== -1 &&
    (currentLoadedIndex < allEvents.length - 1 || Boolean(hasNextPage));

  const handleNavigateNext = useCallback(async () => {
    if (currentLoadedIndex === -1) return;

    // If within current loaded list
    if (currentLoadedIndex < allEvents.length - 1) {
      const nextEvent = allEvents[currentLoadedIndex + 1];
      handleSelectEvent(nextEvent.id);
      return;
    }

    // At edge of loaded pages, fetch next page if available
    if (hasNextPage && !isFetchingNextPage) {
      const result = await fetchNextPage();
      const lastPage = result.data?.pages[result.data.pages.length - 1];
      if (lastPage && lastPage.items.length > 0) {
        handleSelectEvent(lastPage.items[0].id);
      }
    }
  }, [
    currentLoadedIndex,
    allEvents,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
    handleSelectEvent,
  ]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      {/* Left Column: Events List (4 columns on lg) */}
      <div className="lg:col-span-4 order-2 lg:order-1">
        <EventList
          events={allEvents}
          selectedEventId={selectedEventId}
          onSelectEvent={handleSelectEvent}
          isLoading={isListLoading}
          isError={isListError}
          error={listError}
          onRetry={refetchList}
          hasNextPage={Boolean(hasNextPage)}
          isFetchingNextPage={isFetchingNextPage}
          onLoadMore={() => fetchNextPage()}
        />
      </div>

      {/* Right Column: Selected Event Detail Panel (8 columns on lg) */}
      <div className="lg:col-span-8 order-1 lg:order-2">
        <EventDetailPanel
          event={eventDetail}
          isLoading={isDetailLoading || (isListLoading && !eventParam)}
          isError={isDetailError}
          error={detailError}
          onRetry={refetchDetail}
          currentIndex={currentLoadedIndex !== -1 ? currentLoadedIndex + 1 : null}
          totalCount={allEvents.length > 0 ? allEvents.length : null}
          onNavigatePrev={handleNavigatePrev}
          onNavigateNext={handleNavigateNext}
          canNavigatePrev={canNavigatePrev}
          canNavigateNext={canNavigateNext}
          isNavigating={isFetchingNextPage}
        />
      </div>
    </div>
  );
}
