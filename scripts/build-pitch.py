#!/usr/bin/env python3
"""Build the Wave 2 slide deck and a short pitch video from one script."""

import shutil
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "submission"
W, H = 960, 540

SLIDES = [
    {
        "kicker": "Midnight Buildathon  /  Wave 2",
        "title": "TeaPass",
        "lines": [
            "A private proof that a tea lot was issued, blended, and tested.",
            "The recipe stays off the ledger.",
            "Local devnet evidence, 19 October 2026.",
        ],
    },
    {
        "kicker": "The record that has to stay private",
        "title": "Lots are blended.",
        "lines": [
            "A finished batch is made from other batches.",
            "The factory will not publish suppliers, weights, or the formula.",
            "A buyer still needs to check that the recorded weights obeyed the rule.",
            "The proof checks that digital record.",
            "It does not prove where the physical leaf grew.",
        ],
    },
    {
        "kicker": "What the chain is allowed to see",
        "title": "Hide the recipe.",
        "lines": [
            "Private: quantities, salts, owner secrets, the lab reading, the blend split.",
            "Public: commitments, nullifiers, issuer and lab authority,",
            "the batch reference, the material class, and whether the claim still holds.",
            "Supply-graph anonymity is not claimed.",
            "Public note metadata does reveal the batch reference and material.",
        ],
    },
    {
        "kicker": "Settled on the local Midnight devnet",
        "title": "100 + 80 = 40 + 40 + 100",
        "lines": [
            "Authorized issuer. Two made-tea notes: 100 kg and 80 kg.",
            "The blend consumes both and creates two 40 kg remainders",
            "and one 100 kg blend. Mass must balance.",
            "Blend transaction 005dc40a settled in block 391.",
            "A second spend fails against indexed state, before submission.",
            "Contract 774a4f1b on the local undeployed network.",
        ],
    },
    {
        "kicker": "A claim, not a food-safety badge",
        "title": "The reading stays hidden.",
        "lines": [
            "An approved lab anchors a salted result to the batch commitment.",
            "The circuit proves that reading is under the stated demo threshold.",
            "Judges see the policy, the lab, and the status. Not the measurement.",
            "The replay then revokes the lab.",
            "The saved public claim becomes INVALID.",
        ],
    },
    {
        "kicker": "How a judge reproduces it",
        "title": "Compile it yourself.",
        "lines": [
            "scripts/replay-judges.sh",
            "Pins Compact 0.31.1, starts the local node, indexer, and proof server,",
            "and replays issuance, the blend, the lab proof, and revocation.",
            "Receipts: artifacts/midnight/inventory-local.json",
            "Walkthrough: docs/JUDGES.md and docs/PROOF.md.",
        ],
    },
    {
        "kicker": "Said plainly",
        "title": "What this is not.",
        "lines": [
            "Not Midnight preview, preprod, or mainnet.",
            "Not a browser that submits these transactions yet.",
            "A finalized job does not, by itself, prove that declared lineage",
            "edges match the private witnesses.",
            "Negative cases fail in the circuit, before the node accepts them.",
        ],
    },
    {
        "kicker": "This wave",
        "title": "New Compact rules.",
        "lines": [
            "Inventory issuance, transfer, split, blend, and processing.",
            "A batch-bound laboratory threshold proof, with revocation.",
            "An API that reconciles finality and will not fake a verified flag.",
            "Apache-2.0. The judge compiles from this repository.",
        ],
    },
]


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def page_stream(slide: dict) -> bytes:
    ops = [
        "0.984 0.969 0.941 rg",
        f"0 0 {W} {H} re f",
        "0.118 0.302 0.204 rg",
        f"0 {H - 8} {W} 8 re f",
        "0.769 0.396 0.290 rg",
        "0 0 8 540 re f",
        "BT",
        "/F2 14 Tf",
        "0.769 0.396 0.290 rg",
        "64 470 Td",
        f"({esc(slide['kicker'])}) Tj",
        "/F1 42 Tf",
        "0.118 0.302 0.204 rg",
        "0 -62 Td",
        f"({esc(slide['title'])}) Tj",
        "/F2 20 Tf",
        "0.176 0.227 0.188 rg",
    ]
    first = True
    for line in slide["lines"]:
        ops.append("0 -40 Td" if first else "0 -32 Td")
        first = False
        ops.append(f"({esc(line)}) Tj")
    ops.append("ET")
    return "\n".join(ops).encode()


def write_pdf(path: Path) -> None:
    streams = [page_stream(slide) for slide in SLIDES]
    objects: list[bytes] = []

    def add(data: bytes) -> int:
        objects.append(data)
        return len(objects)

    font1 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman >>")
    font2 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    content_ids = [add(b"<< /Length %d >>\nstream\n" % len(raw) + raw + b"\nendstream") for raw in streams]
    page_ids = []
    for cid in content_ids:
        page_ids.append(
            add(
                (
                    f"<< /Type /Page /Parent 0 0 R /MediaBox [0 0 {W} {H}] "
                    f"/Resources << /Font << /F1 {font1} 0 R /F2 {font2} 0 R >> >> "
                    f"/Contents {cid} 0 R >>"
                ).encode()
            )
        )
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    pages = add(f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids}] >>".encode())
    for index, pid in enumerate(page_ids):
        objects[pid - 1] = objects[pid - 1].replace(b"/Parent 0 0 R", f"/Parent {pages} 0 R".encode())
    catalog = add(f"<< /Type /Catalog /Pages {pages} 0 R >>".encode())
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer << /Size {len(objects) + 1} /Root {catalog} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(out)


