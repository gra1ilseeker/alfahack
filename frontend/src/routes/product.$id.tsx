import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { ProductPage } from "@/components/product-page";
import { Shell } from "@/components/shell";
import { useCabinet } from "@/lib/store";

export const Route = createFileRoute("/product/$id")({ component: ProductRoute });

function ProductRoute() {
  const { id } = Route.useParams();
  const profile = useCabinet((state) => state.profile);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const unsub = useCabinet.persist.onFinishHydration(() => setReady(true));
    if (useCabinet.persist.hasHydrated()) setReady(true);
    return unsub;
  }, []);

  return (
    <Shell>
      {!ready ? (
        <p className="text-sm text-muted">Открываем продукт…</p>
      ) : profile ? (
        <ProductPage id={id} />
      ) : (
        <div className="glass rounded-lg p-6">
          <p>Сначала нужен профиль.</p>
          <Link to="/" className="mt-3 inline-flex min-h-11 items-center text-primary">
            Ко входу
          </Link>
        </div>
      )}
    </Shell>
  );
}
