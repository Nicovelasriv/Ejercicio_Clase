"""
Mapa país -> región geográfica, usado SÓLO como apoyo visual (color de las
burbujas), al estilo de las visualizaciones de Hans Rosling / Gapminder.

IMPORTANTE (transparencia metodológica):
  - La región NO es una variable de la base World Happiness Report.
  - Es un atributo geográfico externo, verificable, agregado únicamente para
    agrupar visualmente las burbujas por color. No se usa en ningún cálculo
    ni en ninguna afirmación cuantitativa del análisis.
  - La agrupación sigue las regiones del Banco Mundial, consolidadas en 6
    grupos (se unen América del Norte y América Latina y el Caribe en
    "Américas" para mantener una paleta legible).

La función ``validar_cobertura`` garantiza que cada país de la base tenga
región asignada; si falta alguno, el programa se detiene (no se asigna una
categoría "Otros" silenciosa que pueda confundir la lectura).
"""

from __future__ import annotations

# Orden de las regiones = orden de la leyenda.
REGIONES = [
    "Europa y Asia Central",
    "Américas",
    "Oriente Medio y Norte de África",
    "África Subsahariana",
    "Asia Oriental y Pacífico",
    "Asia Meridional",
]

PAIS_A_REGION = {
    # --- Europa y Asia Central -------------------------------------------
    **{p: "Europa y Asia Central" for p in [
        "Albania", "Armenia", "Austria", "Azerbaijan", "Belarus", "Belgium",
        "Bosnia and Herzegovina", "Bulgaria", "Croatia", "Cyprus",
        "Czech Republic", "Denmark", "Estonia", "Finland", "France", "Georgia",
        "Germany", "Greece", "Hungary", "Iceland", "Ireland", "Italy",
        "Kazakhstan", "Kosovo", "Kyrgyzstan", "Latvia", "Lithuania",
        "Luxembourg", "Malta", "Moldova", "Montenegro", "Netherlands",
        "North Cyprus", "North Macedonia", "Norway", "Poland", "Portugal",
        "Romania", "Russia", "Serbia", "Slovakia", "Slovenia", "Spain",
        "Sweden", "Switzerland", "Tajikistan", "Turkey", "Turkmenistan",
        "Ukraine", "United Kingdom", "Uzbekistan",
    ]},
    # --- Américas (Norte + Latinoamérica y el Caribe) --------------------
    **{p: "Américas" for p in [
        "Argentina", "Belize", "Bolivia", "Brazil", "Canada", "Chile",
        "Colombia", "Costa Rica", "Cuba", "Dominican Republic", "Ecuador",
        "El Salvador", "Guatemala", "Guyana", "Haiti", "Honduras", "Jamaica",
        "Mexico", "Nicaragua", "Panama", "Paraguay", "Peru", "Suriname",
        "Trinidad and Tobago", "United States", "Uruguay", "Venezuela",
    ]},
    # --- Oriente Medio y Norte de África ---------------------------------
    **{p: "Oriente Medio y Norte de África" for p in [
        "Algeria", "Bahrain", "Djibouti", "Egypt", "Iran", "Iraq", "Israel",
        "Jordan", "Kuwait", "Lebanon", "Libya", "Morocco", "Oman",
        "Palestinian Territories", "Qatar", "Saudi Arabia", "Syria", "Tunisia",
        "United Arab Emirates", "Yemen",
    ]},
    # --- África Subsahariana ---------------------------------------------
    **{p: "África Subsahariana" for p in [
        "Angola", "Benin", "Botswana", "Burkina Faso", "Burundi", "Cameroon",
        "Central African Republic", "Chad", "Comoros", "Congo (Brazzaville)",
        "Congo (Kinshasa)", "Ethiopia", "Gabon", "Gambia", "Ghana", "Guinea",
        "Ivory Coast", "Kenya", "Lesotho", "Liberia", "Madagascar", "Malawi",
        "Mali", "Mauritania", "Mauritius", "Mozambique", "Namibia", "Niger",
        "Nigeria", "Rwanda", "Senegal", "Sierra Leone", "Somalia",
        "Somaliland region", "South Africa", "South Sudan", "Sudan",
        "Swaziland", "Tanzania", "Togo", "Uganda", "Zambia", "Zimbabwe",
    ]},
    # --- Asia Oriental y Pacífico ----------------------------------------
    **{p: "Asia Oriental y Pacífico" for p in [
        "Australia", "Cambodia", "China", "Hong Kong S.A.R. of China",
        "Indonesia", "Japan", "Laos", "Malaysia", "Mongolia", "Myanmar",
        "New Zealand", "Philippines", "Singapore", "South Korea",
        "Taiwan Province of China", "Thailand", "Vietnam",
    ]},
    # --- Asia Meridional -------------------------------------------------
    **{p: "Asia Meridional" for p in [
        "Afghanistan", "Bangladesh", "Bhutan", "India", "Maldives", "Nepal",
        "Pakistan", "Sri Lanka",
    ]},
}

# Paleta cualitativa accesible (buen contraste entre categorías y en B/N).
# Basada en la paleta "Okabe-Ito", diseñada para daltonismo.
COLOR_REGION = {
    "Europa y Asia Central":            "#0072B2",  # azul
    "Américas":                         "#D55E00",  # naranja-rojo
    "Oriente Medio y Norte de África":  "#E69F00",  # ámbar
    "África Subsahariana":              "#009E73",  # verde
    "Asia Oriental y Pacífico":         "#CC79A7",  # rosa-morado
    "Asia Meridional":                  "#56B4E9",  # celeste
}


def region_de(pais: str) -> str:
    """Devuelve la región de un país (KeyError si no está mapeado)."""
    return PAIS_A_REGION[pais]


def validar_cobertura(paises) -> None:
    """Verifica que todos los países tengan región; aborta si falta alguno."""
    faltan = sorted({p for p in paises if p not in PAIS_A_REGION})
    if faltan:
        raise KeyError(
            "Países sin región asignada en regiones.py "
            f"(agrégalos al mapa): {faltan}"
        )
