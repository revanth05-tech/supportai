import { apiFetch, getApiErrorMessage } from "./api";

export type KnowledgeItemType =
  | "Faq"
  | "Service"
  | "Policy"
  | "BusinessProfile";

export interface FieldDescriptor {
  name: string;
  label: string;
  kind: "text" | "textarea" | string;
  required: boolean;
}
export interface KnowledgeTypeDescriptor {
  type: KnowledgeItemType;
  label: string;
  singleton: boolean;
  fields: FieldDescriptor[];
}
export interface KnowledgeItem {
  id: string;
  itemType: KnowledgeItemType;
  payload: Record<string, unknown>;
  createdAt: string;
  updatedAt: string | null;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    throw new Error(await getApiErrorMessage(res, `Request failed (${res.status})`));
  }
  return res.json();
}

type KnowledgeItemResponse = {
  id: string;
  item_type: KnowledgeItemType;
  payload: Record<string, unknown>;
  created_at: string;
  updated_at: string | null;
};

function itemFromApi(item: KnowledgeItemResponse): KnowledgeItem {
  return {
    id: item.id,
    itemType: item.item_type,
    payload: item.payload,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
  };
}

export const getTypes = () =>
  apiFetch("/api/knowledge/types").then(json<KnowledgeTypeDescriptor[]>);

export const listKnowledge = async (type?: KnowledgeItemType) => {
  const data = await apiFetch(`/api/knowledge${type ? `?type=${type}` : ""}`).then(
    json<KnowledgeItemResponse[]>,
  );
  return data.map(itemFromApi);
};

export const createKnowledge = (
  itemType: KnowledgeItemType,
  payload: Record<string, unknown>,
) =>
  apiFetch("/api/knowledge", {
    method: "POST",
    body: JSON.stringify({ item_type: itemType, payload }),
  }).then(json<KnowledgeItemResponse>).then(itemFromApi);

export const updateKnowledge = (
  id: string,
  itemType: KnowledgeItemType,
  payload: Record<string, unknown>,
) =>
  apiFetch(`/api/knowledge/${id}`, {
    method: "PUT",
    body: JSON.stringify({ item_type: itemType, payload }),
  }).then(json<KnowledgeItemResponse>).then(itemFromApi);

export const deleteKnowledge = (id: string) =>
  apiFetch(`/api/knowledge/${id}`, { method: "DELETE" });
