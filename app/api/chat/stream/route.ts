import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "../../auth/[...nextauth]/route";
import { backendHeaders, getBackendApiBase } from "../../../../lib/backend-api";

export const dynamic = "force-dynamic";

type ChatStreamPayload = {
  message?: string;
  session_id?: string;
  preferred_sources?: string[];
};

async function getSessionUserId() {
  const session = await getServerSession(authOptions);
  const user = session?.user as { id?: string; email?: string; name?: string } | undefined;
  return user?.id || user?.email || user?.name || "";
}

export async function POST(request: Request) {
  try {
    const userId = await getSessionUserId();
    if (!userId) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = (await request.json()) as ChatStreamPayload;
    const response = await fetch(`${getBackendApiBase()}/api/chat/stream`, {
      method: "POST",
      headers: backendHeaders(),
      body: JSON.stringify({
        ...body,
        user_id: userId,
      }),
      cache: "no-store",
    });

    if (!response.body) {
      const text = await response.text().catch(() => "");
      return new NextResponse(text || "Chat stream failed", { status: response.status });
    }

    return new NextResponse(response.body, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("Content-Type") || "text/plain; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (error) {
    console.error("Chat stream proxy failed", error);
    return NextResponse.json({ error: "Chat stream failed" }, { status: 500 });
  }
}
