import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "../../auth/[...nextauth]/route";
import { backendHeaders, getBackendApiBase } from "../../../../lib/backend-api";

export const dynamic = "force-dynamic";

async function getSessionUserId() {
  const session = await getServerSession(authOptions);
  const user = session?.user as { id?: string; email?: string; name?: string } | undefined;
  return user?.id || user?.email || user?.name || "";
}

export async function GET(request: Request) {
  try {
    const userId = await getSessionUserId();
    if (!userId) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const incomingUrl = new URL(request.url);
    const limit = incomingUrl.searchParams.get("limit") || "20";

    const backendUrl = new URL(`${getBackendApiBase()}/api/chat/sessions`);
    backendUrl.searchParams.set("user_id", userId);
    backendUrl.searchParams.set("limit", limit);

    const response = await fetch(backendUrl, {
      headers: backendHeaders(),
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
    console.error("Chat sessions proxy failed", error);
    return NextResponse.json({ error: "Failed to load chat sessions" }, { status: 500 });
  }
}
