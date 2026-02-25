"""
═══════════════════════════════════════════════════════════════════════════════
MODULE: app/components/cards.py
Description: Composants de cartes réutilisables (métriques, formulations, alertes)
Auteur: Stage R&D - IMT Nord Europe
Version: 1.0.0 - Refactorisé & aligné avec ValidationReport v1.0.0
═══════════════════════════════════════════════════════════════════════════════
"""

import html as html_stdlib
import logging
import re
from typing import Any, Callable, Dict, List, Optional

import streamlit as st

from config.constants import COLOR_PALETTE, QUALITY_THRESHOLDS, STATUS_EMOJI
from config.settings import UI_SETTINGS
from app.core.validator import ValidationAlert, ValidationReport, Severity

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES INTERNES
# ═══════════════════════════════════════════════════════════════════════════════

# Couleurs associées aux niveaux de sévérité (cohérent avec validator.py)
_SEVERITY_COLORS: Dict[str, str] = {
    "critical": COLOR_PALETTE.get("danger",  "#c0392b"),
    "error":    COLOR_PALETTE.get("danger",  "#e74c3c"),
    "warning":  COLOR_PALETTE.get("warning", "#f39c12"),
    "info":     COLOR_PALETTE.get("info",    "#2980b9"),
}

# Emojis de sévérité
_SEVERITY_EMOJIS: Dict[str, str] = {
    "critical": "🚨",
    "error":    "❌",
    "warning":  "⚠️",
    "info":     "ℹ️",
}

# Correspondance sévérité → méthode Streamlit d'affichage
_SEVERITY_ST_FN: Dict[str, Any] = {
    "critical": st.error,
    "error":    st.error,
    "warning":  st.warning,
    "info":     st.info,
}

# Ordre de tri des sévérités (CRITICAL en premier)
_SEVERITY_ORDER: Dict[Severity, int] = {
    Severity.CRITICAL: 0,
    Severity.ERROR:    1,
    Severity.WARNING:  2,
    Severity.INFO:     3,
}


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS PRIVÉS
# ═══════════════════════════════════════════════════════════════════════════════

def _format_value(value: float) -> str:
    """
    Formate un nombre flottant de façon lisible.

    Règles :
      - ≥ 1 000 → séparateur milliers + 1 décimale  (ex: 1 250.0)
      - ≥ 10   → 1 décimale                          (ex: 45.2)
      - < 10   → 2 décimales                         (ex: 0.45)

    Args:
        value: Valeur numérique

    Returns:
        Chaîne formatée
    """
    abs_v = abs(value)
    if abs_v >= 1_000:
        return f"{value:,.1f}"
    if abs_v >= 10:
        return f"{value:.1f}"
    return f"{value:.2f}"


def _simple_markdown_to_html(text: str) -> str:
    """
    Convertit un sous-ensemble de Markdown en HTML sans dépendance externe.

    Gère : **gras**, *italique*, listes à puces (• ou -), sauts de ligne.

    Args:
        text: Texte Markdown simplifié

    Returns:
        HTML sécurisé (entités HTML échappées avant transformation)
    """
    # 1. Échapper les caractères HTML dangereux (XSS)
    escaped = html_stdlib.escape(text, quote=False)

    # 2. Blocs de liste : lignes commençant par •, - ou *
    lines = escaped.split("\n")
    html_lines: List[str] = []
    in_list = False

    for line in lines:
        stripped = line.strip()
        is_bullet = re.match(r"^[\*\-•]\s+(.+)$", stripped)

        if is_bullet:
            if not in_list:
                html_lines.append("<ul style='margin: 0.4rem 0 0.4rem 1.2rem; padding: 0;'>")
                in_list = True
            html_lines.append(f"<li>{is_bullet.group(1)}</li>")
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            if stripped:
                html_lines.append(f"<p style='margin: 0.2rem 0;'>{stripped}</p>")
            else:
                html_lines.append("<br>")

    if in_list:
        html_lines.append("</ul>")

    result = "\n".join(html_lines)

    # 3. **gras**
    result = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", result)

    # 4. *italique*
    result = re.sub(r"\*(.+?)\*", r"<em>\1</em>", result)

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# METRIC CARD
# ═══════════════════════════════════════════════════════════════════════════════

