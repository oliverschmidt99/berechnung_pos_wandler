import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os

# --- 1. Daten aus externen CSV-Dateien laden ---
DATA_DIR = "data"
start_df = pd.read_csv(os.path.join(DATA_DIR, "1_startpositionen.csv")).set_index(
    "Strom"
)
spielraum_df = pd.read_csv(os.path.join(DATA_DIR, "2_spielraum.csv"))
bewegungen_df = pd.read_csv(os.path.join(DATA_DIR, "3_bewegungen.csv"))
schrittweite_df = pd.read_csv(os.path.join(DATA_DIR, "4_schrittweiten.csv")).set_index(
    "Strom"
)
wandler_df = pd.read_csv(os.path.join(DATA_DIR, "5_wandler_abmessungen.csv")).set_index(
    "Strom"
)

# Mapping für Himmelsrichtungen
direction_map = {
    "↑ Norden": np.array([0, 1]),
    "→ Osten": np.array([1, 0]),
    "↓ Süden": np.array([0, -1]),
    "← Westen": np.array([-1, 0]),
    "↗ Nordosten": np.array([1, 1]),
    "↘ Südosten": np.array([1, -1]),
    "↙ Südwesten": np.array([-1, -1]),
    "↖ Nordwesten": np.array([-1, 1]),
}
# Vektoren normalisieren
for key, vec in direction_map.items():
    norm = np.linalg.norm(vec)
    if norm > 0:
        direction_map[key] = vec / norm

# --- 2. Berechnungs- und Kollisionslogik ---
ergebnisse = []
sicherheitsabstand = 20.0
grenzen = spielraum_df.iloc[0]

for strom in start_df.index:
    start_pos, schritte, wandler_dims = (
        start_df.loc[strom],
        schrittweite_df.loc[strom],
        wandler_df.loc[strom],
    )
    for index, bewegung in bewegungen_df.iterrows():
        pos_gruppe = bewegung["PosGruppe"]
        pos_num = int(pos_gruppe[-1])
        schritt = schritte[f"Pos{pos_num}"]
        zeilen_ergebnis = {"Strom": strom, "PosGruppe": pos_gruppe}
        for i in range(1, 4):
            richtung = bewegung[f"L{i}"]
            start_vektor = np.array(
                [
                    start_pos[f"x{i}_in"] + start_pos["X"],
                    start_pos[f"y{i}_in"] + start_pos["Y"],
                ]
            )
            end_vektor = start_vektor + (
                direction_map.get(richtung, np.array([0, 0])) * schritt
            )
            zeilen_ergebnis[f"x{i}_res"], zeilen_ergebnis[f"y{i}_res"] = (
                end_vektor[0],
                end_vektor[1],
            )
            x_min, x_max = (
                end_vektor[0] - wandler_dims["Breite"] / 2,
                end_vektor[0] + wandler_dims["Breite"] / 2,
            )
            y_min, y_max = (
                end_vektor[1] - wandler_dims["Hoehe"] / 2,
                end_vektor[1] + wandler_dims["Hoehe"] / 2,
            )
            kollision = not (
                grenzen["-maxX"] + sicherheitsabstand <= x_min
                and x_max <= grenzen["+maxX"] - sicherheitsabstand
                and grenzen["-maxY"] + sicherheitsabstand <= y_min
                and y_max <= grenzen["+maxY"] - sicherheitsabstand
            )
            zeilen_ergebnis[f"Kollision_L{i}"] = "Kollision" if kollision else "OK"
        ergebnisse.append(zeilen_ergebnis)

# --- 3. Ergebnisse in CSV-Datei speichern ---
ergebnis_df = pd.DataFrame(ergebnisse)
ergebnis_df.to_csv("positionsberechnung_ergebnis.csv", index=False)
print(
    "Berechnung abgeschlossen. Ergebnisse in 'positionsberechnung_ergebnis.csv' gespeichert."
)

