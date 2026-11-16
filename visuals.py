# visuals.py
# Draws the network map with Plotly.
#   red arrows / red circles  = the attacker's path
#   green circles             = defended nodes
#   orange circle = start (Internet), purple circle = target (Database)

import plotly.graph_objects as go

# Where each node is drawn on the picture: (x, y)
POSITIONS = {
    "Internet": (0, 3),
    "Firewall": (1, 5), "Mail Server": (1, 3.5), "VPN": (1, 2), "WiFi": (1, 0.5),
    "Web Server": (2, 5.6), "Student Portal": (2, 4.4), "Staff PC": (2, 3),
    "Lab PCs": (2, 1.5), "Printer": (2, 0.3),
    "App Server": (3, 5), "Admin PC": (3, 3.6), "File Server": (3, 1.2),
    "Backup Server": (4, 2.2),
    "Database": (5, 3.8),
}

GRAY = "#8a8f98"
RED = "#e63946"
GREEN = "#2a9d4f"
ORANGE = "#f4a261"
PURPLE = "#7b2cbf"
BLUE = "#4a7fd4"


def draw_network(graph, attack_path=None, defended=None, compromised=None):
    """Return a Plotly figure of the network.
    attack_path : list of nodes the attacker walks through (drawn in red)
    defended    : list of defended nodes (drawn in green)
    compromised : list of hacked nodes (drawn in orange-red)"""
    if attack_path is None:
        attack_path = []
    if defended is None:
        defended = []
    if compromised is None:
        compromised = []

    # edges that belong to the attack path
    path_edges = []
    for i in range(len(attack_path) - 1):
        path_edges.append((attack_path[i], attack_path[i + 1]))

    fig = go.Figure()

    # 1. Draw every connection as an arrow
    label_x = []
    label_y = []
    label_text = []
    for a in graph:
        for b in graph[a]:
            x0, y0 = POSITIONS[a]
            x1, y1 = POSITIONS[b]
            on_path = (a, b) in path_edges
            fig.add_annotation(x=x1, y=y1, ax=x0, ay=y0,
                               xref="x", yref="y", axref="x", ayref="y",
                               showarrow=True, arrowhead=2, arrowsize=1.1,
                               arrowwidth=4 if on_path else 1.3,
                               arrowcolor=RED if on_path else GRAY,
                               standoff=16, startstandoff=16)
            label_x.append((x0 + x1) / 2)
            label_y.append((y0 + y1) / 2)
            label_text.append(str(graph[a][b]))

    # difficulty numbers in the middle of each arrow
    fig.add_trace(go.Scatter(x=label_x, y=label_y, mode="text", text=label_text,
                             textfont=dict(size=10, color=GRAY),
                             hoverinfo="skip", showlegend=False))

    # 2. Draw the nodes
    node_x = []
    node_y = []
    node_color = []
    node_line = []
    node_names = []
    for name in graph:
        x, y = POSITIONS[name]
        node_x.append(x)
        node_y.append(y)
        node_names.append(name)
        if name in defended:
            color = GREEN
        elif name in compromised:
            color = "#ff7b00"
        elif name == "Internet":
            color = ORANGE
        elif name == "Database":
            color = PURPLE
        else:
            color = BLUE
        node_color.append(color)
        if name in attack_path:
            node_line.append(RED)
        else:
            node_line.append("white")

    fig.add_trace(go.Scatter(
        x=node_x, y=node_y, mode="markers+text", text=node_names,
        textposition="bottom center", textfont=dict(size=11),
        marker=dict(size=30, color=node_color,
                    line=dict(width=4, color=node_line)),
        hovertext=node_names, hoverinfo="text", showlegend=False))

    # 3. Legend (small dummy points, only used to show the colour meaning)
    legend_items = [("Start", ORANGE), ("Target", PURPLE), ("Normal node", BLUE),
                    ("Defended", GREEN), ("Hacked", "#ff7b00")]
    for text, color in legend_items:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=text,
                                 marker=dict(size=12, color=color)))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name="Attack path",
                             line=dict(width=4, color=RED)))

    fig.update_layout(
        height=520, margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(visible=False, range=[-0.5, 5.5]),
        yaxis=dict(visible=False, range=[-0.4, 6.3]),
        legend=dict(orientation="h", yanchor="bottom", y=-0.08, xanchor="center", x=0.5))
    return fig