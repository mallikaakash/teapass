import { redirect } from "next/navigation";
import { SAMPLE_USERNAME } from "@/lib/sample";

export default function DemoPage() {
  redirect(`/${SAMPLE_USERNAME}`);
}
