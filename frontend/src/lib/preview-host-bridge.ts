export function installPreviewHostBridge(_bridge: {
  navigate: (path: string) => void;
  getRoutePaths: () => string[];
}): () => void {
  return () => undefined;
}

export function collectRoutePathsFromTree(_tree: unknown): string[] {
  return [];
}
