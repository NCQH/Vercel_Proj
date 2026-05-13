/**
 * Centralized API Client for AI Teaching Assistant
 * Handles authentication headers, error management, and typed requests.
 */

export interface ApiResponse<T> {
  ok: boolean;
  data?: T;
  error?: string;
  status: number;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

const internalAuthHeaders = (): Record<string, string> => ({});

export type UserRole = "student" | "lecturer" | "public";
export type RoadmapPriority = "high" | "medium" | "low";
export type RoadmapStatus = "todo" | "doing" | "done";
export type MembershipStatus = "pending" | "approved" | "rejected";

export interface ChatHistoryItem {
  role?: "user" | "assistant" | string;
  content?: string;
  sources?: string[];
  created_at?: string;
  session_id?: string;
}

export interface ChatSessionItem {
  session_id: string;
  title?: string;
  updated_at?: string;
  created_at?: string;
  last_message?: string;
  last_role?: string;
  last_created_at?: string;
}

export interface RoadmapItem {
  id: string;
  topic: string;
  description: string;
  priority: RoadmapPriority;
  eta_minutes: number;
  progress: number;
  status: RoadmapStatus;
  sources: string[];
  actions: string[];
}

export interface ClassSummary {
  id?: string;
  name?: string;
  code?: string;
  description?: string;
  is_active?: boolean;
  lecturer_id?: string;
  created_at?: string;
}

export interface ClassMembership {
  membership_id?: string;
  id?: string;
  status?: MembershipStatus;
  requested_at?: string;
  approved_at?: string;
  class?: ClassSummary;
  class_id?: string;
  student_id?: string;
  full_name?: string;
  student_email?: string;
}

export interface ClassFile {
  file_id: string;
  class_id?: string;
  class_name?: string;
  original_filename: string;
  size_bytes?: number;
  uploaded_at?: string;
}

export interface UploadItem {
  file_id: string;
  filename?: string;
  original_filename?: string;
  path?: string;
  stored_path?: string;
  size_bytes?: number;
  uploaded_at?: string;
}

export interface UploadResponse {
  ok?: boolean;
  file_id?: string;
  filename: string;
  size: number;
  path?: string;
}

async function request<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  for (const [key, value] of Object.entries(internalAuthHeaders())) {
    headers.set(key, value);
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorText = await response.text();
    let errorMessage = `API Request failed with status ${response.status}`;
    try {
      const errorJson = JSON.parse(errorText);
      errorMessage = errorJson.detail || errorJson.error || errorMessage;
    } catch (e) {
      // Not JSON
    }
    throw new ApiError(errorMessage, response.status);
  }

  return response.json() as Promise<T>;
}

async function formRequest<T>(url: string, formData: FormData): Promise<T> {
  const headers = new Headers();
  for (const [key, value] of Object.entries(internalAuthHeaders())) {
    headers.set(key, value);
  }

  const response = await fetch(url, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    let errorMessage = `API Request failed with status ${response.status}`;
    try {
      const errorJson = JSON.parse(errorText);
      errorMessage = errorJson.detail || errorJson.error || errorMessage;
    } catch (e) {
      // Not JSON
    }
    throw new ApiError(errorMessage, response.status);
  }

  return response.json() as Promise<T>;
}

export const apiClient = {
  // Chat
  chat: {
    send: (payload: { message: string; session_id: string; preferred_sources?: string[] }) =>
      request<{ reply: string; sources: string[] }>("/api/chat", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    
    getHistory: (sessionId: string, limit = 30) =>
      request<{ items: ChatHistoryItem[] }>(`/api/chat/history?session_id=${encodeURIComponent(sessionId)}&limit=${limit}`),
    
    getSessions: (limit = 20) =>
      request<{ items: ChatSessionItem[] }>(`/api/chat/sessions?limit=${limit}`),
    
    getSources: () =>
      request<{ items: string[] }>("/api/chat/sources"),
  },

  // Roadmap
  roadmap: {
    get: () =>
      request<{ items: RoadmapItem[]; next_action?: RoadmapItem | null }>("/api/roadmap"),
    
    refresh: () =>
      request<{ items: RoadmapItem[]; next_action?: RoadmapItem | null }>("/api/roadmap/refresh", {
        method: "POST",
      }),
    
    updateItem: (itemId: string, payload: { status: RoadmapStatus; progress?: number }) =>
      request<{ ok: boolean; item_id?: string; status?: RoadmapStatus; progress?: number }>(`/api/roadmap/items/${itemId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
  },

  // Classes & Files
  classes: {
    list: (role: UserRole = "student") =>
      request<{ items: ClassMembership[] | ClassSummary[] }>(`/api/classes?role=${role}`),
    
    create: (name: string, description: string) => {
      const formData = new FormData();
      formData.append("name", name);
      formData.append("description", description);
      return formRequest<{ ok: boolean; item: ClassSummary }>("/api/classes", formData);
    },

    join: (code: string) => {
      const formData = new FormData();
      formData.append("code", code);
      return formRequest<{ ok: boolean; item: ClassMembership }>("/api/classes/join", formData);
    },

    listFiles: (classId: string) =>
      request<{ items: ClassFile[] }>(`/api/class-files?class_id=${encodeURIComponent(classId)}`),

    listPendingRequests: (classId: string) =>
      request<{ items: ClassMembership[] }>(`/api/classes/pending?class_id=${encodeURIComponent(classId)}`),

    listMembers: (classId: string) =>
      request<{ items: ClassMembership[] }>(`/api/classes/members?class_id=${encodeURIComponent(classId)}`),

    approveRequest: (membershipId: string, approve: boolean) => {
      const formData = new FormData();
      formData.append("approve", String(approve));
      return formRequest<{ ok: boolean; item: ClassMembership }>(`/api/classes/members/${membershipId}/approve`, formData);
    },

    deleteClassFile: (fileId: string) =>
      request<{ ok: boolean }>(`/api/classes/files/${encodeURIComponent(fileId)}`, {
        method: "DELETE",
      }),

    listApprovedFiles: () =>
      request<{ items: ClassFile[]; cached?: boolean }>("/api/classes/files/user"),

    listPublic: () =>
      request<{ items: ClassSummary[] }>("/api/classes/public"),

    uploadFile: (classId: string, file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("class_id", classId);
      return formRequest<{ ok: boolean; item: ClassFile }>("/api/class-files/upload", formData);
    },
  },

  // Uploads
  uploads: {
    list: () =>
      request<{ items: UploadItem[] }>("/api/uploads"),
    
    upload: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return formRequest<UploadResponse>("/api/upload", formData);
    },

    delete: (fileId: string) =>
      request<{ ok: boolean }>(`/api/uploads/${fileId}`, {
        method: "DELETE",
      }),
  },
};
