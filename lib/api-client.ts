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

async function request<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
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
    send: (payload: { message: string; user_id: string; session_id: string; preferred_sources?: string[] }) =>
      request<{ reply: string; sources: string[] }>("/api/chat", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    
    getHistory: (userId: string, sessionId: string, limit = 30) =>
      request<{ items: any[] }>(`/api/chat/history?user_id=${encodeURIComponent(userId)}&session_id=${encodeURIComponent(sessionId)}&limit=${limit}`),
    
    getSessions: (userId: string, limit = 20) =>
      request<{ items: any[] }>(`/api/chat/sessions?user_id=${encodeURIComponent(userId)}&limit=${limit}`),
    
    getSources: (userId: string) =>
      request<{ items: string[] }>(`/api/chat/sources?user_id=${encodeURIComponent(userId)}`),
  },

  // Roadmap
  roadmap: {
    get: (userId: string) =>
      request<{ items: any[]; next_action?: any }>(`/api/roadmap?user_id=${encodeURIComponent(userId)}`),
    
    refresh: (userId: string) =>
      request<{ items: any[] }>("/api/roadmap/refresh", {
        method: "POST",
        body: JSON.stringify({ user_id: userId }),
      }),
    
    updateItem: (userId: string, itemId: string, payload: { status: string; progress?: number }) =>
      request<{ ok: boolean }>(`/api/roadmap/items/${itemId}`, {
        method: "PATCH",
        body: JSON.stringify({ ...payload, user_id: userId }),
      }),
  },

  // Classes & Files
  classes: {
    list: (userId: string, role: "student" | "lecturer" | "public" = "student") =>
      request<{ items: any[] }>(`/api/classes?user_id=${encodeURIComponent(userId)}&role=${role}`),
    
    create: (userId: string, name: string, description: string) => {
      const formData = new FormData();
      formData.append("user_id", userId);
      formData.append("name", name);
      formData.append("description", description);
      return fetch("/api/classes", { method: "POST", body: formData }).then(res => res.json());
    },

    join: (userId: string, code: string) => {
      const formData = new FormData();
      formData.append("user_id", userId);
      formData.append("code", code);
      return fetch("/api/classes/join", { method: "POST", body: formData }).then(res => res.json());
    },

    listFiles: (userId: string, classId: string) =>
      request<{ items: any[] }>(`/api/class-files?user_id=${encodeURIComponent(userId)}&class_id=${encodeURIComponent(classId)}`),

    listPendingRequests: (userId: string, classId: string) =>
      request<{ items: any[] }>(`/api/classes/pending?user_id=${encodeURIComponent(userId)}&class_id=${encodeURIComponent(classId)}`),

    approveRequest: (userId: string, membershipId: string, approve: boolean) => {
      const formData = new FormData();
      formData.append("user_id", userId);
      formData.append("approve", String(approve));
      return fetch(`/api/classes/members/${membershipId}/approve`, {
        method: "POST",
        body: formData,
      }).then((res) => res.json());
    },
  },

  // Uploads
  uploads: {
    list: (userId: string) =>
      request<{ items: any[] }>(`/api/uploads?user_id=${encodeURIComponent(userId)}`),
    
    delete: (userId: string, fileId: string) =>
      request<{ ok: boolean }>(`/api/uploads/${fileId}?user_id=${encodeURIComponent(userId)}`, {
        method: "DELETE",
      }),
  },
};
