import type { QueryResponse } from "./types";
import { createDemoResponse, getDemoSourceUrl, isDemoMode } from "./demo";

function apiUrl(): string {
  const configured = window.__WIKI_CONFIG__?.apiUrl ?? import.meta.env.VITE_API_URL;
  // Empty is intentional in AWS: CloudFront proxies the API on the same origin.
  return configured?.replace(/\/$/, "") ?? "";
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly correlationId?: string,
  ) {
    super(message);
  }
}

async function authorizedFetch(path: string, token: string, init?: RequestInit): Promise<Response> {
  const response = await fetch(`${apiUrl()}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      authorization: `Bearer ${token}`,
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as {
      message?: string;
      correlation_id?: string;
    };
    const message =
      response.status === 401
        ? "Sua sessão expirou. Entre novamente."
        : (payload.message ?? "Não foi possível concluir a solicitação.");
    throw new ApiError(message, response.status, payload.correlation_id);
  }
  return response;
}

export async function askWiki(question: string, token: string): Promise<QueryResponse> {
  if (isDemoMode()) return createDemoResponse(question);

  const response = await authorizedFetch("/query", token, {
    method: "POST",
    body: JSON.stringify({ question }),
  });
  return (await response.json()) as QueryResponse;
}

export async function getSourceUrl(documentId: string, token: string): Promise<string> {
  if (isDemoMode()) {
    const sourceUrl = getDemoSourceUrl(documentId);
    if (!sourceUrl) throw new ApiError("Fonte demonstrativa não encontrada.", 404);
    return sourceUrl;
  }

  const response = await authorizedFetch(`/sources/${encodeURIComponent(documentId)}`, token);
  const payload = (await response.json()) as { url: string };
  return payload.url;
}
