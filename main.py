import os
import traceback
import flet as ft
from nba_data import search_player_by_name, get_player_9cat_stats, season_to_espn_year
from evaluator import evaluate_trade

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# Put your image at <project>/assets/bg.jpg (or set a direct https:// URL).
# Set to "" (empty string) to disable the background image anytime.
BACKGROUND_IMAGE_SRC = ""


def main(page: ft.Page):
    page.title = "NBA 9-Cat Trade Evaluator"
    page.theme_mode = ft.ThemeMode.DARK

    # Zero page padding so the background image fills edge-to-edge
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    team_a_players = []
    team_b_players = []

    header = ft.Container(
        content=ft.Text("🏀 NBA 9-Cats Trade Evaluator", size=24, weight=ft.FontWeight.BOLD),
        margin=ft.Margin.only(top=10, bottom=10),
    )

    season_dropdown = ft.Dropdown(
        label="Select Season",
        value="2026-27",
        bgcolor=ft.Colors.with_opacity(0.85, ft.Colors.GREY_900),
        options=[
            ft.dropdown.Option("2024-25"),
            ft.dropdown.Option("2025-26"),
            ft.dropdown.Option("2026-27"),
        ],
    )

    top_bar = ft.Container(
        content=ft.Column([
            header,
            season_dropdown,
        ], spacing=10),
        padding=ft.Padding.only(top=5, bottom=10),
    )

    list_a = ft.Column(spacing=10)
    list_b = ft.Column(spacing=10)

    def show_toast(msg: str):
        print(f"[UI TOAST] {msg}", flush=True)
        page.snack_bar = ft.SnackBar(ft.Text(str(msg)))
        page.snack_bar.open = True
        page.update()

    def build_suggestions(query: str):
        matches = search_player_by_name(
            query,
            max_results=10,
            season=season_dropdown.value or "2026-27",
        )
        return [
            ft.AutoCompleteSuggestion(key=m["full_name"], value=m["full_name"])
            for m in (matches[:10] if matches else [])
        ]

    def handle_search_a(e):
        query = (e.data or "").strip()
        if len(query) < 2:
            autocomplete_a.suggestions = []
            autocomplete_a.update()
            return
        autocomplete_a.suggestions = build_suggestions(query)
        autocomplete_a.update()

    def handle_search_b(e):
        query = (e.data or "").strip()
        if len(query) < 2:
            autocomplete_b.suggestions = []
            autocomplete_b.update()
            return
        autocomplete_b.suggestions = build_suggestions(query)
        autocomplete_b.update()

    def on_select_a(e: ft.AutoCompleteSelectEvent):
        input_a.value = e.selection.value
        autocomplete_a.update()

    def on_select_b(e: ft.AutoCompleteSelectEvent):
        input_b.value = e.selection.value
        autocomplete_b.update()

    input_a = ft.TextField(
        label="Give Player Name",
        hint_text="e.g. Stephen Curry",
        expand=True,
        bgcolor=ft.Colors.with_opacity(0.75, ft.Colors.GREY_900),
    )
    input_b = ft.TextField(
        label="Receive Player Name",
        hint_text="e.g. Seth Curry",
        expand=True,
        bgcolor=ft.Colors.with_opacity(0.75, ft.Colors.GREY_900),
    )

    autocomplete_a = ft.AutoComplete(
        on_change=handle_search_a,
        on_select=on_select_a,
        suggestions=[],
        expand=True,
    )
    autocomplete_a.content = input_a

    autocomplete_b = ft.AutoComplete(
        on_change=handle_search_b,
        on_select=on_select_b,
        suggestions=[],
        expand=True,
    )
    autocomplete_b.content = input_b

    result_column = ft.Column([
        ft.Text("Add up to 10 players on each side to evaluate.", size=16)
    ])

    result_card = ft.Container(
        content=result_column,
        padding=15,
        border_radius=8,
        bgcolor=ft.Colors.with_opacity(0.85, ft.Colors.GREY_900),
    )

    def remove_player(player_data, team: str):
        target_list = team_a_players if team == "A" else team_b_players
        if player_data in target_list:
            target_list.remove(player_data)
        render_team_list(team)
        page.update()

    def clear_all(e):
        team_a_players.clear()
        team_b_players.clear()
        render_team_list("A")
        render_team_list("B")

        input_a.value = ""
        input_b.value = ""
        autocomplete_a.suggestions = []
        autocomplete_b.suggestions = []
        autocomplete_a.update()
        autocomplete_b.update()

        result_column.controls = [
            ft.Text("Add up to 10 players on each side to evaluate.", size=16)
        ]

        show_toast("Cleared all players from both teams!")
        page.update()

    def render_team_list(team: str):
        target_list = team_a_players if team == "A" else team_b_players
        target_view = list_a if team == "A" else list_b

        target_view.controls.clear()
        for p in target_list:
            card = ft.Container(
                content=ft.Row([
                    ft.Column([
                        ft.Text(
                            f"• {p['name']} ({p.get('season', season_dropdown.value)})",
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            f"PTS: {p.get('pts',0)} | REB: {p.get('reb',0)} | AST: {p.get('ast',0)} | "
                            f"STL: {p.get('stl',0)} | BLK: {p.get('blk',0)} | 3PM: {p.get('fg3m',0)} | "
                            f"FG%: {p.get('fg_pct',0)} | FT%: {p.get('ft_pct',0)} | TO: {p.get('tov',0)}",
                            size=12,
                        ),
                    ], expand=True),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINED,
                        icon_color=ft.Colors.RED_400,
                        tooltip="Remove Player",
                        on_click=lambda e, player=p, t=team: remove_player(player, t),
                    ),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=8,
                bgcolor=ft.Colors.with_opacity(0.75, ft.Colors.GREY_900),
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                border_radius=5,
            )
            target_view.controls.append(card)

    def add_player(e, team: str):
        autocomplete = autocomplete_a if team == "A" else autocomplete_b
        input_field = input_a if team == "A" else input_b
        target_list = team_a_players if team == "A" else team_b_players

        if len(target_list) >= 10:
            show_toast("Maximum 10 players per side!")
            return

        player_name = (input_field.value or autocomplete.value or "").strip()
        if not player_name:
            return

        selected_season = season_dropdown.value or "2026-27"
        espn_yr = season_to_espn_year(selected_season)
        show_toast(f"Searching stats for '{player_name}' ({selected_season} / ESPN {espn_yr})...")

        matches = search_player_by_name(player_name, max_results=10, season=selected_season)
        if not matches:
            show_toast(f"Player '{player_name}' not found on ESPN roster.")
            return

        player_info = matches[0]
        stats = get_player_9cat_stats(player_info["id"], season=selected_season)

        if not stats:
            show_toast(f"No stats found for {player_info['full_name']} in {selected_season}")
            return

        player_data = {"name": player_info["full_name"], "season": selected_season, **stats}
        target_list.append(player_data)

        autocomplete.value = ""
        autocomplete.suggestions = []
        input_field.value = ""

        render_team_list(team)
        show_toast(f"Added {player_info['full_name']} ({selected_season})!")
        page.update()

    def handle_eval(e):
        if not team_a_players or not team_b_players:
            show_toast("Please add players to BOTH sides before evaluating.")
            return

        try:
            res = evaluate_trade(team_a_players, team_b_players)

            team_a_str = ", ".join(
                [f"{p['name']} ({p['total']:+.2f})" for p in res.get("team_a_players", [])]
            )
            team_b_str = ", ".join(
                [f"{p['name']} ({p['total']:+.2f})" for p in res.get("team_b_players", [])]
            )

            eval_controls = [
                ft.Text("📊 Trade Comparison Summary (9-Cat Z-Scores)", size=20, weight=ft.FontWeight.BOLD),
                ft.Text(
                    f"Team A Gives ({len(team_a_players)} player(s)): {team_a_str}",
                    size=14,
                    weight=ft.FontWeight.W_500,
                ),
                ft.Text(
                    f"Team B Gives ({len(team_b_players)} player(s)): {team_b_str}",
                    size=14,
                    weight=ft.FontWeight.W_500,
                ),
                ft.Divider(),
                ft.Text(
                    f"Verdict: {res.get('status', 'Evaluated')}",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=res.get("status_color", ft.Colors.WHITE),
                ),
                ft.Text(f"Team A Total Z-Score: {res.get('team_a_score', 0):+.2f}"),
                ft.Text(f"Team B Total Z-Score: {res.get('team_b_score', 0):+.2f}"),
                ft.Text(f"Net Z-Score Difference: {res.get('difference', 0):+.2f}"),
            ]

            result_column.controls = eval_controls
            page.update()

        except Exception as err:
            print("Evaluation Error Traceback:", flush=True)
            traceback.print_exc()
            show_toast(f"Eval Error: {err}")

    input_a.on_submit = lambda e: add_player(e, "A")
    input_b.on_submit = lambda e: add_player(e, "B")

    bg_src = (BACKGROUND_IMAGE_SRC or "").strip()
    is_url = bg_src.startswith(("http://", "https://"))
    has_local_asset = bool(bg_src) and not is_url and os.path.exists(os.path.join(ASSETS_DIR, bg_src))
    use_bg_image = is_url or has_local_asset

    bg_image = (
        ft.DecorationImage(
            src=bg_src,
            fit=ft.BoxFit.COVER,
        )
        if use_bg_image
        else None
    )

    page.add(
        ft.Container(
            expand=True,
            bgcolor=ft.Colors.with_opacity(0.65, ft.Colors.BLACK) if use_bg_image else "#121212",
            image=bg_image,
            content=ft.SafeArea(
                content=ft.Container(
                    padding=ft.Padding.only(left=15, right=15, top=20, bottom=20),
                    content=ft.Column([
                        top_bar,
                        ft.Divider(),
                        ft.ResponsiveRow([
                            ft.Container(
                                content=ft.Column([
                                    ft.Text("Players Giving (Team A)", size=16, weight=ft.FontWeight.W_600),
                                    ft.Row([
                                        autocomplete_a,
                                        ft.IconButton(ft.Icons.ADD, on_click=lambda e: add_player(e, "A")),
                                    ]),
                                    list_a,
                                ]),
                                col={"sm": 6},
                                padding=10,
                                border_radius=8,
                                bgcolor=ft.Colors.with_opacity(0.72, ft.Colors.GREY_900),
                                border=ft.Border.all(1, ft.Colors.OUTLINE),
                            ),
                            ft.Container(
                                content=ft.Column([
                                    ft.Text("Players Receiving (Team B)", size=16, weight=ft.FontWeight.W_600),
                                    ft.Row([
                                        autocomplete_b,
                                        ft.IconButton(ft.Icons.ADD, on_click=lambda e: add_player(e, "B")),
                                    ]),
                                    list_b,
                                ]),
                                col={"sm": 6},
                                padding=10,
                                border_radius=8,
                                bgcolor=ft.Colors.with_opacity(0.72, ft.Colors.GREY_900),
                                border=ft.Border.all(1, ft.Colors.OUTLINE),
                            ),
                        ]),
                        ft.Container(height=10),
                        ft.Row([
                            ft.Button(content=ft.Text("Evaluate 9-Cat Trade"), on_click=handle_eval),
                            ft.Button(
                                content=ft.Text("Clear All Players"),
                                icon=ft.Icons.CLEAR_ALL,
                                icon_color=ft.Colors.RED_400,
                                on_click=clear_all,
                            ),
                        ], spacing=10),
                        ft.Container(height=10),
                        result_card,
                    ]),
                ),
            ),
        )
    )


if __name__ == "__main__":
    is_mobile_packaging = os.environ.get("SERIOUS_PYTHON_SITE_PACKAGES") is not None
    if is_mobile_packaging:
        ft.app(main, assets_dir=ASSETS_DIR if os.path.isdir(ASSETS_DIR) else None)
    else:
        port = int(os.environ.get("PORT", 10000))
        os.environ["FLET_SERVER_PORT"] = str(port)
        os.environ["FLET_SERVER_IP"] = "0.0.0.0"
        os.environ["FLET_FORCE_WEB_SERVER"] = "true"
        assets_arg = ASSETS_DIR if os.path.isdir(ASSETS_DIR) else None
        if os.name == "nt":
            ft.run(main, port=port, host="0.0.0.0", view=ft.AppView.WEB_BROWSER, assets_dir=assets_arg)
        else:
            ft.run(main, port=port, host="0.0.0.0", assets_dir=assets_arg)
