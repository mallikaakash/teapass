import { PICKER_LOOKS } from "@/lib/schema";

export function entitlements(_userId?: string) {
  return {
    plan: "open",
    removeBranding: true,
    analyticsDays: 365,
    analyticsExport: false,
    looks: [...PICKER_LOOKS],
    customDomain: false,
  };
}
