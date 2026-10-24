import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import {
  createEvent,
  listProducts,
  rankProducts,
  readRanking,
  requirementFacts,
  rub,
  type ProductResponse,
} from "@/lib/api";
import { useApiConfig, useCabinet } from "@/lib/store";

export function ProductPage({ id }: { id: string }) {
  const config = useApiConfig();
  const profile = useCabinet((state) => state.profile);
  const productId = Number(id);
  const [product, setProduct] = useState<ProductResponse | null>(null);
  const [missing, setMissing] = useState(false);
  const [score, setScore] = useState<number | null>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!profile || !Number.isFinite(productId)) return;
    let cancelled = false;
    void (async () => {
      try {
        const catalog = await listProducts(config);
        const found = catalog.find((item) => item.id === productId) ?? null;
        if (!found) {
          if (!cancelled) setMissing(true);
          return;
        }
        let scoreValue: number | null = null;
        let noteValue = "";
        try {
          const ranked = await rankProducts(config, {
            profile_id: profile.id,
            products: catalog.map((item) => item.id),
          });
          const row = readRanking(ranked.result)?.find((item) => item.productId === productId);
          scoreValue = row?.score ?? null;
          noteValue = row?.note ?? "";
        } catch {
          scoreValue = null;
        }
        void createEvent(config, {
          profile_id: profile.id,
          event_type: "product_view",
          payload: { product_id: productId },
        }).catch(() => undefined);
        if (cancelled) return;
        setProduct(found);
        setScore(scoreValue);
        setNote(noteValue);
      } catch (reason) {
        if (!cancelled) setError(reason instanceof Error ? reason.message : "Продукт не открылся");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [config.base, config.token, productId, profile]);

  async function apply() {
    if (!profile) return;
    setBusy(true);
    try {
      await createEvent(config, {
        profile_id: profile.id,
        event_type: "application_draft",
        payload: { product_id: productId },
      });
      setDraft("Интерес сохранён в этом браузере.");
    } catch (reason) {
      setDraft(reason instanceof Error ? reason.message : "Событие не ушло");
    } finally {
      setBusy(false);
    }
  }

  if (!profile) return null;
  if (missing) {
    return (
      <div className="glass rounded-lg p-6">
        <p>Такого продукта нет.</p>
        <Link to="/" className="mt-4 inline-flex min-h-11 items-center text-primary">
          К дашборду
        </Link>
      </div>
    );
  }
  if (!product) {
    return <p className="text-sm text-muted">{error || "Открываем продукт…"}</p>;
  }

  const facts = [
    { label: "Ставка", value: product.rate == null ? "—" : `${product.rate}%` },
    { label: "Тип", value: product.type || "—" },
    { label: "Лимит от", value: product.min_limit == null ? "—" : rub(product.min_limit) },
    { label: "Лимит до", value: product.max_limit == null ? "—" : rub(product.max_limit) },
    ...requirementFacts(product.requirements_json),
  ];

  return (
    <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
      <article className="glass rounded-lg p-6">
        <Link to="/" className="text-sm text-muted">
          ← К дашборду
        </Link>
        <p className="mt-4 text-sm text-primary">{product.type || "Продукт"}</p>
        <h1 className="mt-1 text-4xl font-semibold tracking-tight">{product.name}</h1>
        <dl className="mt-6 grid grid-cols-2 gap-3">
          {facts.map((fact) => (
            <div key={fact.label} className="rounded-md border border-border p-3">
              <dt className="text-xs text-muted">{fact.label}</dt>
              <dd className="mt-1 text-sm">{fact.value}</dd>
            </div>
          ))}
        </dl>
        <button
          type="button"
          disabled={busy}
          onClick={() => void apply()}
          className="mt-6 min-h-11 rounded-md bg-primary px-5 text-sm font-semibold text-primary-ink disabled:opacity-60"
        >
          {busy ? "Отправляем…" : "Отметить интерес"}
        </button>
        {draft ? <p className="mt-3 text-sm text-muted">{draft}</p> : null}
      </article>
      <aside className="glass rounded-lg p-6">
        <p className="text-sm text-muted">Насколько продукт совпал с профилем</p>
        <p className="num mt-2 text-5xl text-primary">{score ?? "—"}</p>
        <p className="mt-2 text-sm text-muted">{note || "Считаем совпадение…"}</p>
        {error ? <p className="mt-3 text-sm text-accent">{error}</p> : null}
      </aside>
    </div>
  );
}
