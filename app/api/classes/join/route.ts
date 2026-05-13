import { NextResponse } from "next/server";
import { backendHeaders, getBackendApiBase } from "../../../../lib/backend-api";
import { getRequiredSessionUserId } from "../../../../lib/session-user";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const userId = await getRequiredSessionUserId();
    if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const incoming = await request.formData();
    const code = String(incoming.get("code") || incoming.get("class_code") || "");
    const outgoing = new FormData();
    outgoing.append("user_id", userId);
    outgoing.append("code", code);
    outgoing.append("class_code", code);

    const response = await fetch(`${getBackendApiBase()}/api/classes/join`, {
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
    console.error("Class join proxy failed", error);
    return NextResponse.json({ error: "Failed to join class" }, { status: 500 });
  }
}
