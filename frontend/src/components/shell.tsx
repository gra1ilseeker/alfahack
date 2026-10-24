import { useRef, type ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { logout } from "@/lib/api";
import { useApiConfig, useCabinet } from "@/lib/store";

export function Shell({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const config = useApiConfig();
  const token = useCabinet((state) => state.token);
  const reset = useCabinet((state) => state.reset);

  function move(event: React.MouseEvent) {
    const node = ref.current;
    if (!node) return;
    const box = node.getBoundingClientRect();
    node.style.setProperty("--mx", String((event.clientX - box.left) / box.width - 0.5));
    node.style.setProperty("--my", String((event.clientY - box.top) / box.height - 0.5));
  }

  function signOut() {
    if (config.token) void logout(config).catch(() => undefined);
    reset();
  }

  return (
    <div ref={ref} onMouseMove={move} className="stage min-h-screen">
      <div className="parallax-layer" aria-hidden />
      <div className="relative z-10 mx-auto flex min-h-screen w-full max-w-6xl flex-col px-4 py-5 sm:px-6">
        <header className="mb-6 flex items-center justify-between gap-3">
          <Link to="/" className="flex items-center gap-3">
            <span className="grid size-10 place-items-center rounded-md bg-primary text-sm font-semibold text-primary-ink">
              В
            </span>
            <span>
              <span className="block text-base font-semibold tracking-tight">Вектор</span>
              <span className="block text-xs text-muted">Кредитный кабинет ММБ</span>
            </span>
          </Link>
          {token ? (
            <button
              type="button"
              onClick={signOut}
              className="min-h-11 rounded-md border border-border px-3 text-sm text-muted"
            >
              Выйти
            </button>
          ) : null}
        </header>
        <div className="flex-1">{children}</div>
      </div>
    </div>
  );
}
