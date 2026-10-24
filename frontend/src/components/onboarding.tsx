import { useState } from "react";
import { createProfile, getMe, login, register, uploadMetrics, type MetricItem, type ProfileResponse } from "@/lib/api";
import { useApiConfig, useCabinet } from "@/lib/store";
import { cn } from "@/lib/cn";

const INDUSTRIES = [
  "Кофейня и общепит",
  "Интернет-магазин",
  "Розничная точка",
  "Услуги",
  "Небольшое производство",
  "Опт",
];

const GOALS = ["Кассовый разрыв", "Оборотные средства", "Оборудование", "Рост и маркетинг", "Контракт"];

const BANDS = ["до 1 млн ₽", "1–5 млн ₽", "5–20 млн ₽", "больше 20 млн ₽"];

function series(revenue: number, expenses: number, online: number): MetricItem[] {
  const labels = ["май", "июн", "июл", "авг", "сен", "окт"];
  return labels.map((period, index) => {
    const monthRevenue = Math.round(revenue * (1 + (index - 2.5) * 0.015));
    return {
      period,
      revenue: monthRevenue,
      expenses: Math.round(expenses),
      cash_flow: monthRevenue - Math.round(expenses),
      online_share: online,
    };
  });
}

function parseCsv(text: string): MetricItem[] {
  const lines = text
    .trim()
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (!lines.length) return [];
  const header = /revenue|оборот|выруч|period|месяц/i.test(lines[0] ?? "");
  const rows = header ? lines.slice(1) : lines;
  const points: MetricItem[] = [];
  rows.forEach((line) => {
    const parts = line.split(/[;,\t]/).map((part) => part.trim());
    if (parts.length < 3) return;
    const revenue = Number(parts[1]?.replace(/\s/g, "").replace(",", "."));
    const expenses = Number(parts[2]?.replace(/\s/g, "").replace(",", "."));
    if (!Number.isFinite(revenue) || !Number.isFinite(expenses)) return;
    const flowRaw = parts[3] != null ? Number(parts[3].replace(/\s/g, "").replace(",", ".")) : revenue - expenses;
    const onlineRaw = parts[4] != null ? Number(parts[4].replace(/\s/g, "").replace(",", ".")) : 0;
    points.push({
      period: parts[0] || `М${points.length + 1}`,
      revenue,
      expenses,
      cash_flow: Number.isFinite(flowRaw) ? flowRaw : revenue - expenses,
      online_share: !Number.isFinite(onlineRaw) ? 0 : onlineRaw > 1 ? onlineRaw / 100 : onlineRaw,
    });
  });
  return points;
}

export function Onboarding() {
  const token = useCabinet((state) => state.token);
  const profile = useCabinet((state) => state.profile);
  if (!token) return <AuthStep />;
  if (!profile) return <ProfileStep />;
  return <MetricsStep />;
}

