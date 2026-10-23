import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Dashboard } from "@/components/dashboard";
import { Onboarding } from "@/components/onboarding";
import { Shell } from "@/components/shell";
import { useCabinet } from "@/lib/store";

export const Route = createFileRoute("/")({ component: Home });

function Home() {
  const token = useCabinet((state) => state.token);
  const profile = useCabinet((state) => state.profile);
  const metrics = useCabinet((state) => state.metrics);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const unsub = useCabinet.persist.onFinishHydration(() => setReady(true));
    if (useCabinet.persist.hasHydrated()) setReady(true);
    return unsub;
  }, []);

  const cabinetReady = Boolean(token && profile && metrics?.length);

  return (
    <Shell>
      {!ready ? (
        <p className="text-sm text-muted">Открываем кабинет…</p>
      ) : cabinetReady ? (
        <Dashboard />
      ) : (
        <Onboarding />
      )}
    </Shell>
  );
}
