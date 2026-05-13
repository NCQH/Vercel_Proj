import { NextResponse } from "next/server";
import { backendHeaders, getBackendApiBase } from "../../../../../../lib/backend-api";
import { getRequiredSessionUserId } from "../../../../../../lib/session-user";

export const dynamic = "force-dynamic";

export async function POST(request: Request, context: { params: Promise<{ membershipId: string }> }) {
  try {
    const userId = await getRequiredSessionUserId();
    if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const { membershipId } = await context.params;
    const incoming = await request.formData();
    const outgoing = new FormData();
    outgoing.append("user_id", userId);
    outgoing.append("approve", String(incoming.get("approve") || "true"));

    const response = await fetch(`${getBackendApiBase()}/api/classes/members/${encodeURIComponent(membershipId)}/approve`, {
      method: "POST",
      headers: backendHeaders(""),
      body: outgoing,
      cache: "no-store",
    });

    const text = await response.text();
    return new NextResponse(text, {
      status: response.status,
      headers: { "Content-Type": response.headers.get("Content-Type") || "application/json" },
    });
  } catch (error) {
    console.error("Class member approval proxy failed", error);
    return NextResponse.json({ error: "Failed to update member status" }, { status: 500 });
  }
}
