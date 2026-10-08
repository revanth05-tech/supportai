import { apiFetch, getApiErrorMessage } from "./api";

export type Tone = "Friendly" | "Professional" | "Concise";
export type BubblePosition = "BottomRight" | "BottomLeft";
export type LlmProvider = "OpenRouter" | "OpenAI" | "Anthropic" | "Other";

export interface HandoffPosture {
  onExplicitRequest: boolean;
  onNoGrounding: boolean;
  onConsecutiveUnresolved: boolean;
  consecutiveUnresolvedThreshold: number;
}
export interface AgentConfig {
  agentName: string;
  greeting: string;
  tone: Tone;
  extraInstructions: string | null;
  themeColor: string;
  bubblePosition: BubblePosition;
  handoff: HandoffPosture;
}
export interface AgentSettings {
  config: AgentConfig;
  siteKey: string;
  allowedOrigins: string[];
  embedSnippet: string;
}
export interface LlmCredential {
  configured: boolean;
  provider: LlmProvider | null;
  baseUrl: string | null;
  maskedKey: string | null;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    throw new Error(await getApiErrorMessage(res, `Request failed (${res.status})`));
  }
  return res.json();
}

type AgentResponse = {
  business_name: string;
  tone: string;
  instructions: string;
  welcome_message: string;
  allowed_origins: string[];
  site_key: string;
  embed_snippet: string;
};

type LlmCredentialResponse = {
  configured: boolean;
  provider: LlmProvider | "";
  base_url: string | null;
};

type SiteKeyResponse = {
  site_key: string;
  embed_snippet: string;
};

function asTone(value: string): Tone {
  const normalized = value.toLowerCase();
  if (normalized === "professional") return "Professional";
  if (normalized === "concise") return "Concise";
  return "Friendly";
}

function agentFromApi(data: AgentResponse): AgentSettings {
  return {
    config: {
      // The FastAPI model stores the business/agent label in business_name.
      agentName: data.business_name,
      greeting: data.welcome_message,
      tone: asTone(data.tone),
      extraInstructions: data.instructions || null,
      themeColor: "#4f46e5",
      bubblePosition: "BottomRight",
      handoff: {
        onExplicitRequest: true,
        onNoGrounding: true,
        onConsecutiveUnresolved: false,
        consecutiveUnresolvedThreshold: 3,
      },
    },
    siteKey: data.site_key,
    allowedOrigins: data.allowed_origins,
    embedSnippet: data.embed_snippet,
  };
}

function credentialFromApi(data: LlmCredentialResponse): LlmCredential {
  return {
    configured: data.configured,
    provider: data.provider || null,
    baseUrl: data.base_url,
    // The backend deliberately never returns credential material or a mask.
    maskedKey: null,
  };
}

export const getAgent = async () =>
  agentFromApi(await apiFetch("/api/agent").then(json<AgentResponse>));

export const updateAgent = async (config: AgentConfig, allowedOrigins: string[]) =>
  agentFromApi(await apiFetch("/api/agent", {
    method: "PUT",
    body: JSON.stringify({
      business_name: config.agentName,
      tone: config.tone.toLowerCase(),
      instructions: config.extraInstructions ?? "",
      welcome_message: config.greeting,
      allowed_origins: allowedOrigins,
    }),
  }).then(json<AgentResponse>));

export const rotateSiteKey = async () => {
  const data = await
  apiFetch("/api/agent/rotate-site-key", { method: "POST" }).then(
    json<SiteKeyResponse>,
  );
  return { siteKey: data.site_key, embedSnippet: data.embed_snippet };
};

export const getLlmCredential = async () =>
  credentialFromApi(await apiFetch("/api/agent/llm").then(json<LlmCredentialResponse>));

export const upsertLlmCredential = (
  provider: LlmProvider,
  baseUrl: string | null,
  apiKey: string,
) =>
  apiFetch("/api/agent/llm", {
    method: "PUT",
    body: JSON.stringify({ provider, base_url: baseUrl, api_key: apiKey }),
  }).then(json<LlmCredentialResponse>).then(credentialFromApi);

export const deleteLlmCredential = () =>
  apiFetch("/api/agent/llm", { method: "DELETE" });