def metric_card(
    title:         str,
    value:         float,
    unit:          str = "",
    delta:         Optional[float] = None,
    icon:          str = "📊",
    help_text:     Optional[str] = None,
    quality_grade: Optional[str] = None,
    key:           Optional[str] = None,
) -> None:
    """
    Carte métrique stylisée avec couleur dynamique selon le grade qualité.

    Signature v1.0.0 (propre, sans détection d'ordre d'arguments) :
        metric_card(title, value, unit, delta, icon, help_text, quality_grade, key)

    Args:
        title        : Libellé de la métrique (ex: "Résistance")
        value        : Valeur numérique à afficher
        unit         : Unité (ex: "MPa", "kg/m³")
        delta        : Variation optionnelle (float). Positif = vert, négatif = rouge.
        icon         : Emoji préfixant le titre
        help_text    : Texte d'aide dans un expander (optionnel)
        quality_grade: Clé dans QUALITY_THRESHOLDS ("excellent", "bon", "moyen", …)
        key          : Clé Streamlit unique (non utilisée ici, réservé pour extension)

    Example:
        ```python
        metric_card(
            title="Résistance",
            value=45.2,
            unit="MPa",
            icon="💪",
            quality_grade="excellent",
        )
        ```
    """
    # ── Couleur et emoji selon grade ────────────────────────────────────────
    if quality_grade and quality_grade in QUALITY_THRESHOLDS:
        color_key  = QUALITY_THRESHOLDS[quality_grade].get("color", "primary")
        card_color = COLOR_PALETTE.get(color_key, COLOR_PALETTE["primary"])
        grade_emoji = STATUS_EMOJI.get(quality_grade, "")
    else:
        card_color  = COLOR_PALETTE["primary"]
        grade_emoji = ""

    # ── Formatage de la valeur ──────────────────────────────────────────────
    value_str = _format_value(value)

    # ── Delta (variation) ───────────────────────────────────────────────────
    delta_html = ""
    if delta is not None and isinstance(delta, (int, float)):
        delta_color  = COLOR_PALETTE.get("success", "#27ae60") if delta >= 0 \
                       else COLOR_PALETTE.get("danger", "#e74c3c")
        delta_symbol = "↑" if delta >= 0 else "↓"
        delta_html = (
            f'<span style="color:{delta_color}; font-size:0.85rem; margin-left:0.5rem;">'
            f'{delta_symbol} {abs(delta):.1f}'
            f'</span>'
        )

    # ── HTML de la carte ────────────────────────────────────────────────────
    card_html = f"""
    <div class="custom-metric-card" style="
        background: linear-gradient(135deg, {card_color}18 0%, {card_color}06 100%);
        border-left: 4px solid {card_color};
        border-radius: 8px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        box-shadow: 0 3px 10px rgba(0,0,0,0.07);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    ">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div style="flex: 1;">
                <div style="
                    color: {UI_SETTINGS['colors']['dark']};
                    font-size: 0.88rem;
                    margin-bottom: 0.35rem;
                    opacity: 0.75;
                    letter-spacing: 0.02em;
                ">
                    {icon} {html_stdlib.escape(title)}
                </div>
                <div style="
                    color: {card_color};
                    font-size: 2.2rem;
                    font-weight: 700;
                    line-height: 1.1;
                ">
                    {value_str}
                    <span style="font-size: 1rem; font-weight: 400; opacity: 0.85; margin-left: 0.2rem;">
                        {html_stdlib.escape(unit)}
                    </span>
                    {delta_html}
                </div>
            </div>
            <div style="font-size: 2.8rem; opacity: 0.2; margin-left: 0.5rem;">
                {grade_emoji}
            </div>
        </div>
    </div>
    <style>
        .custom-metric-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 7px 18px rgba(0,0,0,0.11);
        }}
    </style>
    """

    st.html(card_html)

    # ── Aide contextuelle ───────────────────────────────────────────────────
    if help_text:
        with st.expander("Détails", expanded=False):
            st.caption(help_text)


# ═══════════════════════════════════════════════════════════════════════════════
# FORMULATION CARD
# ═══════════════════════════════════════════════════════════════════════════════

