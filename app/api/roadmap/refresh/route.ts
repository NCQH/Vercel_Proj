import { NextResponse } from "next/server";
import { backendHeaders, getBackendApiBase } from "../../../../lib/backend-api";
import { getRequiredSessionUserId } from "../../../../lib/session-user";

export const dynamic = "force-dynamic";

export async function POST() {
  try {
    const userId = await getRequiredSessionUserId();
    if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const response = await fetch(`${getBackendApiBase()}/api/roadmap/refresh`, {
      method: "POST",
      headers: backendHeaders(),
      body: JSON.stringify({ user_id: userId }),
      cache: "no-store",
    });

    const text = await response.text();
    return new NextResponse(text, {
      status: response.status,
      headers: { "Content-Type": response.headers.get("Content-Type") || "application/json" },
    });
  } catch (error) {
    console.error("Roadmap refresh proxy failed", error);
    return NextResponse.json({ error: "Failed to refresh roadmap" }, { status: 500 });
  }
}
