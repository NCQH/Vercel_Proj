import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "../../auth/[...nextauth]/route";
import { getUserProfileByEmail, upsertUserProfile } from "../../../../lib/user-profile";

export async function POST(request: Request) {
  try {
    const session = await getServerSession(authOptions);
    const user = session?.user as { id?: string; email?: string; image?: string } | undefined;

    if (!user?.id || !user?.email) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = (await request.json()) as { full_name?: string; class_name?: string };
    const full_name = (body.full_name || "").trim();
    const class_name = (body.class_name || "").trim();

    if (!full_name || !class_name) {
      return NextResponse.json({ error: "full_name and class_name are required" }, { status: 400 });
    }

    const existingByEmail = await getUserProfileByEmail(user.email);
    if (existingByEmail?.onboarded) {
      return NextResponse.json(
        { error: "Email này đã đăng ký. Vui lòng đăng nhập." },
        { status: 409 }
      );
    }

    const profile = await upsertUserProfile({
      id: user.id,
      email: user.email,
      full_name,
      class_name,
      image_url: user.image,
    });

    return NextResponse.json({ ok: true, profile });
  } catch (error) {
    return NextResponse.json(
      { ok: false, error: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}
