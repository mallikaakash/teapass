import { cookies } from "next/headers";

export const SESSION_COOKIE = "teapass_uid";

export async function getSessionUserId() {
  const jar = await cookies();
  return jar.get(SESSION_COOKIE)?.value ?? null;
}
