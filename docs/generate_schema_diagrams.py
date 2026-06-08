"""
Generador de diagramas ERD con modelo relacional completo.
Muestra entidades, atributos (PK/FK marcados) y relaciones con cardinalidad.
Salida: schema_espn.png, schema_app.png, schema_ml.png
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

CW = 3.80   # table column width (inches)
RH = 0.295  # row height (inches)

# ── Paletas por schema ──────────────────────────────────────────────
THEME = {
    "espn": dict(H="#1a3a5c", HT="white",
                 PK="#FFF3CD", PKT="#5C4A00",
                 FK="#D4EDFF", FKT="#004085",
                 BD="white",  BDT="#1a2c3d",
                 BR="#2e6da4", LN="#2e6da4"),
    "app":  dict(H="#155724", HT="white",
                 PK="#FFF3CD", PKT="#5C4A00",
                 FK="#D4EDFF", FKT="#004085",
                 BD="white",  BDT="#1a3022",
                 BR="#28a745", LN="#1a6b30"),
    "ml":   dict(H="#2d1b5e", HT="white",
                 PK="#FFF3CD", PKT="#5C4A00",
                 FK="#D4EDFF", FKT="#004085",
                 BD="white",  BDT="#1e0e3e",
                 BR="#6a3db5", LN="#6a3db5"),
}


# ── Funciones de dibujo base ────────────────────────────────────────

def col_cy(top_y, col_idx):
    """Centro Y de la fila de datos col_idx (0-based), dado el top del tabla."""
    return top_y - (col_idx + 1.5) * RH


def compute_anchors(x, top_y, cols):
    """Precalcula {col_name: (lx, rx, cy)} sin dibujar nada."""
    anch = {}
    for i, (cn, ct, cons) in enumerate(cols):
        cy = col_cy(top_y, i)
        anch[cn] = (x, x + CW, cy)
    return anch


def draw_table(ax, x, top_y, name, cols, tk):
    """Dibuja la tabla ERD. Retorna {col_name: (lx, rx, cy)}."""
    t = THEME[tk]
    n = len(cols)
    total_h = (1 + n) * RH

    # Cuerpo
    ax.add_patch(FancyBboxPatch(
        (x, top_y - total_h), CW, n * RH,
        boxstyle="square,pad=0", lw=0, facecolor=t["BD"], zorder=3))

    # Borde exterior
    ax.add_patch(FancyBboxPatch(
        (x, top_y - total_h), CW, total_h,
        boxstyle="square,pad=0", lw=1.3,
        edgecolor=t["BR"], facecolor="none", zorder=4))

    # Cabecera
    ax.add_patch(FancyBboxPatch(
        (x, top_y - RH), CW, RH,
        boxstyle="square,pad=0", lw=0,
        facecolor=t["H"], zorder=3))
    ax.text(x + CW / 2, top_y - RH / 2, name,
            ha='center', va='center', fontsize=7.5,
            fontweight='bold', color=t["HT"], zorder=5)

    anchors = {}
    for i, (cn, ct, cons) in enumerate(cols):
        cy = col_cy(top_y, i)
        ry = top_y - (i + 2) * RH

        is_pk = cons.startswith("PK")
        is_fk = "FK" in cons
        bg  = t["PK"] if is_pk else (t["FK"] if is_fk else t["BD"])
        fgc = t["PKT"] if is_pk else (t["FKT"] if is_fk else t["BDT"])

        # Fondo de fila
        ax.add_patch(FancyBboxPatch(
            (x, ry), CW, RH,
            boxstyle="square,pad=0", lw=0, facecolor=bg, zorder=3))

        # Separador horizontal
        ax.plot([x, x + CW], [ry + RH, ry + RH],
                color=t["BR"], lw=0.3, alpha=0.4, zorder=4)

        # Icono PK / FK
        tag = "PK" if is_pk else ("FK" if is_fk else "")
        if tag:
            ax.text(x + 0.07, cy, tag, ha='left', va='center',
                    fontsize=5.2, fontweight='bold',
                    color="#AA8800" if is_pk else "#2255AA", zorder=5)
            nx = x + 0.37
        else:
            nx = x + 0.10

        # Nombre de columna
        ax.text(nx, cy, cn, ha='left', va='center',
                fontsize=6.0, color=fgc, zorder=5)

        # Tipo de dato (derecha)
        ax.text(x + CW - 0.08, cy, ct,
                ha='right', va='center',
                fontsize=5.5, color="#888888", style='italic', zorder=5)

        anchors[cn] = (x, x + CW, cy)

    return anchors


def _lookup(anchors, col):
    """Busca col en anchors, admite coincidencia parcial."""
    if col in anchors:
        return anchors[col]
    for cn, v in anchors.items():
        if col.lower() in cn.lower() or cn.lower() in col.lower():
            return v
    return list(anchors.values())[0]


def _crow_foot(ax, x, y, goes_right, color, s=0.18):
    """Pata de gallo en el extremo FK (lado 'muchos')."""
    d = -s if goes_right else s
    ax.plot([x, x + d], [y + s * 0.55, y], color=color, lw=1.4, zorder=2, solid_capstyle='round')
    ax.plot([x, x + d], [y,            y], color=color, lw=1.4, zorder=2, solid_capstyle='round')
    ax.plot([x, x + d], [y - s * 0.55, y], color=color, lw=1.4, zorder=2, solid_capstyle='round')
    # barra de cruce
    ax.plot([x + d, x + d], [y - s * 0.60, y + s * 0.60],
            color=color, lw=1.4, zorder=2, solid_capstyle='round')


def _one_bar(ax, x, y, color, s=0.14):
    """Barra simple en el extremo PK (lado 'uno')."""
    ax.plot([x, x], [y - s, y + s], color=color, lw=2.0,
            solid_capstyle='round', zorder=2)


def draw_relation(ax, fa, from_col, ta, to_col, tk,
                  route="auto", rad_override=None):
    """
    Dibuja la línea de relación FK → PK con cardinalidad.
    route: 'LR' | 'RL' | 'loop_left' | 'loop_right' | 'auto'
    """
    t = THEME[tk]
    color = t["LN"]

    fl, fr, fy = _lookup(fa, from_col)
    tl, tr, ty = _lookup(ta, to_col)

    from_cx = (fl + fr) / 2
    to_cx   = (tl + tr) / 2

    if route == "auto":
        gap = 0.15
        if fr + gap <= tl:
            route = "LR"
        elif tr + gap <= fl:
            route = "RL"
        elif from_cx <= to_cx:
            route = "loop_right"
        else:
            route = "loop_left"

    if route == "LR":
        p1x, p2x = fr, tl
        rad = 0.0 if abs(fy - ty) < 0.4 else (0.08 if fy > ty else -0.08)
        goes_right_fk = True
    elif route == "RL":
        p1x, p2x = fl, tr
        rad = 0.0 if abs(fy - ty) < 0.4 else (-0.08 if fy > ty else 0.08)
        goes_right_fk = False
    elif route == "loop_left":
        # línea sale por el lado izquierdo de ambas tablas y da la vuelta
        p1x = fl - 0.05
        p2x = tl - 0.05
        rad = 0.42 if fy > ty else -0.42
        goes_right_fk = False
    else:  # loop_right
        p1x = fr + 0.05
        p2x = tr + 0.05
        rad = -0.42 if fy > ty else 0.42
        goes_right_fk = True

    if rad_override is not None:
        rad = rad_override

    # Línea de conexión
    ax.annotate("",
        xy=(p2x, ty), xytext=(p1x, fy),
        arrowprops=dict(
            arrowstyle="-",
            connectionstyle=f"arc3,rad={rad:.3f}",
            color=color, lw=1.6, zorder=1,
        )
    )

    # Marcadores de cardinalidad
    _crow_foot(ax, p1x, fy, goes_right_fk, color)
    _one_bar(ax, p2x, ty, color)


def render_erd(tables, positions, relations, tk, title, out_path,
               fig_w, fig_h):
    """Renderiza el diagrama ERD completo."""
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(-0.5, fig_w - 0.2)
    ax.set_ylim(-0.6, fig_h - 0.2)
    ax.axis('off')
    fig.patch.set_facecolor('#F2F4F6')
    ax.set_facecolor('#F2F4F6')

    # Título
    ax.text(fig_w / 2, fig_h - 0.38, title,
            ha='center', va='top', fontsize=13,
            fontweight='bold', color='#1a1a2e', zorder=10)

    # Línea decorativa bajo el título
    ax.plot([0.3, fig_w - 0.3], [fig_h - 0.52, fig_h - 0.52],
            color='#cccccc', lw=0.8, zorder=1)

    # Leyenda
    from matplotlib.patches import Patch
    ax.legend(handles=[
        Patch(facecolor=THEME[tk]["PK"], edgecolor='#aaa', label='Clave Primaria (PK)'),
        Patch(facecolor=THEME[tk]["FK"], edgecolor='#aaa', label='Clave Foranea (FK)'),
    ], loc='lower right', fontsize=8, framealpha=0.95,
       edgecolor='#cccccc', frameon=True)

    # Anotación de cardinalidad
    ax.text(0.3, 0.25,
            "Notacion: pata de gallo = lado 'muchos' (FK)   |   barra = lado 'uno' (PK)",
            fontsize=7, color="#666666", style='italic')

    # Pre-calcular anchors
    all_anchors = {
        name: compute_anchors(positions[name][0], positions[name][1], cols)
        for name, cols in tables.items()
    }

    # Dibujar relaciones primero (quedan detrás)
    for rel in relations:
        from_t, from_c, to_t, to_c = rel[:4]
        route = rel[4] if len(rel) > 4 else "auto"
        rad_ov = rel[5] if len(rel) > 5 else None
        draw_relation(ax,
                      all_anchors[from_t], from_c,
                      all_anchors[to_t],   to_c,
                      tk, route=route, rad_override=rad_ov)

    # Dibujar tablas encima
    for name, cols in tables.items():
        x, y = positions[name]
        draw_table(ax, x, y, name, cols, tk)

    plt.savefig(out_path, dpi=180, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  [OK] {out_path}")


# ═══════════════════════════════════════════════════════════════════
# SCHEMA ESPN
# ═══════════════════════════════════════════════════════════════════

ESPN_TABLES = {
    "espn.games": [
        ("game_id",             "BIGINT",       "PK"),
        ("fecha",               "DATE",         ""),
        ("home_team",           "VARCHAR",      ""),
        ("away_team",           "VARCHAR",      ""),
        ("home_score",          "FLOAT",        ""),
        ("away_score",          "FLOAT",        ""),
        ("home_win",            "BIGINT",       ""),
        ("point_diff",          "FLOAT",        ""),
        ("home_fg_pct",         "FLOAT",        ""),
        ("away_fg_pct",         "FLOAT",        ""),
        ("home_reb / away_reb", "FLOAT",        ""),
        ("home_ast / away_ast", "FLOAT",        ""),
        ("home_team_normalized","VARCHAR",      ""),
        ("net_rating_diff",     "FLOAT",        ""),
    ],
    "espn.teams": [
        ("team_id",      "INTEGER",    "PK"),
        ("name",         "VARCHAR(100)","UNIQUE"),
        ("abbreviation", "VARCHAR(10)", "UNIQUE"),
        ("city",         "VARCHAR(50)", ""),
        ("conference",   "VARCHAR(20)", ""),
        ("division",     "VARCHAR(20)", ""),
        ("logo_url",     "VARCHAR(255)",""),
    ],
    "espn.team_stats_game": [
        ("id",                       "INTEGER", "PK"),
        ("game_id",                  "INTEGER", "FK"),
        ("team_id",                  "INTEGER", "FK"),
        ("is_home",                  "BOOLEAN", ""),
        ("points",                   "INTEGER", ""),
        ("field_goal_pct",           "FLOAT",   ""),
        ("three_point_pct",          "FLOAT",   ""),
        ("rebounds",                 "INTEGER", ""),
        ("assists / steals / blocks","INTEGER", ""),
        ("turnovers / fouls",        "INTEGER", ""),
    ],
    "espn.game_odds": [
        ("id",            "INTEGER",      "PK"),
        ("game_id",       "INTEGER",      "FK"),
        ("odds_type",     "VARCHAR(20)",  ""),
        ("odds_value",    "NUMERIC(10,4)",""),
        ("line_value",    "NUMERIC(10,2)",""),
        ("provider",      "VARCHAR(50)",  ""),
        ("snapshot_time", "TIMESTAMPTZ",  ""),
    ],
    "espn.bets": [
        ("id",              "INTEGER",      "PK"),
        ("user_id",         "INTEGER",      ""),
        ("game_id",         "INTEGER",      "FK"),
        ("bet_type_code",   "VARCHAR(20)",  "FK"),
        ("bet_status_code", "VARCHAR(20)",  "FK"),
        ("bet_amount",      "NUMERIC(10,2)",""),
        ("odds_id",         "INTEGER",      "FK"),
        ("potential_payout","NUMERIC(10,2)",""),
        ("placed_at",       "TIMESTAMPTZ",  ""),
    ],
    "espn.bet_selections": [
        ("id",               "INTEGER",      "PK"),
        ("bet_id",           "INTEGER",      "FK"),
        ("selected_team_id", "INTEGER",      "FK"),
        ("spread_value",     "NUMERIC(10,2)",""),
        ("over_under_value", "NUMERIC(10,2)",""),
        ("is_over",          "BOOLEAN",      ""),
    ],
    "espn.bet_results": [
        ("id",           "INTEGER",      "PK"),
        ("bet_id",       "INTEGER",      "FK"),
        ("actual_payout","NUMERIC(10,2)",""),
        ("result_notes", "TEXT",         ""),
        ("settled_at",   "TIMESTAMPTZ",  ""),
    ],
    "espn.bet_types": [
        ("code",        "VARCHAR(20)",  "PK"),
        ("name",        "VARCHAR(100)", ""),
        ("description", "TEXT",         ""),
    ],
    "espn.bet_statuses": [
        ("code",        "VARCHAR(20)",  "PK"),
        ("name",        "VARCHAR(100)", ""),
        ("description", "TEXT",         ""),
    ],
}

# x=col*left, y=table_top
#   Col 0  x=0.0   : bet_types, bet_statuses, bet_selections
#   Col 1  x=4.3   : bets, bet_results
#   Col 2  x=8.6   : games, team_stats_game
#   Col 3  x=12.9  : teams, game_odds
ESPN_POS = {
    "espn.games":           (8.6,  16.0),
    "espn.teams":           (12.9, 16.0),
    "espn.game_odds":       (12.9, 13.0),
    "espn.team_stats_game": (8.6,  11.5),
    "espn.bets":            (4.3,  16.0),
    "espn.bet_selections":  (0.0,  12.2),
    "espn.bet_results":     (4.3,  12.2),
    "espn.bet_types":       (0.0,  16.5),
    "espn.bet_statuses":    (0.0,  14.8),
}

ESPN_REL = [
    # team_stats_game → games  (misma col 2 → loop por la izquierda)
    ("espn.team_stats_game", "game_id",         "espn.games",        "game_id",     "loop_left",  0.38),
    # team_stats_game → teams  (col 2 → col 3, LR)
    ("espn.team_stats_game", "team_id",         "espn.teams",        "team_id",     "LR"),
    # game_odds → games  (col 3 → col 2, RL)
    ("espn.game_odds",       "game_id",         "espn.games",        "game_id",     "RL"),
    # bets → games  (col 1 → col 2, LR)
    ("espn.bets",            "game_id",         "espn.games",        "game_id",     "LR"),
    # bets → bet_types / bet_statuses  (col 1 → col 0, RL)
    ("espn.bets",            "bet_type_code",   "espn.bet_types",    "code",        "RL"),
    ("espn.bets",            "bet_status_code", "espn.bet_statuses", "code",        "RL"),
    # bets → game_odds  (col 1 → col 3, LR)
    ("espn.bets",            "odds_id",         "espn.game_odds",    "id",          "LR"),
    # bet_selections → bets  (col 0 → col 1, LR)
    ("espn.bet_selections",  "bet_id",          "espn.bets",         "id",          "LR"),
    # bet_selections → teams  (col 0 → col 3, LR)
    ("espn.bet_selections",  "selected_team_id","espn.teams",        "team_id",     "LR"),
    # bet_results → bets  (misma col 1 → loop por la izquierda)
    ("espn.bet_results",     "bet_id",          "espn.bets",         "id",          "loop_left",  0.30),
]


# ═══════════════════════════════════════════════════════════════════
# SCHEMA APP
# ═══════════════════════════════════════════════════════════════════

APP_TABLES = {
    "app.user_accounts": [
        ("id",              "INTEGER",     "PK"),
        ("username",        "VARCHAR(50)", "UNIQUE"),
        ("email",           "VARCHAR(100)","UNIQUE"),
        ("hashed_password", "VARCHAR(255)",""),
        ("is_active",       "BOOLEAN",     ""),
        ("created_at",      "TIMESTAMPTZ", ""),
    ],
    "app.clients": [
        ("id",              "INTEGER",      "PK"),
        ("user_account_id", "INTEGER",      "FK"),
        ("role_id",         "INTEGER",      "FK"),
        ("credits",         "NUMERIC(10,2)","≥0"),
        ("first_name",      "VARCHAR(100)", ""),
        ("last_name",       "VARCHAR(100)", ""),
        ("date_of_birth",   "DATE",         ""),
        ("avatar_url",      "VARCHAR(500)", ""),
    ],
    "app.administrators": [
        ("id",              "INTEGER",     "PK"),
        ("user_account_id", "INTEGER",     "FK"),
        ("role_id",         "INTEGER",     "FK"),
        ("first_name",      "VARCHAR(100)",""),
        ("last_name",       "VARCHAR(100)",""),
        ("employee_id",     "VARCHAR(50)", "UNIQUE"),
        ("department",      "VARCHAR(100)",""),
    ],
    "app.operators": [
        ("id",              "INTEGER",     "PK"),
        ("user_account_id", "INTEGER",     "FK"),
        ("role_id",         "INTEGER",     "FK"),
        ("first_name",      "VARCHAR(100)",""),
        ("last_name",       "VARCHAR(100)",""),
        ("employee_id",     "VARCHAR(50)", "UNIQUE"),
        ("shift",           "VARCHAR(50)", ""),
    ],
    "app.roles": [
        ("id",          "INTEGER",    "PK"),
        ("code",        "VARCHAR(50)","UNIQUE"),
        ("name",        "VARCHAR(100)",""),
        ("description", "TEXT",       ""),
    ],
    "app.permissions": [
        ("id",          "INTEGER",     "PK"),
        ("code",        "VARCHAR(100)","UNIQUE"),
        ("name",        "VARCHAR(200)",""),
        ("scope",       "VARCHAR(50)", ""),
        ("created_at",  "TIMESTAMPTZ", ""),
    ],
    "app.user_roles": [
        ("id",       "INTEGER", "PK"),
        ("user_id",  "INTEGER", "FK"),
        ("role_id",  "INTEGER", "FK"),
        ("is_active","BOOLEAN", ""),
    ],
    "app.role_permissions": [
        ("role_id",       "INTEGER", "FK PK"),
        ("permission_id", "INTEGER", "FK PK"),
    ],
    "app.transactions": [
        ("id",               "INTEGER", "PK"),
        ("user_id",          "INTEGER", "FK"),
        ("bet_id",           "INTEGER", ""),
        ("transaction_type", "ENUM",    ""),
        ("amount",           "FLOAT",   ""),
        ("balance_before",   "FLOAT",   ""),
        ("balance_after",    "FLOAT",   ""),
        ("created_at",       "TIMESTAMPTZ",""),
    ],
    "app.requests": [
        ("id",            "INTEGER",     "PK"),
        ("user_id",       "INTEGER",     "FK"),
        ("event_id",      "INTEGER",     ""),
        ("request_key",   "VARCHAR(255)",""),
        ("status",        "ENUM",        ""),
        ("request_metadata","TEXT(JSON)",""),
        ("created_at",    "TIMESTAMPTZ", ""),
    ],
    "app.predictions": [
        ("id",               "INTEGER", "PK"),
        ("request_id",       "INTEGER", "FK"),
        ("model_version_id", "INTEGER", "FK"),
        ("score",            "TEXT(JSON)",""),
        ("latency_ms",       "FLOAT",   ""),
        ("telemetry",        "TEXT(JSON)",""),
        ("created_at",       "TIMESTAMPTZ",""),
    ],
    "app.model_versions": [
        ("id",             "INTEGER",     "PK"),
        ("version",        "VARCHAR(50)", "UNIQUE"),
        ("is_active",      "BOOLEAN",     ""),
        ("model_metadata", "TEXT(JSON)",  ""),
        ("description",    "TEXT",        ""),
        ("created_at",     "TIMESTAMPTZ", ""),
    ],
    "app.odds_snapshots": [
        ("id",         "INTEGER",    "PK"),
        ("request_id", "INTEGER",    "FK"),
        ("taken_at",   "TIMESTAMPTZ",""),
    ],
    "app.odds_lines": [
        ("id",           "INTEGER",     "PK"),
        ("snapshot_id",  "INTEGER",     "FK"),
        ("provider_id",  "INTEGER",     "FK"),
        ("source",       "VARCHAR(50)", ""),
        ("line_code",    "VARCHAR(100)",""),
        ("price",        "NUMERIC(10,4)",""),
    ],
    "app.providers": [
        ("id",              "INTEGER",    "PK"),
        ("code",            "VARCHAR(50)","UNIQUE"),
        ("name",            "VARCHAR(100)",""),
        ("is_active",       "BOOLEAN",    ""),
        ("timeout_seconds", "INTEGER",    ""),
        ("max_retries",     "INTEGER",    ""),
        ("created_at",      "TIMESTAMPTZ",""),
    ],
    "app.outbox": [
        ("id",           "INTEGER",    "PK"),
        ("topic",        "VARCHAR(100)",""),
        ("payload",      "TEXT(JSON)", ""),
        ("created_at",   "TIMESTAMPTZ",""),
        ("published_at", "TIMESTAMPTZ","NULL=pendiente"),
    ],
    "app.audit_log": [
        ("id",             "INTEGER",    "PK"),
        ("actor_user_id",  "INTEGER",    "FK"),
        ("action",         "VARCHAR(100)",""),
        ("resource_type",  "VARCHAR(50)", ""),
        ("resource_id",    "INTEGER",     ""),
        ("before / after", "TEXT(JSON)",  ""),
        ("created_at",     "TIMESTAMPTZ", ""),
    ],
    "app.user_sessions": [
        ("id",              "INTEGER",     "PK"),
        ("user_account_id", "INTEGER",     "FK"),
        ("token_hash",      "VARCHAR(64)", ""),
        ("device_info",     "VARCHAR(255)",""),
        ("is_active",       "BOOLEAN",     ""),
        ("expires_at",      "TIMESTAMPTZ", ""),
        ("revoked_at",      "TIMESTAMPTZ", ""),
    ],
    "app.user_two_factor": [
        ("id",              "INTEGER",    "PK"),
        ("user_account_id", "INTEGER",    "FK"),
        ("secret",          "VARCHAR(32)",""),
        ("is_enabled",      "BOOLEAN",    ""),
        ("backup_codes",    "TEXT(JSON)", ""),
        ("enabled_at",      "TIMESTAMPTZ",""),
    ],
    "app.idempotency_keys": [
        ("id",            "INTEGER",     "PK"),
        ("request_key",   "VARCHAR(255)","UNIQUE"),
        ("request_id",    "INTEGER",     ""),
        ("response_data", "TEXT(JSON)",  ""),
        ("expires_at",    "TIMESTAMPTZ", ""),
    ],
}

# Layout: 4 columnas
# Col 0 (x=0.0):   tablas satélite izq de user_accounts
# Col 1 (x=4.35):  user_accounts, transactions, user_roles
# Col 2 (x=8.70):  perfiles (clients, admin, operators), RBAC
# Col 3 (x=13.05): pipeline de requests/predicciones
# Col 4 (x=17.40): odds y providers
APP_POS = {
    # Col 0
    "app.user_two_factor":   (0.0,   15.0),
    "app.user_sessions":     (0.0,   12.6),
    "app.audit_log":         (0.0,    9.9),
    "app.outbox":            (0.0,    7.2),
    "app.idempotency_keys":  (0.0,    5.0),
    # Col 1
    "app.user_accounts":     (4.35,  15.0),
    "app.transactions":      (4.35,  12.6),
    "app.user_roles":        (4.35,   9.6),
    # Col 2
    "app.clients":           (8.70,  15.0),
    "app.administrators":    (8.70,  12.3),
    "app.operators":         (8.70,   9.6),
    "app.roles":             (8.70,   6.9),
    "app.role_permissions":  (8.70,   5.1),
    "app.permissions":       (8.70,   3.6),
    # Col 3
    "app.requests":          (13.05, 15.0),
    "app.predictions":       (13.05, 12.3),
    "app.model_versions":    (13.05,  9.6),
    "app.odds_snapshots":    (13.05,  7.3),
    # Col 4
    "app.providers":         (17.40, 15.0),
    "app.odds_lines":        (17.40, 12.7),
}

APP_REL = [
    # user_accounts → perfiles (col1 → col2, LR)
    ("app.clients",        "user_account_id", "app.user_accounts", "id",            "RL"),
    ("app.administrators", "user_account_id", "app.user_accounts", "id",            "RL"),
    ("app.operators",      "user_account_id", "app.user_accounts", "id",            "RL"),
    # user_accounts → satélites (col0 → col1, LR)
    ("app.user_two_factor","user_account_id", "app.user_accounts", "id",            "LR"),
    ("app.user_sessions",  "user_account_id", "app.user_accounts", "id",            "LR"),
    ("app.audit_log",      "actor_user_id",   "app.user_accounts", "id",            "LR"),
    # transactions → user_accounts (col1 → col1, loop)
    ("app.transactions",   "user_id",         "app.user_accounts", "id",            "loop_left", 0.35),
    # user_roles (col1 → col1/col2)
    ("app.user_roles",     "user_id",         "app.user_accounts", "id",            "loop_left", 0.30),
    ("app.user_roles",     "role_id",         "app.roles",         "id",            "LR"),
    # RBAC (col2 interno)
    ("app.clients",        "role_id",         "app.roles",         "id",            "loop_right", -0.28),
    ("app.administrators", "role_id",         "app.roles",         "id",            "loop_right", -0.22),
    ("app.operators",      "role_id",         "app.roles",         "id",            "loop_right", -0.16),
    ("app.role_permissions","role_id",        "app.roles",         "id",            "loop_right", -0.25),
    ("app.role_permissions","permission_id",  "app.permissions",   "id",            "loop_right", -0.25),
    # requests → user_accounts (col3 → col1)
    ("app.requests",       "user_id",         "app.user_accounts", "id",            "RL"),
    # predictions pipeline (col3 interno)
    ("app.predictions",    "request_id",      "app.requests",      "id",            "loop_right", -0.28),
    ("app.predictions",    "model_version_id","app.model_versions","id",            "loop_right", -0.28),
    ("app.odds_snapshots", "request_id",      "app.requests",      "id",            "loop_right", -0.22),
    # odds (col4 → col3)
    ("app.odds_lines",     "snapshot_id",     "app.odds_snapshots","id",            "RL"),
    ("app.odds_lines",     "provider_id",     "app.providers",     "id",            "loop_right", -0.30),
]


# ═══════════════════════════════════════════════════════════════════
# SCHEMA ML
# ═══════════════════════════════════════════════════════════════════

ML_TABLES = {
    "ml.ml_ready_games": [
        ("game_id",                      "BIGINT",  "PK"),
        ("fecha",                        "DATE",    ""),
        ("season",                       "VARCHAR", ""),
        ("home_team_id",                 "INTEGER", ""),
        ("away_team_id",                 "INTEGER", ""),
        ("home_score / away_score",      "FLOAT",   ""),
        ("home_win",                     "BOOLEAN", "TARGET"),
        ("home_ppg_last5 / away_ppg_last5",   "FLOAT",""),
        ("home_ppg_last10 / away_ppg_last10", "FLOAT",""),
        ("home_net_rating_last5/10",     "FLOAT",   ""),
        ("away_net_rating_last5/10",     "FLOAT",   ""),
        ("home_rest_days / away_rest_days",   "FLOAT",""),
        ("home_b2b / away_b2b",          "BOOLEAN", ""),
        ("home_injuries_count",          "INTEGER", ""),
        ("away_injuries_count",          "INTEGER", ""),
        ("home_win_rate_last10",         "FLOAT",   ""),
        ("away_win_rate_last10",         "FLOAT",   ""),
        ("ppg_diff",                     "FLOAT",   "home-away"),
        ("net_rating_diff_rolling",      "FLOAT",   "home-away"),
        ("rest_days_diff",               "FLOAT",   "home-away"),
        ("injuries_diff",                "FLOAT",   "home-away"),
        ("pace_diff",                    "FLOAT",   "v2.0.0"),
        ("off_rating_diff",              "FLOAT",   "v2.0.0"),
        ("def_rating_diff",              "FLOAT",   "v2.0.0"),
        ("reb_rolling_diff",             "FLOAT",   "v2.0.0"),
        ("ast_rolling_diff",             "FLOAT",   "v2.0.0"),
        ("tov_rolling_diff",             "FLOAT",   "v2.0.0"),
        ("win_rate_diff",                "FLOAT",   "v2.0.0"),
        ("efg_pct_diff",                 "FLOAT",   "v2.0.0"),
        ("tov_rate_diff",                "FLOAT",   "v2.0.0"),
        ("oreb_pct_diff / dreb_pct_diff","FLOAT",   "v2.0.0"),
        ("elo_diff",                     "FLOAT",   "v2.0.0"),
        ("streak_diff",                  "FLOAT",   "v2.0.0"),
        ("h2h_home_advantage",           "FLOAT",   "v2.0.0"),
        ("home_elo / away_elo",          "FLOAT",   "v2.0.0"),
        ("home_streak / away_streak",    "FLOAT",   "v2.0.0"),
        ("implied_prob_home",            "FLOAT",   "~1% cobertura"),
        ("implied_prob_away",            "FLOAT",   "~1% cobertura"),
    ],
}

ML_POS = {
    "ml.ml_ready_games": (1.0, 13.8),
}

ML_REL = []  # tabla única, sin relaciones


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Generando diagramas ERD relacionales...")

    # ESPN
    render_erd(
        ESPN_TABLES, ESPN_POS, ESPN_REL, "espn",
        title="Schema ESPN — Modelo Relacional (Datos de Scraping)",
        out_path=os.path.join(OUTPUT_DIR, "schema_espn.png"),
        fig_w=17.5, fig_h=18.0,
    )

    # APP
    render_erd(
        APP_TABLES, APP_POS, APP_REL, "app",
        title="Schema APP — Modelo Relacional (Aplicacion, Seguridad y Auditoria)",
        out_path=os.path.join(OUTPUT_DIR, "schema_app.png"),
        fig_w=22.5, fig_h=16.0,
    )

    # ML
    render_erd(
        ML_TABLES, ML_POS, ML_REL, "ml",
        title="Schema ML — Tabla ml_ready_games (Feature Store de Entrenamiento)",
        out_path=os.path.join(OUTPUT_DIR, "schema_ml.png"),
        fig_w=7.0, fig_h=14.5,
    )

    print("\nDiagramas guardados en:", OUTPUT_DIR)
