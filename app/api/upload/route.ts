import { NextResponse } from "next/server";
import { backendHeaders, getBackendApiBase } from "../../../lib/backend-api";
import { getRequiredSessionUserId } from "../../../lib/session-user";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const userId = await getRequiredSessionUserId();
    if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const incoming = await request.formData();
    const outgoing = new FormData();
    const file = incoming.get("file");
    if (file) outgoing.append("file", file);
    outgoing.append("user_id", userId);

    const headers = backendHeaders("");
    const response = await fetch(`${getBackendApiBase()}/api/upload`, {
      method: "POST",
      headers,
      body: outgoing,
      cache: "no-store",
    });

    const text = await response.text();
    return new NextResponse(text, {
      status: response.status,
      headers: { "Content-Type": response.headers.get("Content-Type") || "application/json" },
    });
  } catch (error) {
    console.error("Upload proxy failed", error);
    return NextResponse.json({ error: "Failed to upload file" }, { status: 500 });
  }
}
