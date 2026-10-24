import type { ErrorComponentProps } from "@tanstack/react-router";

export function AppErrorComponent({ error }: ErrorComponentProps) {
  const message =
    error instanceof Error && error.message ? error.message : "Что-то сломалось. Обновите страницу.";
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-3 bg-[#14080a] px-6 text-center text-[#f8ecec]">
      <h1 className="text-lg font-semibold">Не получилось открыть кабинет</h1>
      <p className="max-w-md text-sm break-words text-[#b89494]">{message}</p>
    </main>
  );
}
