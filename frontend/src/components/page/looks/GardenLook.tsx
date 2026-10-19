import type { PageDocument, Tile } from "@/lib/schema";
import { tileLabel } from "@/lib/tile-label";
import { LOOKS } from "@/lib/looks";
import "./garden.css";

const SIZE_CLASS: Record<string, string> = {
  s: "garden-size-s",
  w: "garden-size-w",
  t: "garden-size-t",
  l: "garden-size-l",
};

function TileCard({ tile, index }: { tile: Tile; index: number }) {
  const { title, subtitle, href } = tileLabel(tile);
  const body = (
    <>
      {tile.type === "heading" ? <h3 className="garden-heading">{title}</h3> : <strong>{title}</strong>}
      {subtitle ? <span className="garden-sub">{subtitle}</span> : null}
      {tile.type === "image" ? (
        <div className="garden-media">
          <img src={tile.src} alt="" className="garden-thumb" />
        </div>
      ) : null}
    </>
  );
  const className = `garden-tile ${SIZE_CLASS[tile.size] ?? "garden-size-s"}`;
  if (href) {
    return (
      <a key={tile.id} className={className} href={href} data-index={index}>
        {body}
      </a>
    );
  }
  return (
    <article key={tile.id} className={className} data-index={index}>
      {body}
    </article>
  );
}

export function GardenLook({ page, username }: { page: PageDocument; username: string }) {
  const look = page.theme.look;
  const label = LOOKS[look as keyof typeof LOOKS]?.label ?? "Garden";
  const layout = page.theme.layout;

  return (
    <div className="garden-root" data-look={look} data-layout={layout} data-font={page.theme.font}>
      <header className="garden-header">
        <p className="garden-kicker">{label} · @{username}</p>
        <h1>{page.profile.name}</h1>
        <p className="garden-bio">{page.profile.bio}</p>
        {page.profile.location ? <p className="garden-location">{page.profile.location}</p> : null}
      </header>
      {layout === "list" ? (
        <div className="garden-list">
          {page.tiles.map((tile, index) => (
            <TileCard key={tile.id} tile={tile} index={index} />
          ))}
        </div>
      ) : (
        <div className="garden-bento">
          {page.tiles.map((tile, index) => (
            <TileCard key={tile.id} tile={tile} index={index} />
          ))}
        </div>
      )}
      {page.badge ? <footer className="garden-badge">TeaPass</footer> : null}
    </div>
  );
}
