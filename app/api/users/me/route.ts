import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "../../auth/[...nextauth]/route";
import { getUserProfile } from "../../../../lib/user-profile";

export async function GET() {
  try {
    const session = await getServerSession(authOptions);
    const user = session?.user as { id?: string } | undefined;

    if (!user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const profile = await getUserProfile(user.id);
    return NextResponse.json({ ok: true, profile, onboarded: Boolean(profile?.onboarded) });
  } catch (error) {
    return NextResponse.json(
      { ok: false, error: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}
