import { NextResponse } from "next/server";
import { backendHeaders, getBackendApiBase } from "../../../../../lib/backend-api";
import { getRequiredSessionUserId } from "../../../../../lib/session-user";

export const dynamic = "force-dynamic";

export async function PATCH(request: Request, context: { params: Promise<{ itemId: string }> }) {
  try {
    const userId = await getRequiredSessionUserId();
    if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const { itemId } = await context.params;
    const body = await request.json();

    const response = await fetch(`${getBackendApiBase()}/api/roadmap/items/${encodeURIComponent(itemId)}`, {
      method: "PATCH",
      headers: backendHeaders(),
      body: JSON.stringify({ ...body, user_id: userId }),
      cache: "no-store",
    });

    const text = await response.text();
    return new NextResponse(text, {
      status: response.status,
      headers: { "Content-Type": response.headers.get("Content-Type") || "application/json" },
    });
  } catch (error) {
    console.error("Roadmap item proxy failed", error);
    return NextResponse.json({ error: "Failed to update roadmap item" }, { status: 500 });
  }
}
