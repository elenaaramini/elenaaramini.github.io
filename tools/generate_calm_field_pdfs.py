#!/usr/bin/env python3
"""Generate PDF presentation decks for The Calm Field brand study.

The script intentionally has no third-party dependencies so it can run in the
static-site repository and CI-like sandboxes without browser/PDF packages.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import textwrap

OUT_DIR = Path("presentations")
PAGE_W = 842
PAGE_H = 595
MARGIN = 54

COLORS = {
    "ink": (0.13, 0.19, 0.17),
    "muted": (0.39, 0.45, 0.42),
    "cream": (0.97, 0.94, 0.89),
    "paper": (1.0, 0.99, 0.96),
    "green": (0.15, 0.24, 0.21),
    "sand": (0.85, 0.80, 0.72),
    "ochre": (0.61, 0.48, 0.34),
    "terracotta": (0.72, 0.45, 0.29),
    "bosco": (0.25, 0.35, 0.28),
    "blue": (0.18, 0.23, 0.29),
    "sage": (0.84, 0.88, 0.83),
    "slate": (0.18, 0.23, 0.29),
}


def enc(text: str) -> str:
    """Encode text for standard PDF fonts using cp1252 hex strings."""
    safe = (
        text.replace("–", "-")
        .replace("—", "-")
        .replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
        .replace("•", "-")
        .replace("…", "...")
    )
    return safe.encode("cp1252", errors="replace").hex().upper()


class Canvas:
    def __init__(self) -> None:
        self.ops: list[str] = []

    def raw(self, op: str) -> None:
        self.ops.append(op)

    def color(self, name_or_rgb: str | tuple[float, float, float], stroke: bool = False) -> None:
        rgb = COLORS[name_or_rgb] if isinstance(name_or_rgb, str) else name_or_rgb
        self.ops.append(f"{rgb[0]:.4f} {rgb[1]:.4f} {rgb[2]:.4f} {'RG' if stroke else 'rg'}")

    def rect(self, x: float, y: float, w: float, h: float, fill: str | tuple[float, float, float] | None = None,
             stroke: str | tuple[float, float, float] | None = None, width: float = 1) -> None:
        if fill:
            self.color(fill)
        if stroke:
            self.color(stroke, stroke=True)
            self.ops.append(f"{width:.2f} w")
        self.ops.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re {'B' if fill and stroke else 'f' if fill else 'S'}")

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str = "ink", width: float = 1) -> None:
        self.color(color, stroke=True)
        self.ops.append(f"{width:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")

    def circle(self, cx: float, cy: float, r: float, fill: str | None = None, stroke: str | None = None, width: float = 1) -> None:
        k = 0.5522847498
        if fill:
            self.color(fill)
        if stroke:
            self.color(stroke, stroke=True)
            self.ops.append(f"{width:.2f} w")
        self.ops.append(
            f"{cx+r:.2f} {cy:.2f} m "
            f"{cx+r:.2f} {cy+k*r:.2f} {cx+k*r:.2f} {cy+r:.2f} {cx:.2f} {cy+r:.2f} c "
            f"{cx-k*r:.2f} {cy+r:.2f} {cx-r:.2f} {cy+k*r:.2f} {cx-r:.2f} {cy:.2f} c "
            f"{cx-r:.2f} {cy-k*r:.2f} {cx-k*r:.2f} {cy-r:.2f} {cx:.2f} {cy-r:.2f} c "
            f"{cx+k*r:.2f} {cy-r:.2f} {cx+r:.2f} {cy-k*r:.2f} {cx+r:.2f} {cy:.2f} c "
            f"{'B' if fill and stroke else 'f' if fill else 'S'}"
        )

    def text(self, x: float, y: float, text: str, size: float = 16, font: str = "F1", color: str = "ink") -> None:
        self.color(color)
        self.ops.append(f"BT /{font} {size:.2f} Tf {x:.2f} {y:.2f} Td <{enc(text)}> Tj ET")

    def paragraph(self, x: float, y: float, text: str, size: float = 15, width_chars: int = 72,
                  leading: float | None = None, font: str = "F1", color: str = "muted") -> float:
        leading = leading or size * 1.35
        lines = textwrap.wrap(text, width=width_chars)
        cy = y
        for line in lines:
            self.text(x, cy, line, size=size, font=font, color=color)
            cy -= leading
        return cy

    def bytes(self) -> bytes:
        return ("\n".join(self.ops) + "\n").encode("ascii")


class SimplePDF:
    def __init__(self) -> None:
        self.pages: list[bytes] = []

    def add_page(self, canvas: Canvas) -> None:
        self.pages.append(canvas.bytes())

    def write(self, path: Path) -> None:
        objects: list[bytes] = []
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        kids = " ".join(f"{4 + i*2} 0 R" for i in range(len(self.pages)))
        objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(self.pages)} >>".encode())
        objects.append(
            b"<< /Font << "
            b"/F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >> "
            b"/F2 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >> "
            b"/F3 << /Type /Font /Subtype /Type1 /BaseFont /Times-Roman /Encoding /WinAnsiEncoding >> "
            b"/F4 << /Type /Font /Subtype /Type1 /BaseFont /Times-Bold /Encoding /WinAnsiEncoding >> "
            b">> >>"
        )
        for i, stream in enumerate(self.pages):
            content_id = 5 + i * 2
            objects.append(
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] /Resources 3 0 R /Contents {content_id} 0 R >>".encode()
            )
            objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"endstream")

        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for idx, obj in enumerate(objects, start=1):
            offsets.append(len(out))
            out.extend(f"{idx} 0 obj\n".encode())
            out.extend(obj)
            out.extend(b"\nendobj\n")
        xref = len(out)
        out.extend(f"xref\n0 {len(objects)+1}\n".encode())
        out.extend(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            out.extend(f"{off:010d} 00000 n \n".encode())
        out.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
        path.write_bytes(out)


def page_base(title: str, kicker: str = "THE CALM FIELD - BRAND STUDY") -> Canvas:
    c = Canvas()
    c.rect(0, 0, PAGE_W, PAGE_H, fill="cream")
    c.rect(0, 0, 18, PAGE_H, fill="green")
    c.text(MARGIN, PAGE_H - 45, kicker, 10, "F2", "terracotta")
    c.text(MARGIN, PAGE_H - 82, title, 34, "F4", "ink")
    c.line(MARGIN, PAGE_H - 100, PAGE_W - MARGIN, PAGE_H - 100, "sand", 1.2)
    return c


def footer(c: Canvas, page: int, label: str) -> None:
    c.text(MARGIN, 28, label, 9, "F2", "muted")
    c.text(PAGE_W - MARGIN - 18, 28, str(page), 9, "F2", "muted")


def logo_mark(c: Canvas, x: float, y: float, theme: str) -> None:
    color = "green" if theme == "calm" else "bosco" if theme == "campo" else "blue"
    c.circle(x, y, 52, stroke=color, width=2.5)
    c.circle(x, y, 7, fill=color)
    for i, amp in enumerate([0, 12, -10]):
        yy = y - 10 + i * 16
        c.line(x - 42, yy, x - 10, yy + amp / 2, color, 2)
        c.line(x - 10, yy + amp / 2, x + 16, yy - amp / 3, color, 2)
        c.line(x + 16, yy - amp / 3, x + 42, yy + amp / 4, color, 2)


def add_bullets(c: Canvas, x: float, y: float, items: list[str], size: float = 15, width_chars: int = 54) -> float:
    cy = y
    for item in items:
        c.circle(x + 4, cy + 4, 2.2, fill="terracotta")
        cy = c.paragraph(x + 16, cy, item, size=size, width_chars=width_chars, color="muted") - 8
    return cy


@dataclass
class BrandConcept:
    filename: str
    name: str
    subtitle: str
    theme: str
    direction: str
    summary: str
    palette: list[tuple[str, str]]
    social_titles: list[str]
    assessment: list[tuple[str, str]]


CONCEPTS = [
    BrandConcept(
        filename="01-the-calm-field.pdf",
        name="The Calm Field",
        subtitle="Relational Ethology for Humans & Animals",
        theme="calm",
        direction="Versione 01 - internazionale premium",
        summary="La direzione piu esportabile: sobria, elegante e adatta a una seconda fase internazionale. Richiede copy molto chiaro per evitare letture spirituali o terapeutiche.",
        palette=[("Field Green", "green"), ("Warm Sand", "sand"), ("Quiet Cream", "cream"), ("Earth Ochre", "ochre")],
        social_titles=["Prima di chiedere, osserva.", "Calma non significa immobilita.", "Che presenza porti nella relazione?"],
        assessment=[("Vantaggi", "Premium, internazionale, adatto a corsi e contenuti bilingue."), ("Svantaggi", "In Italia puo essere meno immediato: va spiegato bene."), ("Priorita", "Alta se vuoi costruire subito asset esportabili.")],
    ),
    BrandConcept(
        filename="02-campo-relazionale.pdf",
        name="Campo Relazionale",
        subtitle="Etologia, presenza, relazione",
        theme="campo",
        direction="Versione 02 - italiana educativa",
        summary="La direzione piu chiara per vendere subito in Italia. Comunica relazione e pratica concreta, con possibile estensione futura: Campo Relazionale by The Calm Field.",
        palette=[("Bosco", "bosco"), ("Argilla chiara", "sand"), ("Terracotta", "terracotta"), ("Carta", "paper")],
        social_titles=["7 segnali da osservare prima di correggere.", "Quando l'intenzione arriva prima della richiesta.", "Il diario del campo relazionale."],
        assessment=[("Vantaggi", "Molto comprensibile in Italia e facile da vendere in webinar."), ("Svantaggi", "Meno distintivo all'estero: servira architettura di naming."), ("Priorita", "Molto alta per validare il mercato italiano." )],
    ),
    BrandConcept(
        filename="03-animalia-relazionale.pdf",
        name="Animalia Relazionale",
        subtitle="Scuola di etologia relazionale",
        theme="animalia",
        direction="Versione 03 - istituzionale scalabile",
        summary="La direzione piu scuola/metodo: meno poetica e piu istituzionale. Utile per piattaforma educativa, percorsi, docenti e formazione futura.",
        palette=[("Blu ardesia", "blue"), ("Salvia chiara", "sage"), ("Rovere", "ochre"), ("Avorio", "paper")],
        social_titles=["La relazione non e una tecnica.", "Etologia relazionale per la vita quotidiana.", "Dal comportamento al contesto."],
        assessment=[("Vantaggi", "Solida per academy, partnership e formazione futura."), ("Svantaggi", "Meno emozionale: puo sembrare accademica."), ("Priorita", "Media ora, alta se diventa una scuola strutturata." )],
    ),
]


def cover_deck(title: str, subtitle: str) -> Canvas:
    c = Canvas()
    c.rect(0, 0, PAGE_W, PAGE_H, fill="cream")
    c.rect(0, 0, PAGE_W, PAGE_H, stroke="sand", width=14)
    c.circle(706, 446, 126, stroke="sand", width=2)
    c.circle(706, 446, 58, fill="green")
    c.text(MARGIN, PAGE_H - 68, "STUDIO INIZIALE DI AGENZIA", 11, "F2", "terracotta")
    c.text(MARGIN, PAGE_H - 148, title, 52, "F4", "ink")
    c.paragraph(MARGIN, PAGE_H - 202, subtitle, 20, width_chars=62, color="muted")
    c.rect(MARGIN, 92, 250, 70, fill="green")
    c.text(MARGIN + 18, 126, "Elena Aramini", 19, "F2", "paper")
    c.text(MARGIN + 18, 106, "Italia oggi, internazionale domani", 10, "F1", "sand")
    return c


def strategy_pages(pdf: SimplePDF, start_page: int = 2) -> int:
    c = page_base("Fondazione strategica")
    c.paragraph(MARGIN, 435, "Obiettivo: costruire un brand italiano credibile e scalabile, dedicato alla relazione consapevole tra persone e animali, senza diventare training performativo, terapia o spiritualita generica.", 18, 72)
    add_bullets(c, MARGIN, 330, [
        "Categoria: etologia relazionale applicata alla vita quotidiana con animali familiari e cavalli.",
        "Promessa realistica: osservare meglio, intervenire meno impulsivamente e creare relazioni piu sicure e consapevoli.",
        "Confine etico: educazione e benessere relazionale; nessuna diagnosi, cura o promessa di guarigione.",
        "Scelta commerciale: partire in italiano con copy chiaro, ma progettare naming e visual gia espandibili all'estero.",
    ])
    footer(c, start_page, "Posizionamento")
    pdf.add_page(c)
    return start_page + 1


def concept_page(concept: BrandConcept, page_num: int) -> Canvas:
    c = page_base(concept.name, concept.direction)
    logo_mark(c, 126, 348, concept.theme)
    c.text(58, 270, concept.name, 28, "F4", "ink")
    c.text(58, 245, concept.subtitle, 10, "F2", "terracotta")
    c.paragraph(270, 420, concept.summary, 18, 60)
    x = 270
    y = 300
    for label, color in concept.palette:
        c.rect(x, y, 118, 58, fill=color, stroke="paper", width=1)
        c.text(x + 10, y + 22, label, 9, "F2", "paper" if color in {"green", "bosco", "blue", "terracotta", "ochre"} else "ink")
        x += 132
    y = 162
    for title in concept.social_titles:
        c.rect(58 + concept.social_titles.index(title) * 252, y, 224, 86, fill="paper", stroke="sand", width=1)
        c.text(74 + concept.social_titles.index(title) * 252, y + 58, "SOCIAL MOCKUP", 8, "F2", "terracotta")
        c.paragraph(74 + concept.social_titles.index(title) * 252, y + 38, title, 13, 24, font="F2", color="ink")
    footer(c, page_num, concept.name)
    return c


def assessment_page(concept: BrandConcept, page_num: int) -> Canvas:
    c = page_base(f"Valutazione - {concept.name}")
    add_bullets(c, MARGIN, 420, [f"{k}: {v}" for k, v in concept.assessment], 17, 78)
    add_bullets(c, MARGIN, 270, [
        "Difficolta: media, perche il pubblico deve capire cosa compra prima di apprezzare la filosofia.",
        "Costi: bassi per MVP digitale; medi se si aggiungono trademark, shooting e identita completa.",
        "Tempo: 2-8 settimane a seconda della profondita del lancio.",
        "Potenziale economico: buono nel mercato italiano se collegato a quiz, newsletter, mini percorso e consulenze pilota.",
    ], 15, 82)
    footer(c, page_num, "Valutazione commerciale")
    return c


def mvp_page(page_num: int) -> Canvas:
    c = page_base("MVP commerciale per l'Italia")
    cards = [
        ("Gratis", "Quiz + checklist", "Pattern relazionale + guida di osservazione prima dell'intervento."),
        ("Entry 19-39 EUR", "Audio + workbook", "Pratiche brevi di presenza, osservazione e journaling."),
        ("Core 149-349 EUR", "Corso base", "Metodo di osservazione relazionale in 4-6 settimane."),
        ("Premium 450-1.200 EUR", "Review individuale", "Questionario, video/situazioni e piano educativo non clinico."),
    ]
    x = MARGIN
    for tier, title, body in cards:
        c.rect(x, 215, 178, 210, fill="paper", stroke="sand", width=1)
        c.text(x + 16, 385, tier, 9, "F2", "terracotta")
        c.paragraph(x + 16, 350, title, 19, 17, font="F2", color="ink")
        c.paragraph(x + 16, 284, body, 13, 22, color="muted")
        x += 194
    footer(c, page_num, "Offerte")
    return c


def roadmap_page(page_num: int) -> Canvas:
    c = page_base("Roadmap 90 giorni")
    steps = [
        ("01 Fondazione", "Nome, manifesto, confini etici, landing page, kit gratuito e prime 8 email."),
        ("02 Audience", "12 contenuti evergreen, interviste, quiz e lista d'attesa."),
        ("03 Beta", "Mini percorso, 5 consulenze pilota, feedback e revisione copy."),
    ]
    x = MARGIN
    for title, body in steps:
        c.circle(x + 28, 370, 28, fill="green")
        c.text(x + 14, 365, title[:2], 16, "F2", "paper")
        c.text(x, 312, title, 22, "F4", "ink")
        c.paragraph(x, 274, body, 15, 28, color="muted")
        x += 258
    c.rect(MARGIN, 96, PAGE_W - MARGIN * 2, 70, fill="paper", stroke="sand", width=1)
    c.text(MARGIN + 20, 128, "Verdetto: vendere in Italia con chiarezza, non costruire subito una grande academy.", 17, "F2", "ink")
    c.text(MARGIN + 20, 108, "Testare nome, lead magnet, prezzo entry e consulenze prima di ampliare.", 12, "F1", "muted")
    footer(c, page_num, "Roadmap")
    return c


def build_master() -> None:
    pdf = SimplePDF()
    pdf.add_page(cover_deck("The Calm Field", "Studio brand e progetto commerciale: tre direzioni visuali per un'impresa italiana di etologia relazionale, pensata per espandersi in futuro."))
    page = strategy_pages(pdf, 2)
    for concept in CONCEPTS:
        pdf.add_page(concept_page(concept, page)); page += 1
        pdf.add_page(assessment_page(concept, page)); page += 1
    pdf.add_page(mvp_page(page)); page += 1
    pdf.add_page(roadmap_page(page))
    pdf.write(OUT_DIR / "the-calm-field-brand-study.pdf")


def build_individual(concept: BrandConcept) -> None:
    pdf = SimplePDF()
    pdf.add_page(cover_deck(concept.name, f"{concept.direction}. {concept.summary}"))
    pdf.add_page(concept_page(concept, 2))
    pdf.add_page(assessment_page(concept, 3))
    pdf.add_page(mvp_page(4))
    pdf.add_page(roadmap_page(5))
    pdf.write(OUT_DIR / concept.filename)


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    build_master()
    for concept in CONCEPTS:
        build_individual(concept)
    for pdf in sorted(OUT_DIR.glob("*.pdf")):
        print(f"generated {pdf} ({pdf.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
