import { apiFetch, getApiErrorMessage } from "./api";

export interface Summary {
  totalConversations: number;
  activeConversations: number;
  handedOffConversations: number;
  totalLeads: number;
  newLeads: number;
}

export interface ConversationListItem {
  id: string;
  status: string;
  startedAt: string;
  lastMessageAt: string;
}

export interface ConversationList {
  total: number;
  items: ConversationListItem[];
}

export interface ConversationMessage {
  role: string;
  content: string;
  createdAt: string;
  topSimilarity: number | null;
  wasGrounded: boolean | null;
  modelUsed: string | null;
  latencyMs: number | null;
  titles: string[] | null;
}

export interface ConversationDetail {
  id: string;
  status: string;
  originUrl: string | null;
  startedAt: string;
  lastMessageAt: string;
  messages: ConversationMessage[];
  lead: {
    id: string;
    reason: string;
    status: string;
    contactName: string | null;
    contactEmail: string | null;
  } | null;
}

export interface Lead {
  id: string;
  conversationId: string;
  reason: string;
  status: string;
  contactName: string | null;
  contactEmail: string | null;
  contactPhone: string | null;
  visitorMessage: string | null;
  stumpingQuestion: string | null;
  createdAt: string;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(await getApiErrorMessage(res, `Request failed (${res.status})`));

  return res.json();
}

type DashboardSummaryResponse = {
  total_conversations: number;
  active_conversations: number;
  handed_off_conversations: number;
  total_leads: number;
  new_leads: number;
};

type DashboardConversationResponse = {
  id: string;
  status: string;
  origin_url: string | null;
  started_at: string;
  last_message_at: string;
};

type DashboardMessageResponse = {
  role: string;
  content: string;
  created_at: string;
  top_similarity: number | null;
  was_grounded: boolean | null;
  model_used: string | null;
  latency_ms: number | null;
  matched_titles: string[] | null;
};

type DashboardConversationDetailResponse = {
  conversation: DashboardConversationResponse;
  messages: DashboardMessageResponse[];
};

type LeadResponse = {
  id: string;
  conversation_id: string;
  reason: string;
  status: string;
  contact_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  visitor_message: string | null;
  stumping_question: string | null;
  created_at: string;
};

function conversationFromApi(
  conversation: DashboardConversationResponse,
): ConversationListItem {
  return {
    id: conversation.id,
    status: conversation.status,
    startedAt: conversation.started_at,
    lastMessageAt: conversation.last_message_at,
  };
}

export const getSummary = async (): Promise<Summary> => {
  const data = await apiFetch("/api/dashboard/summary").then(
    json<DashboardSummaryResponse>,
  );
  return {
    totalConversations: data.total_conversations,
    activeConversations: data.active_conversations,
    handedOffConversations: data.handed_off_conversations,
    totalLeads: data.total_leads,
    newLeads: data.new_leads,
  };
};

export const listConversations = async (): Promise<ConversationList> => {
  const data = await apiFetch("/api/dashboard/conversations").then(
    json<DashboardConversationResponse[]>,
  );
  return { total: data.length, items: data.map(conversationFromApi) };
};

export const getConversation = async (id: string): Promise<ConversationDetail> => {
  const data = await apiFetch(`/api/dashboard/conversations/${id}`).then(
    json<DashboardConversationDetailResponse>,
  );
  return {
    id: data.conversation.id,
    status: data.conversation.status,
    originUrl: data.conversation.origin_url,
    startedAt: data.conversation.started_at,
    lastMessageAt: data.conversation.last_message_at,
    lead: null,
    messages: data.messages.map((message) => ({
      role: message.role,
      content: message.content,
      createdAt: message.created_at,
      topSimilarity: message.top_similarity,
      wasGrounded: message.was_grounded,
      modelUsed: message.model_used,
      latencyMs: message.latency_ms,
      titles: message.matched_titles,
    })),
  };
};

export const deleteConversation = (id: string) =>
  apiFetch(`/api/dashboard/conversations/${id}`, {
    method: "DELETE",
  });

export const listLeads = async (status?: string): Promise<Lead[]> => {
  const data = await apiFetch(`/api/leads${status ? `?status=${status}` : ""}`).then(
    json<LeadResponse[]>,
  );
  return data.map((lead) => ({
    id: lead.id,
    conversationId: lead.conversation_id,
    reason: lead.reason,
    status: lead.status,
    contactName: lead.contact_name,
    contactEmail: lead.contact_email,
    contactPhone: lead.contact_phone,
    visitorMessage: lead.visitor_message,
    stumpingQuestion: lead.stumping_question,
    createdAt: lead.created_at,
  }));
};

export const updateLeadStatus = (id: string, status: string) =>
  apiFetch(`/api/leads/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
