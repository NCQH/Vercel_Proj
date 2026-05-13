import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "../auth/[...nextauth]/route";
import { backendHeaders, getBackendApiBase } from "../../../lib/backend-api";

export const dynamic = "force-dynamic";

type ChatPayload = {
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

    const body = (await request.json()) as ChatPayload;
    const response = await fetch(`${getBackendApiBase()}/api/chat`, {
      method: "POST",
      headers: backendHeaders(),
      body: JSON.stringify({
        ...body,
        user_id: userId,
      }),
      cache: "no-store",
    });

    const text = await response.text();
    return new NextResponse(text, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("Content-Type") || "application/json",
      },
    });
  } catch (error) {
    console.error("Chat proxy failed", error);
    return NextResponse.json({ error: "Chat request failed" }, { status: 500 });
  }
}