def formulation_card(
    composition:   Dict[str, float],
    predictions:   Dict[str, float],
    name:          str = "Formulation",
    on_select:     Optional[Callable] = None,
    show_actions:  bool = True,
) -> None:
    """
    Carte affichant une formulation béton avec ses propriétés prédites.

    Affiche les constituants principaux, le ratio E/L et les prédictions clés.
    Trois boutons d'action : Analyser, Favori, Export.

    Args:
        composition  : Composition béton (kg/m³)
        predictions  : Résultats de prédiction ML
        name         : Nom de la formulation
        on_select    : Callback appelé lors du clic sur "Analyser"
                       (reçoit composition, predictions)
        show_actions : Afficher les boutons d'action

    Example:
        ```python
        formulation_card(
            composition={"Ciment": 350, "Eau": 175, "Laitier": 100},
            predictions={"Resistance": 45.2, "Diffusion_Cl": 6.1},
            name="C35/45 HP",
            on_select=lambda c, p: st.session_state.update({"selected": c}),
        )
        ```
    """
    with st.container():

        # ── Header ──────────────────────────────────────────────────────────
        st.markdown(
            f"""
            <div style="
                background: {COLOR_PALETTE['primary']};
                color: white;
                padding: 0.75rem 1rem;
                border-radius: 8px 8px 0 0;
                font-weight: 600;
                font-size: 1rem;
            ">
                🧪 {html_stdlib.escape(name)}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Corps ───────────────────────────────────────────────────────────
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**📦 Composition**")
            _MAIN_COMPONENTS = [
                "Ciment", "Laitier", "CendresVolantes",
                "Eau", "Superplastifiant",
            ]
            for comp in _MAIN_COMPONENTS:
                val = composition.get(comp, 0.0)
                if val > 0:
                    st.caption(f"• {comp} : **{val:.1f}** kg/m³")

            if "Ratio_E_L" in predictions:
                st.caption(f"• Ratio E/L : **{predictions['Ratio_E_L']:.3f}**")

        with col2:
            st.markdown("**🎯 Prédictions**")
            resistance    = predictions.get("Resistance", 0.0)
            diffusion     = predictions.get("Diffusion_Cl", 0.0)
            carbonatation = predictions.get("Carbonatation", 0.0)

            st.caption(f"💪 Résistance : **{resistance:.1f}** MPa")
            st.caption(f"🧂 Diffusion Cl⁻ : **{diffusion:.2f}** ×10⁻¹²")
            st.caption(f"🌫️ Carbonatation : **{carbonatation:.1f}** mm")

        # ── Actions ─────────────────────────────────────────────────────────
        if show_actions:
            st.markdown("---")
            col_a, col_b, col_c = st.columns(3)

            with col_a:
                if st.button("📊 Analyser", key=f"analyze_{name}",
                             use_container_width=True):
                    if on_select:
                        on_select(composition, predictions)

            with col_b:
                if st.button("⭐ Favori", key=f"fav_{name}",
                             use_container_width=True):
                    st.toast(f"⭐ {name} ajouté aux favoris")

            with col_c:
                if st.button("📥 Export", key=f"export_{name}",
                             use_container_width=True):
                    st.toast("📥 Export en cours…")


# ═══════════════════════════════════════════════════════════════════════════════
# ALERT BANNER
# ═══════════════════════════════════════════════════════════════════════════════

def alert_banner(
    alerts:      List[ValidationAlert],
    max_display: int = 5,
) -> None:
    """
    Affiche une liste d'alertes de validation, triées par sévérité décroissante.

    Les alertes CRITICAL et ERROR apparaissent en premier.
    Les alertes au-delà de `max_display` sont masquées dans un expander.

    Args:
        alerts     : Liste de ValidationAlert (depuis validate_formulation())
        max_display: Nombre maximum d'alertes affichées directement

    Example:
        ```python
        report = validate_formulation(composition, predictions, required_class="XD2")
        alert_banner(report.alerts)
        ```
    """
    if not alerts:
        st.success("Aucune alerte — Formulation conforme")
        return

    # Tri par sévérité décroissante
    sorted_alerts = sorted(
        alerts,
        key=lambda a: _SEVERITY_ORDER.get(a.severity, 9),
    )

    displayed = sorted_alerts[:max_display]
    hidden    = sorted_alerts[max_display:]

    st.markdown(f"### 🚨 Alertes de Validation ({len(alerts)})")

    for alert in displayed:
        sev_val  = alert.severity.value
        emoji    = _SEVERITY_EMOJIS.get(sev_val, "•")
        st_fn    = _SEVERITY_ST_FN.get(sev_val, st.info)

        # Message structuré (pas de f-string trop long)
        parts = [
            f"**{emoji} {alert.category}**\n\n",
            alert.message,
            f"\n\n💡 **Recommandation** : {alert.recommendation}",
        ]
        if alert.norm_ref:
            parts.append(f"\n\n📖 *Norme : {alert.norm_ref}*")

        st_fn("".join(parts))

    # Alertes masquées
    if hidden:
        with st.expander(f"➕ Afficher {len(hidden)} alerte(s) supplémentaire(s)"):
            for alert in hidden:
                sev_val = alert.severity.value
                emoji   = _SEVERITY_EMOJIS.get(sev_val, "•")
                st.caption(
                    f"{emoji} **{alert.category}** : {alert.message}"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# VERDICT CARD (NOUVEAU — aligné avec ValidationReport v1.0.0)
# ═══════════════════════════════════════════════════════════════════════════════

def verdict_card(report: ValidationReport) -> None:
    """
    Affiche un bandeau de verdict contractuel complet à partir d'un ValidationReport.

    Affiche :
      - Verdict global (CONFORME / NON CONFORME / INVALIDE)
      - Classe exigée vs classe atteinte (côte à côte)
      - Score de conformité + classe de résistance

    Conçu pour être le premier bloc affiché dans la page résultats,
    avant tout détail technique.

    Args:
        report: ValidationReport produit par validate_formulation()

    Example:
        ```python
        report = validate_formulation(composition, predictions, required_class="XD2")
        verdict_card(report)
        ```
    """
    # ── Bandeau verdict ─────────────────────────────────────────────────────
    if not report.is_valid:
        st.error(
            "🚨 **INVALIDE** — La formulation contient au moins une alerte CRITICAL. "
            "Elle est physiquement inutilisable en l'état.",
            icon="🚨",
        )
    elif report.compliance_with_required:
        st.success(
            f"**CONFORME** — La formulation satisfait les exigences EN 206.",
            icon="✅",
        )
    else:
        st.error(
            f"❌ **NON CONFORME** — La formulation ne satisfait pas la classe d'exposition exigée.",
            icon="❌",
        )

    # ── Comparaison Classe Exigée → Classe Atteinte ─────────────────────────
    required = report.required_class or "—"
    achieved = report.achieved_class or "—"

    col_req, col_arrow, col_ach, col_score = st.columns([2, 0.4, 2, 2])

    with col_req:
        st.metric(
            label="📋 Classe Exigée",
            value=required,
            help="Classe d'exposition imposée par l'environnement du projet (EN 206)",
        )

    with col_arrow:
        st.markdown(
            "<div style='text-align:center; font-size:1.8rem; padding-top:1.4rem;'>→</div>",
            unsafe_allow_html=True,
        )

    with col_ach:
        delta_text  = "✅ Conforme" if report.compliance_with_required else "❌ Insuffisant"
        delta_color = "normal"      if report.compliance_with_required else "inverse"
        st.metric(
            label="🎯 Classe Atteinte",
            value=achieved,
            delta=delta_text,
            delta_color=delta_color,
            help="Classe réellement atteinte par la formulation (moteur EN 206)",
        )

    with col_score:
        score     = report.compliance_score
        color_dot = "🟢" if score >= 80 else ("🟡" if score >= 60 else "🔴")
        res_class = report.resistance_class or "N/A"
        st.metric(
            label="Score Conformité",
            value=f"{color_dot} {score:.0f} / 100",
            help="Score calculé sur les alertes (CRITICAL=-40, ERROR=-20, WARNING=-8)",
        )
        st.caption(f"Classe résistance : **{res_class}**")

    # ── Note de surperformance ───────────────────────────────────────────────
    if (
        report.compliance_with_required
        and required != "—"
        and achieved != "—"
        and achieved != required
    ):
        st.info(
            f"**Surperformance** : La formulation atteint **{achieved}** "
            f"alors que **{required}** est exigée. "
            "Opportunité d'optimisation du coût ou de l'empreinte CO₂.",
            icon="💡",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# INFO BOX
# ═══════════════════════════════════════════════════════════════════════════════

def info_box(
    title:   str,
    content: str,
    icon:    str = "ℹ️",
    color:   str = "primary",
) -> None:
    """
    Encadré d'information stylisé avec support Markdown simplifié.

    Remplace l'ancienne version qui dépendait de la bibliothèque `markdown`
    (non incluse dans les dépendances du projet). Conversion Markdown→HTML
    effectuée par `_simple_markdown_to_html()` (stdlib uniquement).

    Args:
        title  : Titre de l'encadré
        content: Contenu Markdown (gras, italique, listes supportés)
        icon   : Emoji affiché à côté du titre
        color  : Clé COLOR_PALETTE (ex: "primary", "info", "success")

    Example:
        ```python
        info_box(
            title="Mode d'emploi",
            content="**1.** Saisir la composition\n- Ciment\n- Eau\n\n**2.** Lancer la prédiction",
            icon="ℹ️",
            color="info",
        )
        ```
    """
    color_value = COLOR_PALETTE.get(color, COLOR_PALETTE["primary"])

    # Sécurité : forcer string
    if not isinstance(content, str):
        content = str(content)

    # Conversion Markdown → HTML (sans dépendance externe)
    html_content = _simple_markdown_to_html(content.strip())

    st.markdown(
        f"""
        <div style="
            background: {color_value}12;
            border-left: 4px solid {color_value};
            border-radius: 8px;
            padding: 1.2rem 1.4rem;
            margin: 1rem 0;
            line-height: 1.65;
        ">
            <div style="
                display: flex;
                align-items: center;
                gap: 0.7rem;
                margin-bottom: 0.8rem;
            ">
                <span style="font-size: 1.5rem;">{icon}</span>
                <h4 style="
                    margin: 0;
                    color: {color_value};
                    font-weight: 600;
                    font-size: 1.05rem;
                ">{html_stdlib.escape(title)}</h4>
            </div>
            <div style="color: {UI_SETTINGS['colors']['dark']}; font-size: 0.95rem;">
                {html_content}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS PUBLICS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "metric_card",
    "formulation_card",
    "alert_banner",
    "verdict_card",   # ← NOUVEAU
    "info_box",
]