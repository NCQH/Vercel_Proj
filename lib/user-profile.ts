export type UserProfile = {
  id: string;
  email: string;
  full_name: string;
  class_name: string;
  image_url?: string;
  onboarded: boolean;
  created_at?: string;
  updated_at?: string;
};

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseServiceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

function assertSupabaseEnv() {
  if (!supabaseUrl || !supabaseServiceRoleKey) {
    throw new Error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY");
  }
}

export async function getUserProfile(userId: string): Promise<UserProfile | null> {
  assertSupabaseEnv();

  const url = `${supabaseUrl}/rest/v1/users?id=eq.${encodeURIComponent(userId)}&select=*`;
  const response = await fetch(url, {
    headers: {
      apikey: supabaseServiceRoleKey as string,
      Authorization: `Bearer ${supabaseServiceRoleKey}`,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Failed to read user profile: ${response.status}`);
  }

  const rows = (await response.json()) as UserProfile[];
  return rows[0] ?? null;
}

export async function getUserProfileByEmail(email: string): Promise<UserProfile | null> {
  assertSupabaseEnv();

  const url = `${supabaseUrl}/rest/v1/users?email=eq.${encodeURIComponent(email)}&select=*`;
  const response = await fetch(url, {
    headers: {
      apikey: supabaseServiceRoleKey as string,
      Authorization: `Bearer ${supabaseServiceRoleKey}`,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Failed to read user by email: ${response.status}`);
  }

  const rows = (await response.json()) as UserProfile[];
  return rows[0] ?? null;
}

export async function upsertUserProfile(input: {
  id: string;
  email: string;
  full_name: string;
  class_name: string;
  image_url?: string;
}): Promise<UserProfile> {
  assertSupabaseEnv();

  const response = await fetch(`${supabaseUrl}/rest/v1/users`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      apikey: supabaseServiceRoleKey as string,
      Authorization: `Bearer ${supabaseServiceRoleKey}`,
      Prefer: "resolution=merge-duplicates,return=representation",
    },
    body: JSON.stringify([
      {
        id: input.id,
        email: input.email,
        full_name: input.full_name,
        class_name: input.class_name,
        image_url: input.image_url ?? null,
        onboarded: true,
      },
    ]),
    cache: "no-store",
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Failed to save user profile: ${response.status} ${text}`);
  }

  const rows = (await response.json()) as UserProfile[];
  return rows[0];
}
