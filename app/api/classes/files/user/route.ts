import { NextResponse } from "next/server";
import { backendHeaders, getBackendApiBase } from "../../../../../lib/backend-api";
import { getRequiredSessionUserId } from "../../../../../lib/session-user";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const userId = await getRequiredSessionUserId();
    if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const backendUrl = new URL(`${getBackendApiBase()}/api/classes/files/user`);
    backendUrl.searchParams.set("user_id", userId);

    const response = await fetch(backendUrl, { headers: backendHeaders(), cache: "no-store" });
    const text = await response.text();
    return new NextResponse(text, {
      status: response.status,
      headers: { "Content-Type": response.headers.get("Content-Type") || "application/json" },
    });
  } catch (error) {
    console.error("User class files proxy failed", error);
    return NextResponse.json({ error: "Failed to load class files" }, { status: 500 });
  }
}
