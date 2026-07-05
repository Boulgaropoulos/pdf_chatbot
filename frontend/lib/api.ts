const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type Status = "queued" | "processing" | "ready" | "failed";

export type Workspace = {
  id: string;
  name: string;
  created_at: string;
};

export type Job = {
  id: string;
  document_id: string;
  status: Status;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type DocumentItem = {
  id: string;
  workspace_id: string;
  filename: string;
  status: Status;
  uploaded_at: string;
  job: Job | null;
};

export type ChatResponse = {
  answer: string;
  citations: Array<{
    filename: string;
    page: number;
  }>;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export function listWorkspaces(): Promise<Workspace[]> {
  return request<Workspace[]>("/workspaces");
}

export function createWorkspace(name: string): Promise<Workspace> {
  return request<Workspace>("/workspaces", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name }),
  });
}

export async function deleteWorkspace(workspaceId: string): Promise<void> {
  await request<void>(`/workspaces/${workspaceId}`, { method: "DELETE" });
}

export function listDocuments(workspaceId: string): Promise<DocumentItem[]> {
  return request<DocumentItem[]>(`/workspaces/${workspaceId}/documents`);
}

export function uploadDocuments(workspaceId: string, files: FileList): Promise<{ documents: DocumentItem[] }> {
  const formData = new FormData();
  Array.from(files).forEach((file) => formData.append("files", file));

  return request<{ documents: DocumentItem[] }>(`/workspaces/${workspaceId}/documents`, {
    method: "POST",
    body: formData,
  });
}

export function askQuestion(workspaceId: string, question: string): Promise<ChatResponse> {
  return request<ChatResponse>(`/workspaces/${workspaceId}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });
}
