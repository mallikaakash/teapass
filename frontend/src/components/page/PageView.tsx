import type { PageDocument } from "@/lib/schema";
import { PICKER_LOOKS } from "@/lib/schema";
import { GardenLook } from "./looks/GardenLook";

export function PageView({ page, username }: { page: PageDocument; username: string }) {
  const look = (PICKER_LOOKS as readonly string[]).includes(page.theme.look) ? page.theme.look : "estate";
  const doc = look === page.theme.look ? page : { ...page, theme: { ...page.theme, look } };
  return <GardenLook page={doc} username={username} />;
}
