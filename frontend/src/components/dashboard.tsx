import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import {
  createEvent,
  getDashboard,
  listProducts,
  rankProducts,
  readRanking,
  readSummary,
  rub,
  type ProductResponse,
  type RankRow,
} from "@/lib/api";
import { useApiConfig, useCabinet } from "@/lib/store";

export function Dashboard() {
  const config = useApiConfig();
  const profile = useCabinet((state) => state.profile);
  const metrics = useCabinet((state) => state.metrics) ?? [];
  const [summary, setSummary] = useState("");
  const [index, setIndex] = useState<number | null>(null);
  const [products, setProducts] = useState<ProductResponse[]>([]);
  const [rows, setRows] = useState<RankRow[] | null>(null);
  const [error, setError] = useState("");
  const [chartOn, setChartOn] = useState(false);

  useEffect(() => {
    setChartOn(true);
  }, []);

  useEffect(() => {
    if (!profile) return;
    let cancelled = false;
    void (async () => {
      try {
        const dashboard = await getDashboard(config, profile.id);
        let catalog: ProductResponse[] = [];
        try {
          catalog = await listProducts(config);
        } catch {
          catalog = [];
        }
        let rankedRows: RankRow[] | null = null;
        if (catalog.length) {
          try {
            const ranked = await rankProducts(config, {
              profile_id: profile.id,
              products: catalog.map((item) => item.id),
            });
            rankedRows = readRanking(ranked.result);
          } catch {
            rankedRows = null;
          }
        }
        void createEvent(config, { profile_id: profile.id, event_type: "dashboard_view" }).catch(() => undefined);
        if (cancelled) return;
        setSummary(readSummary(dashboard.summary));
        setIndex(dashboard.stability_index);
        setProducts(catalog);
        setRows(rankedRows);
      } catch (reason) {
        if (!cancelled) setError(reason instanceof Error ? reason.message : "Дашборд не загрузился");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [config.base, config.token, profile]);

  if (!profile) return null;

  const ordered = rows
    ? [
        ...rows.flatMap((row) => {
          const product = products.find((item) => item.id === row.productId);
          return product ? [{ product, row }] : [];
        }),
        ...products
          .filter((product) => !rows.some((row) => row.productId === product.id))
          .map((product) => ({ product, row: null as RankRow | null })),
      ]
    : products.map((product) => ({ product, row: null as RankRow | null }));

  const tone =
    index == null
      ? "Считаем"
      : index >= 0 && index <= 100
        ? index >= 70
          ? "Устойчивый"
          : index >= 45
            ? "Рабочий"
            : "Хрупкий"
        : index > 0
          ? "Положительный поток"
          : "Хрупкий";
  const flow = metrics.reduce((sum, item) => sum + item.cash_flow, 0) / (metrics.length || 1);
  const revenue = metrics.reduce((sum, item) => sum + item.revenue, 0) / (metrics.length || 1);

  return (
    <div className="space-y-5">
      <section className="glass grid gap-6 rounded-lg p-5 lg:grid-cols-[1.15fr_0.85fr]">
        <div>
          <p className="text-sm text-muted">
            Профиль {profile.id}
            {profile.industry ? ` · ${profile.industry}` : ""}
          </p>
          <div className="mt-3 flex items-end gap-4">
            <p className="num text-4xl font-medium leading-none text-primary sm:text-6xl">
              {index == null ? "—" : Math.abs(index) > 100 ? rub(index) : String(Math.round(index))}
            </p>
            <div>
              <p className="text-lg font-semibold">{tone} профиль</p>
              <p className="text-sm text-muted">индекс устойчивости</p>
            </div>
          </div>
          <p className="mt-4 max-w-xl text-base leading-relaxed">{error || summary || "Считаем кабинет…"}</p>
        </div>
        <dl className="grid grid-cols-2 gap-3">
          <Metric label="Полоса выручки" value={profile.revenue_band || "—"} />
          <Metric label="Цель" value={profile.goals || "—"} />
          <Metric label="Сотрудники" value={profile.employees == null ? "—" : String(profile.employees)} />
          <Metric label="Средний поток" value={metrics.length ? rub(flow) : "—"} />
        </dl>
      </section>

      {metrics.length ? (
        <section className="glass rounded-lg p-5">
          <div className="mb-3 flex items-baseline justify-between gap-3">
            <h2 className="text-lg font-semibold">Загруженные метрики</h2>
            <p className="text-xs text-muted">средняя выручка {rub(revenue)}</p>
          </div>
          <div className="h-56">
            {chartOn ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={metrics}>
                  <CartesianGrid stroke="var(--color-border)" vertical={false} />
                  <XAxis dataKey="period" stroke="var(--color-muted)" fontSize={12} tickLine={false} />
                  <YAxis
                    stroke="var(--color-muted)"
                    fontSize={12}
                    tickLine={false}
                    width={48}
                    tickFormatter={(value: number) => `${Math.round(value / 1000)}к`}
                  />
                  <Tooltip
                    formatter={(value) => rub(Number(value ?? 0))}
                    contentStyle={{
                      background: "var(--color-surface)",
                      border: "1px solid var(--color-border)",
                      borderRadius: 12,
                      color: "var(--color-fg)",
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="revenue"
                    name="Выручка"
                    stroke="var(--color-primary)"
                    fill="var(--color-primary)"
                    fillOpacity={0.18}
                    strokeWidth={2}
                  />
                  <Area
                    type="monotone"
                    dataKey="expenses"
                    name="Расходы"
                    stroke="var(--color-accent)"
                    fill="var(--color-accent)"
                    fillOpacity={0.08}
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : null}
          </div>
        </section>
      ) : null}

      <section>
        <div className="mb-3">
          <h2 className="text-lg font-semibold">Продукты</h2>
          <p className="text-sm text-muted">Порядок — насколько продукт подходит вашему профилю.</p>
        </div>
        {ordered.length ? (
          <ul className="grid gap-3">
            {ordered.map(({ product, row }, position) => (
            <li key={product.id}>
              <Link
                to="/product/$id"
                params={{ id: String(product.id) }}
                className="glass grid gap-4 rounded-lg p-4 sm:grid-cols-[auto_1fr_auto] sm:items-center"
              >
                <span className="num text-sm text-muted">{String(position + 1).padStart(2, "0")}</span>
                <div>
                  <div className="flex flex-wrap items-baseline gap-2">
                    <h3 className="text-lg font-semibold">{product.name}</h3>
                    {product.type ? <span className="text-xs text-muted">{product.type}</span> : null}
                  </div>
                  <p className="mt-1 text-sm text-muted">{row?.note || "Без пояснения от ранжирования"}</p>
                </div>
                <div className="sm:text-right">
                  <p className="num text-3xl text-primary">{row?.score ?? "—"}</p>
                  <p className="text-xs text-muted">скор</p>
                  <p className="num mt-2 text-sm">
                    {product.min_limit != null || product.max_limit != null
                      ? `${product.min_limit != null ? rub(product.min_limit) : "—"} – ${product.max_limit != null ? rub(product.max_limit) : "—"}`
                      : "лимит не задан"}
                  </p>
                </div>
              </Link>
            </li>
          ))}
          </ul>
        ) : (
          <p className="text-sm text-muted">В каталоге пока нет продуктов — ранжировать нечего.</p>
        )}
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-bg/40 p-3">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="num mt-1 text-lg">{value}</dd>
    </div>
  );
}
