import { Landing } from "@/components/landing/Landing";
import { PageView } from "@/components/page/PageView";
import { PICKER_LOOKS } from "@/lib/schema";
import { SAMPLE_PAGE, SAMPLE_USERNAME } from "@/lib/sample";

export default function HomePage() {
  const cards = PICKER_LOOKS.map((look) => (
    <div key={look}>
      <PageView
        username={SAMPLE_USERNAME}
        page={{ ...SAMPLE_PAGE, theme: { ...SAMPLE_PAGE.theme, look } }}
      />
    </div>
  ));
  return <Landing cards={cards} />;
}