# --- 4. Grafische Darstellung mit Plotly ---
fig = go.Figure()
stromstaerken = sorted(ergebnis_df["Strom"].unique())
strom_pro_spur = []

for strom in stromstaerken:
    df_strom = ergebnis_df[ergebnis_df["Strom"] == strom]
    startpos = start_df.loc[strom]
    for i in range(1, 4):
        # *** HIER IST DER FIX ***
        # Wir wandeln das Ergebnis in einen echten Python-Boolean um
        show_legend_flag = bool(strom == stromstaerken[0])
        fig.add_trace(
            go.Scatter(
                x=[startpos[f"x{i}_in"] + startpos["X"]],
                y=[startpos[f"y{i}_in"] + startpos["Y"]],
                mode="markers",
                marker=dict(color="blue", size=12, symbol="x"),
                name=f"Start L{i}",
                legendgroup=f"L{i}",
                legendrank=i,
                showlegend=show_legend_flag,
            )
        )
        strom_pro_spur.append(strom)
    for index, row in df_strom.iterrows():
        for i in range(1, 4):
            farbe = "green" if row[f"Kollision_L{i}"] == "OK" else "red"
            fig.add_trace(
                go.Scatter(
                    x=[row[f"x{i}_res"]],
                    y=[row[f"y{i}_res"]],
                    mode="markers+text",
                    marker=dict(color=farbe, size=15),
                    text=row["PosGruppe"],
                    textposition="top center",
                    showlegend=False,
                    hoverinfo="text",
                    hovertext=f"Leiter: L{i}<br>Pos: {row['PosGruppe']}<br>X: {row[f'x{i}_res']:.1f}<br>Y: {row[f'y{i}_res']:.1f}<br>Status: {row[f'Kollision_L{i}']}",
                )
            )
            strom_pro_spur.append(strom)

# Dropdown-Menü
buttons = []
for strom_button in stromstaerken:
    visibility = [s == strom_button for s in strom_pro_spur]
    buttons.append(
        dict(
            label=f"{strom_button}A",
            method="update",
            args=[
                {"visible": visibility},
                {"title": f"Positionen für {strom_button}A"},
            ],
        )
    )

fig.update_layout(
    updatemenus=[
        dict(active=0, buttons=buttons, x=0.01, xanchor="left", y=1.1, yanchor="top")
    ],
    title_text=f"Positionen für {stromstaerken[0]}A",
    xaxis=dict(
        scaleanchor="y",
        scaleratio=1,
        range=[grenzen["-maxX"] - 50, grenzen["+maxX"] + 50],
    ),
    yaxis=dict(
        title="Y-Position (mm)", range=[grenzen["-maxY"] - 50, grenzen["+maxY"] + 50]
    ),
    xaxis_title="X-Position (mm)",
    legend_title="Legende",
    width=900,
    height=700,
    template="plotly_white",
)

# Initiale Sichtbarkeit
initial_visibility = [s == stromstaerken[0] for s in strom_pro_spur]
for i, trace in enumerate(fig.data):
    trace.visible = initial_visibility[i]

# Shapes (Grenzen)
fig.add_shape(
    type="rect",
    x0=grenzen["-maxX"],
    y0=grenzen["-maxY"],
    x1=grenzen["+maxX"],
    y1=grenzen["+maxY"],
    line=dict(color="black", width=2),
    fillcolor="lightgrey",
    layer="below",
    opacity=0.3,
)
fig.add_shape(
    type="rect",
    x0=grenzen["-maxX"] + sicherheitsabstand,
    y0=grenzen["-maxY"] + sicherheitsabstand,
    x1=grenzen["+maxX"] - sicherheitsabstand,
    y1=grenzen["+maxY"] - sicherheitsabstand,
    line=dict(color="red", width=2, dash="dash"),
    layer="below",
)

fig.write_html("visualisierung_positionen.html")
print("Interaktive Visualisierung in 'visualisierung_positionen.html' gespeichert.")