NARRATION = textwrap.dedent(
    """
    TeaPass is a private proof that a tea lot was issued, blended, and tested, without putting the recipe on the ledger.

    Assam tea is split and blended before it reaches a buyer. The factory cannot publish its suppliers or its formula. The buyer still needs to know the recorded weights followed the rule. The proof checks that digital record. It does not prove where the physical leaf grew.

    The Compact contract keeps quantities, salts, and the lab reading private. What the chain shows is a commitment, a nullifier, the issuer, the material class, and whether the claim still holds. We do not claim the supply graph is anonymous.

    On the local Midnight devnet, an authorized issuer committed one hundred kilograms and eighty kilograms of made tea. The blend circuit consumed both notes and created two forty kilogram remainders and a one hundred kilogram blend. That transaction settled in block three ninety one. Spending either input again fails against the indexed state, before a second transaction is submitted.

    A registered lab then anchors a synthetic test to that batch. The circuit proves the hidden reading sits under the stated threshold. Judges see the policy, the lab, and the status. They do not see the measurement. The replay ends by revoking the lab, so the public claim becomes invalid.

    To reproduce it, run scripts slash replay judges dot sh. It installs the pinned Compact compiler, starts the local node, and writes the receipts under artifacts slash midnight. The walkthrough is in the judges guide.

    This evidence is a local undeployed network, not Midnight preprod or mainnet. The browser does not yet send these transactions. And a finalized job is not, by itself, proof that the private witnesses match every declared lineage edge.

    The Midnight code in this repository is new, Apache licensed, and meant to be compiled by the judge. That is the Wave 2 submission.
    """
).strip()


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


RENDER = r"""
import AppKit
import Foundation
import PDFKit

let pdf = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1]))!
let directory = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true)
for index in 0..<pdf.pageCount {
    let page = pdf.page(at: index)!
    let bounds = page.bounds(for: .mediaBox)
    let scale: CGFloat = 2
    let width = Int(bounds.width * scale)
    let height = Int(bounds.height * scale)
    let image = NSImage(size: NSSize(width: width, height: height))
    image.lockFocus()
    let context = NSGraphicsContext.current!.cgContext
    context.setFillColor(NSColor(calibratedRed: 0.984, green: 0.969, blue: 0.941, alpha: 1).cgColor)
    context.fill(CGRect(x: 0, y: 0, width: width, height: height))
    context.saveGState()
    context.scaleBy(x: scale, y: scale)
    page.draw(with: .mediaBox, to: context)
    context.restoreGState()
    image.unlockFocus()
    let rep = NSBitmapImageRep(data: image.tiffRepresentation!)!
    let png = rep.representation(using: .png, properties: [:])!
    try png.write(to: directory.appendingPathComponent(String(format: "slide-%02d.png", index)))
}
"""


def write_video(work: Path, audio: Path, pdf: Path) -> Path:
    duration = float(
        subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(audio)],
            text=True,
        ).strip()
    )
    weights = [max(1, len(slide["title"]) + sum(len(line) for line in slide["lines"])) for slide in SLIDES]
    total = sum(weights)
    spans = [duration * weight / total for weight in weights]
    renderer = work / "render.swift"
    renderer.write_text(RENDER)
    run(["swift", str(renderer), str(pdf), str(work)])
    inputs: list[str] = []
    for index, span in enumerate(spans):
        inputs += ["-loop", "1", "-t", f"{span:.3f}", "-i", str(work / f"slide-{index:02d}.png")]
    filters = []
    for index in range(len(spans)):
        filters.append(f"[{index}:v]scale=1920:1080,fps=30,format=yuv420p[v{index}]")
    chain = "".join(f"[v{index}]" for index in range(len(spans))) + f"concat=n={len(spans)}:v=1:a=0[v]"
    video = work / "picture.mp4"
    run(
        ["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters) + ";" + chain, "-map", "[v]", str(video)]
    )
    final = OUT / "akindo-wave2-pitch.mp4"
    run(
        [
            "ffmpeg", "-y", "-i", str(video), "-i", str(audio),
            "-c:v", "libx264", "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(final),
        ]
    )
    return final


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pdf = OUT / "akindo-wave2-deck.pdf"
    write_pdf(pdf)
    work = OUT / ".build"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir()
    script = work / "narration.txt"
    script.write_text(NARRATION + "\n")
    audio = work / "narration.aiff"
    run(["say", "-v", "Samantha", "-o", str(audio), "-f", str(script)])
    video = write_video(work, audio, pdf)
    shutil.rmtree(work)
    print(pdf)
    print(video)


if __name__ == "__main__":
    main()
