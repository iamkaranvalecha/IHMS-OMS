import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  abandonSession,
  confirmSession,
  createSession,
  fetchCatalog,
  fetchSession,
  placeHold,
} from "./client";
import type { CartItem, ObservabilityIds } from "./types";

export const queryKeys = {
  catalog: ["catalog"] as const,
  session: (id: string) => ["session", id] as const,
};

export function useCatalog() {
  return useQuery({
    queryKey: queryKeys.catalog,
    queryFn: async () => {
      const result = await fetchCatalog();
      return result;
    },
  });
}

export function useSession(sessionId: string | null, enabled = true) {
  return useQuery({
    queryKey: sessionId ? queryKeys.session(sessionId) : ["session", "none"],
    queryFn: async () => {
      if (!sessionId) {
        throw new Error("sessionId required");
      }
      return fetchSession(sessionId);
    },
    enabled: Boolean(sessionId) && enabled,
    refetchInterval: (query) => {
      const state = query.state.data?.data.state;
      return state === "HELD" ? 2000 : false;
    },
  });
}

export function useCheckoutMutations(onObservability?: (ids: ObservabilityIds) => void) {
  const queryClient = useQueryClient();

  const track = (observability: ObservabilityIds) => {
    onObservability?.(observability);
  };

  const startCheckout = useMutation({
    mutationFn: async (payload: { cart: CartItem; customerName: string }) => {
      const created = await createSession();
      track(created.observability);
      const held = await placeHold(created.data.sessionId, {
        sku: payload.cart.sku,
        quantity: payload.cart.quantity,
        customerName: payload.customerName,
      });
      track(held.observability);
      return held;
    },
    onSuccess: (result) => {
      queryClient.setQueryData(queryKeys.session(result.data.sessionId), result);
      void queryClient.invalidateQueries({ queryKey: queryKeys.catalog });
    },
  });

  const confirmCheckout = useMutation({
    mutationFn: async (payload: { sessionId: string; idempotencyKey: string }) => {
      const result = await confirmSession(payload.sessionId, payload.idempotencyKey);
      track(result.observability);
      return result;
    },
    onSuccess: (result) => {
      queryClient.setQueryData(queryKeys.session(result.data.sessionId), result);
      void queryClient.invalidateQueries({ queryKey: queryKeys.catalog });
    },
  });

  const abandonCheckout = useMutation({
    mutationFn: async (sessionId: string) => {
      const result = await abandonSession(sessionId);
      track(result.observability);
      return result;
    },
    onSuccess: (result) => {
      queryClient.setQueryData(queryKeys.session(result.data.sessionId), result);
      void queryClient.invalidateQueries({ queryKey: queryKeys.catalog });
    },
  });

  return { startCheckout, confirmCheckout, abandonCheckout };
}
