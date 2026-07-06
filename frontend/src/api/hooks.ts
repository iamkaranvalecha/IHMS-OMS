import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchCatalog, fetchSession, placeCheckout, placeOrder } from "./client";
import type { CartItem, ObservabilityIds } from "./types";

export const queryKeys = {
  catalog: ["catalog"] as const,
  session: (id: string) => ["session", id] as const,
};

export function useCatalog(options?: { refetchInterval?: number | false }) {
  return useQuery({
    queryKey: queryKeys.catalog,
    queryFn: async () => fetchCatalog(),
    refetchInterval: options?.refetchInterval ?? false,
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
      return state === "FULFILL_PENDING" ? 2000 : false;
    },
  });
}

export function useCheckoutMutations(onObservability?: (ids: ObservabilityIds) => void) {
  const queryClient = useQueryClient();

  const track = (observability: ObservabilityIds) => {
    onObservability?.(observability);
  };

  const placeOrderMutation = useMutation({
    mutationFn: async (payload: {
      cart: CartItem[];
      customerName?: string;
      idempotencyKey: string;
      sessionId?: string;
    }) => {
      const items = payload.cart.map((line) => ({ sku: line.sku, quantity: line.quantity }));
      if (payload.sessionId) {
        const result = await placeOrder(
          payload.sessionId,
          { items, customerName: payload.customerName },
          payload.idempotencyKey,
        );
        track(result.observability);
        return result;
      }
      const result = await placeCheckout(
        { items, customerName: payload.customerName },
        payload.idempotencyKey,
      );
      track(result.observability);
      return result;
    },
    onSuccess: (result) => {
      queryClient.setQueryData(queryKeys.session(result.data.sessionId), result);
      void queryClient.invalidateQueries({ queryKey: queryKeys.catalog });
    },
  });

  return { placeOrder: placeOrderMutation };
}
