# main.py
import flet as ft
import traceback
from nba_data import search_player_by_name, get_player_9cat_stats
from evaluator import evaluate_trade

def main(page: ft.Page):
    page.title = "NBA 9-Cat Trade Evaluator"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    team_a_players = []
    team_b_players = []

    header = ft.Text("🏀 NBA 9-Cats Trade Evaluator", size=28, weight=ft.FontWeight.BOLD)

    list_a = ft.Column(spacing=10)
    list_b = ft.Column(spacing=10)

    # Search and suggestion handlers - displays up to 10 matches
    def handle_search_a(e):
        query = (e.data or "").strip()
        if len(query) < 2:
            autocomplete_a.suggestions = []
            autocomplete_a.update()
            return
        matches = search_player_by_name(query, max_results=10)
        suggestions = [
            ft.AutoCompleteSuggestion(key=m['full_name'], value=m['full_name'])
            for m in (matches[:10] if matches else [])
        ]
        autocomplete_a.suggestions = suggestions
        autocomplete_a.update()

    def handle_search_b(e):
        query = (e.data or "").strip()
        if len(query) < 2:
            autocomplete_b.suggestions = []
            autocomplete_b.update()
            return
        matches = search_player_by_name(query, max_results=10)
        suggestions = [
            ft.AutoCompleteSuggestion(key=m['full_name'], value=m['full_name'])
            for m in (matches[:10] if matches else [])
        ]
        autocomplete_b.suggestions = suggestions
        autocomplete_b.update()

    def on_select_a(e: ft.AutoCompleteSelectEvent):
        input_a.value = e.selection.value
        autocomplete_a.update()

    def on_select_b(e: ft.AutoCompleteSelectEvent):
        input_b.value = e.selection.value
        autocomplete_b.update()

    input_a = ft.TextField(label="Give Player Name", hint_text="e.g. Stephen Curry", expand=True)
    input_b = ft.TextField(label="Receive Player Name", hint_text="e.g. Seth Curry", expand=True)

    autocomplete_a = ft.AutoComplete(
        on_change=handle_search_a,
        on_select=on_select_a,
        suggestions=[],
        expand=True
    )
    autocomplete_a.content = input_a

    autocomplete_b = ft.AutoComplete(
        on_change=handle_search_b,
        on_select=on_select_b,
        suggestions=[],
        expand=True
    )
    autocomplete_b.content = input_b

    # Dynamic result display column
    result_column = ft.Column([
        ft.Text("Add up to 10 players on each side to evaluate.", size=16)
    ])

    result_card = ft.Container(
        content=result_column,
        padding=15,
        border_radius=8,
        bgcolor=ft.Colors.GREY_900
    )

    def show_toast(msg: str):
        page.snack_bar = ft.SnackBar(ft.Text(str(msg)))
        page.snack_bar.open = True
        page.update()

    def remove_player(player_data, team: str):
        target_list = team_a_players if team == "A" else team_b_players
        if player_data in target_list:
            target_list.remove(player_data)
        render_team_list(team)
        page.update()

    # Clear all players from both teams
    def clear_all(e):
        team_a_players.clear()
        team_b_players.clear()
        render_team_list("A")
        render_team_list("B")
        
        # Reset input fields and autocomplete suggestions
        input_a.value = ""
        input_b.value = ""
        autocomplete_a.suggestions = []
        autocomplete_b.suggestions = []
        autocomplete_a.update()
        autocomplete_b.update()

        # Reset result column text
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
                        ft.Text(f"• {p['name']} ({p.get('season', '2025-26')})", weight=ft.FontWeight.BOLD),
                        ft.Text(
                            f"PTS: {p.get('pts',0)} | REB: {p.get('reb',0)} | AST: {p.get('ast',0)} | "
                            f"STL: {p.get('stl',0)} | BLK: {p.get('blk',0)} | 3PM: {p.get('fg3m',0)} | "
                            f"FG%: {p.get('fg_pct',0)} | FT%: {p.get('ft_pct',0)} | TO: {p.get('tov',0)}",
                            size=12
                        )
                    ], expand=True),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINED,
                        icon_color=ft.Colors.RED_400,
                        tooltip="Remove Player",
                        on_click=lambda e, player=p, t=team: remove_player(player, t)
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=8,
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                border_radius=5
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

        show_toast(f"Searching stats for '{player_name}'...")

        matches = search_player_by_name(player_name, max_results=10)
        if not matches:
            show_toast(f"Active player '{player_name}' not found.")
            return

        player_info = matches[0]
        stats = get_player_9cat_stats(player_info['id'], season="2025-26")

        if not stats:
            show_toast(f"No stats found for {player_info['full_name']}")
            return

        player_data = {"name": player_info['full_name'], **stats}
        target_list.append(player_data)

        autocomplete.value = ""
        autocomplete.suggestions = []
        input_field.value = ""

        render_team_list(team)
        show_toast(f"Added {player_info['full_name']}!")
        page.update()

    def handle_eval(e):
        if not team_a_players or not team_b_players:
            show_toast("Please add players to BOTH sides before evaluating.")
            return

        try:
            res = evaluate_trade(team_a_players, team_b_players)

            names_a = ", ".join([p["name"] for p in team_a_players])
            names_b = ", ".join([p["name"] for p in team_b_players])

            eval_controls = [
                ft.Text("📊 Trade Comparison Summary", size=22, weight=ft.FontWeight.BOLD),
                ft.Text(f"Team A gives ({len(team_a_players)} player(s)): {names_a}", size=14, weight=ft.FontWeight.W_500),
                ft.Text(f"Team B gives ({len(team_b_players)} player(s)): {names_b}", size=14, weight=ft.FontWeight.W_500),
                ft.Divider(),
                ft.Text(f"Verdict: {res.get('status', 'Evaluated')}", size=18, weight=ft.FontWeight.BOLD, color=res.get('status_color', ft.Colors.WHITE)),
                ft.Text(f"Team A Total Value Score: {res.get('team_a_score', 0)}"),
                ft.Text(f"Team B Total Value Score: {res.get('team_b_score', 0)}"),
                ft.Text(f"Net Difference: {res.get('difference', 0)}"),
            ]

            result_column.controls = eval_controls
            page.update()

        except Exception as err:
            print("Evaluation Error Traceback:")
            traceback.print_exc()
            show_toast(f"Eval Error: {err}")

    input_a.on_submit = lambda e: add_player(e, "A")
    input_b.on_submit = lambda e: add_player(e, "B")

    page.add(
        header,
        ft.Divider(),
        ft.Row([
            ft.Container(
                content=ft.Column([
                    ft.Text("Players Giving (Team A)", size=16, weight=ft.FontWeight.W_600),
                    ft.Row([autocomplete_a, ft.IconButton(ft.Icons.ADD, on_click=lambda e: add_player(e, "A"))]),
                    list_a
                ]),
                expand=True, padding=10, border=ft.Border.all(1, ft.Colors.OUTLINE)
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("Players Receiving (Team B)", size=16, weight=ft.FontWeight.W_600),
                    ft.Row([autocomplete_b, ft.IconButton(ft.Icons.ADD, on_click=lambda e: add_player(e, "B"))]),
                    list_b
                ]),
                expand=True, padding=10, border=ft.Border.all(1, ft.Colors.OUTLINE)
            ),
        ]),
        ft.Container(height=10),
        ft.Row([
            ft.Button(content=ft.Text("Evaluate 9-Cat Trade"), on_click=handle_eval),
            ft.Button(
                content=ft.Text("Clear All Players"),
                icon=ft.Icons.CLEAR_ALL,
                icon_color=ft.Colors.RED_400,
                on_click=clear_all
            ),
        ], spacing=10),
        ft.Container(height=10),
        result_card
    )

if __name__ == "__main__":
    ft.run(main)