import { NextResponse } from "next/server";
import { backendHeaders, getBackendApiBase } from "../../../../lib/backend-api";
import { getRequiredSessionUserId } from "../../../../lib/session-user";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const userId = await getRequiredSessionUserId();
    if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const incomingUrl = new URL(request.url);
    const classId = incomingUrl.searchParams.get("class_id") || "";
    const backendUrl = new URL(`${getBackendApiBase()}/api/classes/pending`);
    backendUrl.searchParams.set("user_id", userId);
    backendUrl.searchParams.set("class_id", classId);

    const response = await fetch(backendUrl, { headers: backendHeaders(), cache: "no-store" });
    const text = await response.text();
    return new NextResponse(text, {
      status: response.status,
      headers: { "Content-Type": response.headers.get("Content-Type") || "application/json" },
    });
  } catch (error) {
    console.error("Pending class requests proxy failed", error);
    return NextResponse.json({ error: "Failed to load pending requests" }, { status: 500 });
  }
}
