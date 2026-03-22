from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io
from datetime import datetime


def generate_pdf(plan: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    PRIMARY = colors.HexColor("#2E86AB")
    SECONDARY = colors.HexColor("#F18F01")
    LIGHT = colors.HexColor("#F5F5F5")

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=24,
        textColor=PRIMARY,
        spaceAfter=6,
        alignment=TA_CENTER
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=12,
        textColor=colors.grey,
        spaceAfter=20,
        alignment=TA_CENTER
    )
    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=PRIMARY,
        spaceBefore=16,
        spaceAfter=8,
        borderPad=4
    )
    day_style = ParagraphStyle(
        "Day",
        parent=styles["Heading3"],
        fontSize=12,
        textColor=SECONDARY,
        spaceBefore=10,
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=4,
        leading=14
    )

    story = []

    # Titre
    dest = plan.get("destination", "Destination")
    origin = plan.get("origin", "")
    dates = plan.get("dates", "")
    story.append(Paragraph(f"✈ Itinéraire de Voyage", title_style))
    story.append(Paragraph(f"{origin} → {dest} | {dates}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=PRIMARY))
    story.append(Spacer(1, 0.4*cm))

    # Infos générales
    story.append(Paragraph("📋 Informations générales", section_style))
    info_data = [
        ["Destination", dest],
        ["Départ", origin],
        ["Dates", dates],
        ["Voyageurs", str(plan.get("travelers", 1))],
        ["Budget total", f"{plan.get('budget', 0)}€"],
        ["Type de voyage", plan.get("travel_type", "équilibré").capitalize()],
    ]
    info_table = Table(info_data, colWidths=[5*cm, 12*cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("TEXTCOLOR", (0, 0), (0, -1), PRIMARY),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, LIGHT]),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.4*cm))

    # Budget
    if plan.get("budget_breakdown"):
        story.append(Paragraph("💰 Répartition du budget", section_style))
        budget_data = [["Catégorie", "Total (€)", "Par pers./jour (€)"]]
        b = plan["budget_breakdown"]
        for cat, vals in b.items():
            budget_data.append([
                cat.replace("_", " ").capitalize(),
                f"{vals['total']:.0f}€",
                f"{vals['per_person_per_day']:.0f}€"
            ])
        # Ligne vols
        budget_data.insert(1, ["Vols", f"{plan.get('flight_cost', 0):.0f}€", "-"])

        b_table = Table(budget_data, colWidths=[8*cm, 4.5*cm, 4.5*cm])
        b_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(b_table)
        story.append(Spacer(1, 0.4*cm))

    # Météo
    if plan.get("weather"):
        story.append(Paragraph("🌤 Prévisions météo", section_style))
        weather_data = [["Date", "Conditions", "Temp. min", "Temp. max", "Humidité"]]
        for day in plan["weather"][:7]:
            weather_data.append([
                day["date"],
                day["description"].capitalize(),
                f"{day['temp_min']}°C",
                f"{day['temp_max']}°C",
                f"{day['humidity']}%"
            ])
        w_table = Table(weather_data, colWidths=[3*cm, 5*cm, 2.5*cm, 2.5*cm, 2.5*cm])
        w_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), SECONDARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
            ("ALIGN", (2, 0), (-1, -1), "CENTER"),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(w_table)
        story.append(Spacer(1, 0.4*cm))

    # Itinéraire
    if plan.get("itinerary"):
        story.append(Paragraph("📅 Itinéraire jour par jour", section_style))
        for day_plan in plan["itinerary"]:
            story.append(Paragraph(
                f"Jour {day_plan.get('day', '?')} — {day_plan.get('date', '')} : {day_plan.get('title', '')}",
                day_style
            ))
            for activity in day_plan.get("activities", []):
                story.append(Paragraph(f"• {activity}", body_style))
            story.append(Spacer(1, 0.2*cm))

    # Conseils
    if plan.get("tips"):
        story.append(Paragraph("💡 Conseils pratiques", section_style))
        for tip in plan["tips"]:
            story.append(Paragraph(f"• {tip}", body_style))

    # Footer
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Paragraph(
        f"Généré par l'Agent Planificateur de Voyage — {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8,
                      textColor=colors.grey, alignment=TA_CENTER)
    ))

    doc.build(story)
    return buffer.getvalue()
