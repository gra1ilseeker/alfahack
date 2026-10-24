import { create } from "zustand";
import { persist } from "zustand/middleware";
import { defaultApiBase, type ApiConfig, type MetricItem, type ProfileResponse } from "@/lib/api";

type SessionInput = {
  token: string;
  email: string;
  password?: string;
};

type CabinetState = {
  token: string | null;
  email: string | null;
  password: string | null;
  profile: ProfileResponse | null;
  metrics: MetricItem[] | null;
  setSession: (session: SessionInput) => void;
  setProfile: (profile: ProfileResponse) => void;
  setMetrics: (metrics: MetricItem[]) => void;
  reset: () => void;
};

export const useCabinet = create<CabinetState>()(
  persist(
    (set) => ({
      token: null,
      email: null,
      password: null,
      profile: null,
      metrics: null,
      setSession: ({ token, email, password }) =>
        set((state) => ({
          token,
          email,
          password: password ?? state.password,
        })),
      setProfile: (profile) => set({ profile }),
      setMetrics: (metrics) => set({ metrics }),
      reset: () => set({ token: null, email: null, password: null, profile: null, metrics: null }),
    }),
    {
      name: "vektor-cabinet",
      partialize: (state) => ({
        token: state.token,
        email: state.email,
        profile: state.profile,
        metrics: state.metrics,
      }),
    },
  ),
);

export function useApiConfig(): ApiConfig {
  const token = useCabinet((state) => state.token);
  return { base: defaultApiBase(), token };
}