function AuthStep() {
  const config = useApiConfig();
  const setSession = useCabinet((state) => state.setSession);
  const [email, setEmail] = useState("owner@example.com");
  const [password, setPassword] = useState("secret12");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(kind: "login" | "register") {
    setBusy(true);
    setError("");
    try {
      const body = { email: email.trim(), password };
      const token = kind === "login" ? await login(config, body) : await register(config, body);
      setSession({ token: token.access_token, email: body.email, password: body.password });
      try {
        const me = await getMe({ base: config.base, token: token.access_token });
        if (me.profile) {
          const profile: ProfileResponse = {
            id: me.profile.id,
            user_id: me.id,
            industry: me.profile.industry,
            revenue_band: me.profile.revenue_band,
            employees: me.profile.employees,
            goals: me.profile.goals,
          };
          useCabinet.getState().setProfile(profile);
        }
      } catch {
        // /auth/me есть в текущем бэке; старый Swagger без него не должен ломать вход.
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось войти");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid items-start gap-6 lg:grid-cols-[0.9fr_1.1fr]">
      <section className="pt-2">
        <p className="text-sm text-primary">Кредитная лаборатория</p>
        <h1 className="mt-2 max-w-md text-4xl font-semibold leading-tight tracking-tight">
          Сначала картина бизнеса, потом продукт.
        </h1>
        <p className="mt-4 max-w-md text-base leading-relaxed text-muted">
          Войдите, укажите обороты — кабинет покажет устойчивость и подберёт кредитный продукт.
        </p>
      </section>
      <form
        className="glass space-y-4 rounded-lg p-5"
        onSubmit={(event) => {
          event.preventDefault();
          void submit("login");
        }}
      >
        <label className="block text-sm">
          <span className="text-muted">Почта</span>
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="mt-1 w-full rounded-md border border-border bg-bg px-3 py-3"
          />
        </label>
        <label className="block text-sm">
          <span className="text-muted">Пароль</span>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="mt-1 w-full rounded-md border border-border bg-bg px-3 py-3"
          />
        </label>
        {error ? <p className="text-sm text-accent">{error}</p> : null}
        <div className="grid gap-2 sm:grid-cols-2">
          <button
            type="submit"
            disabled={busy}
            className="min-h-11 rounded-md bg-primary text-sm font-semibold text-primary-ink disabled:opacity-60"
          >
            Войти
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void submit("register")}
            className="min-h-11 rounded-md border border-border text-sm disabled:opacity-60"
          >
            Создать аккаунт
          </button>
        </div>
      </form>
    </div>
  );
}

function ProfileStep() {
  const config = useApiConfig();
  const email = useCabinet((state) => state.email) ?? "";
  const savedPassword = useCabinet((state) => state.password) ?? "";
  const setProfile = useCabinet((state) => state.setProfile);
  const [password, setPassword] = useState(savedPassword);
  const [industry, setIndustry] = useState(INDUSTRIES[2]);
  const [band, setBand] = useState(BANDS[1]);
  const [employees, setEmployees] = useState("4");
  const [goal, setGoal] = useState(GOALS[1]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    const staff = Number(employees.replace(/\s/g, ""));
    setBusy(true);
    setError("");
    try {
      const profile = await createProfile(config, {
        user_email: email,
        password,
        industry,
        revenue_band: band,
        employees: Number.isFinite(staff) ? staff : null,
        goals: goal,
      });
      setProfile(profile);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Профиль не создан");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      className="glass mx-auto max-w-xl space-y-5 rounded-lg p-5"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Профиль бизнеса</h1>
        <p className="mt-2 text-sm text-muted">{email}</p>
      </div>
      <label className="block text-sm">
        <span className="text-muted">Пароль</span>
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className="mt-1 w-full rounded-md border border-border bg-bg px-3 py-3"
        />
      </label>
      <label className="block text-sm">
        <span className="text-muted">Отрасль</span>
        <select
          value={industry}
          onChange={(event) => setIndustry(event.target.value)}
          className="mt-1 w-full rounded-md border border-border bg-bg px-3 py-3"
        >
          {INDUSTRIES.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
      </label>
      <label className="block text-sm">
        <span className="text-muted">Полоса выручки</span>
        <select
          value={band}
          onChange={(event) => setBand(event.target.value)}
          className="mt-1 w-full rounded-md border border-border bg-bg px-3 py-3"
        >
          {BANDS.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
      </label>
      <label className="block text-sm">
        <span className="text-muted">Сотрудники</span>
        <input
          inputMode="numeric"
          value={employees}
          onChange={(event) => setEmployees(event.target.value)}
          className="num mt-1 w-full rounded-md border border-border bg-bg px-3 py-3"
        />
      </label>
      <fieldset>
        <legend className="text-sm text-muted">Цель</legend>
        <div className="mt-2 flex flex-wrap gap-2">
          {GOALS.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setGoal(item)}
              className={cn(
                "min-h-11 rounded-md border px-3 text-sm",
                goal === item ? "border-primary bg-primary text-primary-ink" : "border-border",
              )}
            >
              {item}
            </button>
          ))}
        </div>
      </fieldset>
      {error ? <p className="text-sm text-accent">{error}</p> : null}
      <button
        type="submit"
        disabled={busy}
        className="min-h-11 w-full rounded-md bg-primary text-sm font-semibold text-primary-ink disabled:opacity-60"
      >
        Создать профиль
      </button>
    </form>
  );
}

function MetricsStep() {
  const config = useApiConfig();
  const profile = useCabinet((state) => state.profile);
  const setMetrics = useCabinet((state) => state.setMetrics);
  const [revenue, setRevenue] = useState("1400000");
  const [expenses, setExpenses] = useState("1120000");
  const [online, setOnline] = useState("35");
  const [csvNote, setCsvNote] = useState("");
  const [csvMonths, setCsvMonths] = useState<MetricItem[] | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onFile(file: File | undefined) {
    if (!file) return;
    const months = parseCsv(await file.text());
    if (!months.length) {
      setCsvMonths(null);
      setCsvNote("Не разобрал файл. Нужны период, выручка, расходы.");
      return;
    }
    setCsvMonths(months);
    setCsvNote(`В файле ${months.length} периодов.`);
  }

  async function submit() {
    if (!profile) return;
    const rev = Number(revenue.replace(/\s/g, ""));
    const exp = Number(expenses.replace(/\s/g, ""));
    const share = Number(online.replace(",", ".")) / 100;
    const metrics = csvMonths?.length ? csvMonths : series(rev, exp, Number.isFinite(share) ? share : 0);
    if (!metrics.length || metrics.some((item) => item.revenue <= 0)) {
      setError("Нужна положительная выручка.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await uploadMetrics(config, profile.id, { metrics });
      setMetrics(metrics);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Метрики не ушли");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      className="glass mx-auto max-w-xl space-y-5 rounded-lg p-5"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Обороты</h1>
        <p className="mt-2 text-sm text-muted">Период, выручка, расходы, денежный поток и доля онлайн.</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <Field label="Выручка / мес" value={revenue} onChange={setRevenue} />
        <Field label="Расходы / мес" value={expenses} onChange={setExpenses} />
        <Field label="Онлайн, %" value={online} onChange={setOnline} />
      </div>
      <label className="block text-sm text-muted">
        CSV вместо средних
        <input
          type="file"
          accept=".csv,text/csv"
          onChange={(event) => void onFile(event.target.files?.[0])}
          className="mt-2 block w-full text-sm text-fg"
        />
      </label>
      {csvNote ? <p className="text-sm text-accent">{csvNote}</p> : null}
      {error ? <p className="text-sm text-accent">{error}</p> : null}
      <button
        type="submit"
        disabled={busy}
        className="min-h-11 w-full rounded-md bg-primary text-sm font-semibold text-primary-ink disabled:opacity-60"
      >
        {busy ? "Считаем…" : "Показать кабинет"}
      </button>
    </form>
  );
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block text-sm">
      <span className="text-muted">{label}</span>
      <input
        inputMode="decimal"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="num mt-1 w-full rounded-md border border-border bg-bg px-3 py-3"
      />
    </label>
  );
}
